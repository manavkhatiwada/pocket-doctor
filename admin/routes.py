from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
import json
import os
from datetime import datetime
from models import db, Appointment, ChatHistory

# Create Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

# Admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            if 'username' in session and session.get('is_admin'):
                # User is logged in as admin in the main app but not in admin panel
                # Just redirect to admin login
                return redirect(url_for('admin.login'))
            else:
                # Not logged in or not an admin
                flash('Access denied. Admin privileges required.', 'error')
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Load admin users
def load_admin_users():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    admin_file = os.path.join(current_dir, 'admin_users.json')
    
    if not os.path.exists(admin_file):
        # Create default admin if file doesn't exist
        default_admin = {"admin": "admin123"}
        with open(admin_file, 'w') as file:
            json.dump(default_admin, file)
        return default_admin
    
    try:
        with open(admin_file, 'r') as file:
            return json.load(file)
    except:
        return {"admin": "admin123"}  # Default fallback

# Load doctors and departments
def load_doctors():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doctors_file = os.path.join(current_dir, 'doctors.json')
    
    if not os.path.exists(doctors_file):
        # Create default doctors if file doesn't exist
        default_doctors = {
            "Cardiology": ["Dr. Smith", "Dr. Johnson"],
            "Neurology": ["Dr. Brown", "Dr. Davis"],
            "Dermatology": ["Dr. Wilson", "Dr. Moore"],
            "Orthopedics": ["Dr. Taylor", "Dr. Anderson"],
            "Pediatrics": ["Dr. Thomas", "Dr. Jackson"]
        }
        with open(doctors_file, 'w') as file:
            json.dump(default_doctors, file)
        return default_doctors
    
    try:
        with open(doctors_file, 'r') as file:
            return json.load(file)
    except:
        return {}  # Empty dict fallback

# Save doctors and departments
def save_doctors(doctors_data):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doctors_file = os.path.join(current_dir, 'doctors.json')
    
    with open(doctors_file, 'w') as file:
        json.dump(doctors_data, file)

# Admin routes
@admin_bp.route('/')
@admin_required
def index():
    # Use the app context from the main app for database operations
    with current_app.app_context():
        # Dashboard statistics
        total_users = len(set([appt.email for appt in Appointment.query.all()]))
        total_appointments = Appointment.query.count()
        pending_appointments = Appointment.query.filter_by(status='pending').count()
        completed_appointments = Appointment.query.filter_by(status='completed').count()
        
        # Recent appointments
        recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                          total_users=total_users,
                          total_appointments=total_appointments,
                          pending_appointments=pending_appointments,
                          completed_appointments=completed_appointments,
                          recent_appointments=recent_appointments)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in as admin in the main app, auto-login to admin panel
    if 'username' in session and session.get('is_admin') and 'admin_logged_in' not in session:
        admin_users = load_admin_users()
        if session['username'] in admin_users:
            session['admin_logged_in'] = True
            session['admin_username'] = session['username']
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin_users = load_admin_users()
        
        if username in admin_users and admin_users[username] == password:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            # Also set the regular user session for consistency
            session['username'] = username
            session['is_admin'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid admin credentials', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Admin logged out successfully', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/users')
@admin_required
def users():
    # Use the app context from the main app for database operations
    with current_app.app_context():
        # Get unique users from appointments
        user_emails = set([appt.email for appt in Appointment.query.all()])
        users_data = []
        
        for email in user_emails:
            # Get the most recent appointment for this user to get their info
            user_info = Appointment.query.filter_by(email=email).order_by(Appointment.created_at.desc()).first()
            appointment_count = Appointment.query.filter_by(email=email).count()
            chat_count = ChatHistory.query.filter_by(email=email).count()
            
            users_data.append({
                'email': email,
                'name': user_info.name if user_info else 'Unknown',
                'phone': user_info.phone if user_info else 'Unknown',
                'appointment_count': appointment_count,
                'chat_count': chat_count,
                'joined': user_info.created_at.strftime('%Y-%m-%d') if user_info else 'Unknown'
            })
    
    return render_template('admin/users.html', users=users_data)

@admin_bp.route('/appointments')
@admin_required
def appointments():
    status_filter = request.args.get('status', '')
    
    # Use the app context from the main app for database operations
    with current_app.app_context():
        if status_filter and status_filter != 'all':
            appointments = Appointment.query.filter_by(status=status_filter).order_by(Appointment.date.desc()).all()
        else:
            appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    
    return render_template('admin/appointments.html', appointments=appointments, current_filter=status_filter)

@admin_bp.route('/appointment/<int:id>')
@admin_required
def appointment_detail(id):
    # Use the app context from the main app for database operations
    with current_app.app_context():
        appointment = Appointment.query.get_or_404(id)
    return render_template('admin/appointment_detail.html', appointment=appointment)

@admin_bp.route('/update_appointment_status/<int:id>', methods=['POST'])
@admin_required
def update_appointment_status(id):
    # Use the app context from the main app for database operations
    with current_app.app_context():
        appointment = Appointment.query.get_or_404(id)
        new_status = request.form.get('status')
        
        if new_status in ['pending', 'confirmed', 'completed', 'cancelled']:
            appointment.status = new_status
            db.session.commit()
            flash(f'Appointment status updated to {new_status}', 'success')
        else:
            flash('Invalid status', 'error')
    
    return redirect(url_for('admin.appointment_detail', id=id))

@admin_bp.route('/settings')
@admin_required
def settings():
    return render_template('admin/settings.html')

@admin_bp.route('/change_password', methods=['POST'])
@admin_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    admin_users = load_admin_users()
    admin_username = session.get('admin_username')
    
    if admin_users.get(admin_username) != current_password:
        flash('Current password is incorrect', 'error')
    elif new_password != confirm_password:
        flash('New passwords do not match', 'error')
    else:
        admin_users[admin_username] = new_password
        
        # Save updated admin users
        current_dir = os.path.dirname(os.path.abspath(__file__))
        admin_file = os.path.join(current_dir, 'admin_users.json')
        
        with open(admin_file, 'w') as file:
            json.dump(admin_users, file)
            
        flash('Admin password updated successfully', 'success')
    
    return redirect(url_for('admin.settings'))

# Doctor and Department Management
@admin_bp.route('/doctors')
@admin_required
def doctors():
    doctors_data = load_doctors()
    return render_template('admin/doctors.html', doctors=doctors_data)

@admin_bp.route('/add_department', methods=['POST'])
@admin_required
def add_department():
    department_name = request.form.get('department_name')
    if department_name:
        doctors_data = load_doctors()
        if department_name not in doctors_data:
            doctors_data[department_name] = []
            save_doctors(doctors_data)
            flash(f'Department "{department_name}" added successfully', 'success')
        else:
            flash(f'Department "{department_name}" already exists', 'warning')
    else:
        flash('Department name cannot be empty', 'error')
    return redirect(url_for('admin.doctors'))

@admin_bp.route('/remove_department', methods=['POST'])
@admin_required
def remove_department():
    department_name = request.form.get('department_name')
    if department_name:
        doctors_data = load_doctors()
        if department_name in doctors_data:
            del doctors_data[department_name]
            save_doctors(doctors_data)
            flash(f'Department "{department_name}" removed successfully', 'success')
        else:
            flash(f'Department "{department_name}" not found', 'error')
    return redirect(url_for('admin.doctors'))

@admin_bp.route('/add_doctor', methods=['POST'])
@admin_required
def add_doctor():
    department_name = request.form.get('department_name')
    doctor_name = request.form.get('doctor_name')
    
    if department_name and doctor_name:
        doctors_data = load_doctors()
        if department_name in doctors_data:
            if doctor_name not in doctors_data[department_name]:
                doctors_data[department_name].append(doctor_name)
                save_doctors(doctors_data)
                flash(f'Doctor "{doctor_name}" added to "{department_name}" successfully', 'success')
            else:
                flash(f'Doctor "{doctor_name}" already exists in "{department_name}"', 'warning')
        else:
            flash(f'Department "{department_name}" not found', 'error')
    else:
        flash('Department and doctor name cannot be empty', 'error')
    return redirect(url_for('admin.doctors'))

@admin_bp.route('/remove_doctor', methods=['POST'])
@admin_required
def remove_doctor():
    department = request.form.get('department')
    doctor = request.form.get('doctor')
    
    if department and doctor:
        doctors_data = load_doctors()
        if department in doctors_data and doctor in doctors_data[department]:
            doctors_data[department].remove(doctor)
            save_doctors(doctors_data)
            flash(f'Doctor {doctor} removed successfully', 'success')
        else:
            flash('Doctor or department not found', 'error')
    else:
        flash('Department and doctor name are required', 'error')
    
    return redirect(url_for('admin.doctors'))

@admin_bp.route('/user_chats/<email>')
@admin_required
def user_chats(email):
    # Use the app context from the main app for database operations
    with current_app.app_context():
        # Get user info for display
        user_info = Appointment.query.filter_by(email=email).order_by(Appointment.created_at.desc()).first()
        
        # Get all chat history for this user
        chat_history = ChatHistory.query.filter_by(email=email).order_by(ChatHistory.timestamp.desc()).all()
        
    return render_template('admin/user_chats.html', 
                           email=email, 
                           user_info=user_info, 
                           chat_history=chat_history)

@admin_bp.route('/user_appointments/<email>')
@admin_required
def user_appointments(email):
    # Use the app context from the main app for database operations
    with current_app.app_context():
        # Get user info for display
        user_info = Appointment.query.filter_by(email=email).order_by(Appointment.created_at.desc()).first()
        
        # Get all appointments for this user
        appointments = Appointment.query.filter_by(email=email).order_by(Appointment.date.desc()).all()
        
    return render_template('admin/user_appointments.html', 
                           email=email, 
                           user_info=user_info, 
                           appointments=appointments) 
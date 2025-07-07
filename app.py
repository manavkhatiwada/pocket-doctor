from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os
from datetime import datetime
import sqlalchemy
from auth import register_user, login_user, get_user_email
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
import pickle
from groq import Groq
from typing import List, Dict
from models import db, Appointment, ChatHistory

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# For development: disable actual email sending but keep functionality
# This avoids the Gmail authentication error while testing
app.config['MAIL_SUPPRESS_SEND'] = True  # Disable actual email sending
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = None  # Set to None to avoid authentication
app.config['MAIL_PASSWORD'] = None  # Set to None to avoid authentication
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = ('MyPocketDoctor', 'noreply@mypocketdoctor.com')

db.init_app(app)
mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Add Jinja2 filter for converting newlines to <br> tags
@app.template_filter('nl2br')
def nl2br_filter(s):
    if s:
        return s.replace('\n', '<br>')
    return ''

# Chatbot functionality
class HealthVectorStore:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        # self.encoder = None
        self.encoder = SentenceTransformer(model_name)

        # Initialize nearest neighbors model
        self.knn = NearestNeighbors(n_neighbors=3, metric='cosine')
        
        # Store texts and vectors
        self.texts = []
        self.vectors = None
        
        # Path for persistence
        self.data_path = "health_data.pkl"
        
        # Load existing data if available
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Load existing data or initialize with default health data"""
        if os.path.exists(self.data_path):
            # Load existing data
            with open(self.data_path, 'rb') as f:
                data = pickle.load(f)
                self.texts = data['texts']
                self.vectors = data['vectors']
                if len(self.texts) > 0:
                    self.knn.fit(self.vectors)
        else:
            # Initialize with default health data
            default_texts = [
                "Fever is a common symptom of infections and can be caused by viruses or bacteria. General Physician or Infectious Disease Specialist is recommended.",
                "Headache can be caused by stress, dehydration, or underlying medical conditions. Neurologist is recommended for persistent headaches.",
                "Chest pain should be evaluated by a cardiologist immediately.",
                "Skin rashes can be caused by allergies, infections, or autoimmune conditions. Dermatologist is recommended.",
                "Abdominal pain can be related to digestive issues, infections, or organ problems. Gastroenterologist is recommended.",
                "Shortness of breath may indicate respiratory or cardiac conditions. Pulmonologist or Cardiologist is recommended.",
                "Joint pain can be caused by arthritis, injury, or autoimmune diseases. Orthopedic Surgeon or Rheumatologist is recommended.",
                "Fatigue can be a symptom of various conditions including anemia, thyroid problems, or chronic fatigue syndrome. General Physician is recommended.",
                "Nausea and vomiting can be caused by infections, food poisoning, or digestive disorders. Gastroenterologist is recommended.",
                "Dizziness can be related to inner ear problems, low blood pressure, or neurological conditions. ENT Specialist or Neurologist is recommended."
            ]
            self.add_texts(default_texts)
    
    def add_texts(self, texts):
        """Add new texts to the vector store"""
        if not texts:
            return
        
        # Convert texts to vectors
        new_vectors = self.encoder.encode(texts)
        
        # Update vectors
        if self.vectors is None:
            self.vectors = new_vectors
        else:
            self.vectors = np.vstack([self.vectors, new_vectors])
        
        # Update texts
        self.texts.extend(texts)
        
        # Fit the KNN model
        self.knn.fit(self.vectors)
        
        # Save to disk
        self._save()
    
    def search(self, query, k=3):
        """Search for similar texts"""
        # Convert query to vector
        query_vector = self.encoder.encode([query])
        
        # If we don't have any vectors yet, return empty list
        if self.vectors is None or len(self.vectors) == 0:
            return []
        
        # Find nearest neighbors
        distances, indices = self.knn.kneighbors(query_vector)
        
        # Get corresponding texts
        results = [self.texts[i] for i in indices[0]]
        return results
    
    def _save(self):
        """Save the data to disk"""
        data = {
            'texts': self.texts,
            'vectors': self.vectors
        }
        with open(self.data_path, 'wb') as f:
            pickle.dump(data, f)

# Initialize vector store
vector_store = HealthVectorStore()

# Register the admin blueprints
try:
    import sys
    import os
    # Add the current directory to the path so we can import admin modules
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from admin.routes import admin_bp
    from admin.admin_routes import admin_notes_bp
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_notes_bp)
    
    @app.route('/admin')
    def admin_redirect():
        # Check if user is logged in and is an admin
        if 'username' in session and session.get('is_admin'):
            return redirect(url_for('admin.index'))
        
        elif 'username' in session:
            # User is logged in but not an admin
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('home'))
        
        else:
            # User is not logged in
            flash('Please login first to access the admin panel', 'warning')
            return redirect(url_for('login'))
        
except ImportError as e:
    print(f"Error importing admin modules: {e}")
    # Continue without admin functionality

@app.route('/')
def home():
    return render_template('home.html', active_page='home')

@app.route('/about')
def about():
    return render_template('about.html', active_page='about')

@app.route('/chat')
def chat():
    # Check if user is logged in
    if 'username' not in session:
        flash('Please login first to access the chat feature', 'warning')
        return redirect(url_for('login'))
    return render_template('chat.html', active_page='chat')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        success, message = login_user(username, password)
        if success:
            session['username'] = username
            
            # Get and store the user's email in the session
            email = get_user_email(username)
            if email:
                session['email'] = email
            
            # Check if the user is an admin
            try:
                from admin.routes import load_admin_users
                admin_users = load_admin_users()
                if username in admin_users:
                    session['is_admin'] = True
                else:
                    session['is_admin'] = False

            except:
                session['is_admin'] = False
                
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash(message, 'error')
    return render_template('login.html', active_page='login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        success, message = register_user(username, password, email)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    return render_template('signup.html', active_page='signup')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    # Check if user is logged in
    if 'username' not in session:
        flash('Please login first to book an appointment', 'warning')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        try:
            data = request.form
            
            # Extract form data from randomized field names
            name = None
            email = None
            phone = None
            
            # Find the actual field values by looking for fields that start with the base name
            for field_name in data:
                if field_name.startswith('name_'):
                    name = data[field_name]
                elif field_name.startswith('email_'):
                    email = data[field_name]
                elif field_name.startswith('phone_'):
                    phone = data[field_name]
            
            # If we couldn't find the fields with randomized names, fall back to the standard names
            name = name or data.get('name')
            email = email or data.get('email')
            phone = phone or data.get('phone')
            
            # Get the rest of the fields (these don't have randomized names)
            department = data['department']
            doctor = data['doctor']
            problem = data['problem']
            date = data['date']
            time = data['time']
            
            # Validate required fields
            if not all([name, email, phone, department, doctor, problem, date, time]):
                flash('All fields are required. Please fill out the form completely.', 'error')
                return redirect(url_for('appointment'))
            
            token = s.dumps(email, salt='email-confirm')
            new_appointment = Appointment(
                name=name,
                email=email,
                phone=phone,
                department=department,
                doctor=doctor,
                problem=problem,
                date=date,
                time=time,
                verification_token=token,
                status='pending'
            )
            db.session.add(new_appointment)
            db.session.commit()

            # Try to send verification email
            try:
                link = url_for('verify_email', token=token, _external=True)
                msg = Message('Verify Your MyPocketDoctor Appointment', 
                             recipients=[email])
                
                # HTML Email template
                appointment_html = f'''
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #0099e5; color: white; padding: 15px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .appointment-details {{ background-color: white; padding: 15px; margin: 20px 0; border-left: 4px solid #0099e5; }}
                        .cta-button {{ display: inline-block; background-color: #0099e5; color: white; text-decoration: none; padding: 12px 25px; border-radius: 4px; margin: 20px 0; }}
                        .footer {{ text-align: center; padding-top: 20px; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>MyPocketDoctor</h1>
                        </div>
                        <div class="content">
                            <h2>Hello {name},</h2>
                            <p>Thank you for booking an appointment with MyPocketDoctor. Please confirm your appointment details below and verify by clicking the button.</p>
                            
                            <div class="appointment-details">
                                <p><strong>Name:</strong> {name}</p>
                                <p><strong>Department:</strong> {department}</p>
                                <p><strong>Doctor:</strong> {doctor}</p>
                                <p><strong>Date:</strong> {date}</p>
                                <p><strong>Time:</strong> {time}</p>
                            </div>
                            
                            <p>Your appointment will only be confirmed after verification.</p>
                            <center>
                                <a href="{link}" class="cta-button">Verify My Appointment</a>
                            </center>
                            <p>If the button doesn't work, copy and paste this URL into your browser:</p>
                            <p>{link}</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                            <p>&copy; 2025 MyPocketDoctor. All rights reserved.</p>
                        </div>
                    </div>
                </body>
                </html>
                '''
                
                # Plain text version for email clients that don't support HTML
                appointment_text = f'''
                Hello {name},
                
                Thank you for booking an appointment with MyPocketDoctor. Below are your appointment details:
                
                Name: {name}
                Department: {department}
                Doctor: {doctor}
                Date: {date}
                Time: {time}
                
                Please verify your appointment by clicking this link: {link}
                
                Your appointment will only be confirmed after verification.
                
                MyPocketDoctor Team
                '''
                
                msg.body = appointment_text
                msg.html = appointment_html
                mail.send(msg)
                
                if app.config['MAIL_SUPPRESS_SEND']:
                    # For development: auto-verify
                    new_appointment.verified = True
                    db.session.commit()
                    # No flash message about verification link
                else:
                    flash('Appointment booked! Please check your email to verify.', 'success')
                    
            except Exception as e:
                # If email sending fails, notify user but don't prevent appointment creation
                flash(f'Appointment booked, but email verification failed: {str(e)}', 'warning')
                # Auto-verify the appointment since email is not working
                new_appointment.verified = True
                db.session.commit()
                
            # Redirect to dashboard instead of appointment page
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error booking appointment: {str(e)}', 'error')
            return redirect(url_for('appointment'))
            
    # Get preselected doctor and department from query params
    preselected_doctor = request.args.get('doctor', '')
    preselected_department = request.args.get('department', '')
    return render_template('appointment.html', active_page='appointment', preselected_doctor=preselected_doctor, preselected_department=preselected_department)

@app.route('/verify/<token>')
def verify_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        appointment = Appointment.query.filter_by(email=email, verification_token=token).first()
        if appointment:
            appointment.verified = True
            appointment.status = 'confirmed'
            db.session.commit()
            
            # Send confirmation email 
            try:
                msg = Message('Your MyPocketDoctor Appointment is Confirmed', 
                            recipients=[appointment.email])
                
                # HTML Email template for confirmation
                confirmation_html = f'''
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #0099e5; color: white; padding: 15px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .appointment-details {{ background-color: white; padding: 15px; margin: 20px 0; border-left: 4px solid #00b67a; }}
                        .save-calendar {{ display: inline-block; background-color: #00b67a; color: white; text-decoration: none; padding: 12px 25px; border-radius: 4px; margin: 20px 0; }}
                        .view-appointments {{ display: inline-block; background-color: #0099e5; color: white; text-decoration: none; padding: 12px 25px; border-radius: 4px; margin-left: 10px; }}
                        .footer {{ text-align: center; padding-top: 20px; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>MyPocketDoctor</h1>
                        </div>
                        <div class="content">
                            <h2>Appointment Confirmed!</h2>
                            <p>Hello {appointment.name},</p>
                            <p>Your appointment has been successfully confirmed. Here are your appointment details:</p>
                            
                            <div class="appointment-details">
                                <p><strong>Name:</strong> {appointment.name}</p>
                                <p><strong>Department:</strong> {appointment.department}</p>
                                <p><strong>Doctor:</strong> {appointment.doctor}</p>
                                <p><strong>Date:</strong> {appointment.date}</p>
                                <p><strong>Time:</strong> {appointment.time}</p>
                                <p><strong>Status:</strong> <span style="color: #00b67a; font-weight: bold;">Confirmed</span></p>
                            </div>
                            
                            <p>Please arrive 15 minutes prior to your appointment time. If you need to reschedule or cancel, please contact us at least 24 hours in advance.</p>
                            
                            <center>
                                <!-- In a real app, you might include a calendar invitation -->
                                <a href="#" class="save-calendar">Add to Calendar</a>
                                <a href="{url_for('dashboard', email=appointment.email, _external=True)}" class="view-appointments">View All Appointments</a>
                            </center>
                            
                            <p style="margin-top: 30px;">Thank you for choosing MyPocketDoctor for your healthcare needs.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                            <p>&copy; 2025 MyPocketDoctor. All rights reserved.</p>
                        </div>
                    </div>
                </body>
                </html>
                '''
                
                # Plain text version for email clients that don't support HTML
                confirmation_text = f'''
                Appointment Confirmed!
                
                Hello {appointment.name},
                
                Your appointment has been successfully confirmed. Here are your appointment details:
                
                Name: {appointment.name}
                Department: {appointment.department}
                Doctor: {appointment.doctor}
                Date: {appointment.date}
                Time: {appointment.time}
                Status: Confirmed
                
                Please arrive 15 minutes prior to your appointment time. If you need to reschedule or cancel, please contact us at least 24 hours in advance.
                
                Thank you for choosing MyPocketDoctor for your healthcare needs.
                
                MyPocketDoctor Team
                '''
                
                msg.body = confirmation_text
                msg.html = confirmation_html
                mail.send(msg)
                
                if app.config['MAIL_SUPPRESS_SEND']:
                    print("Development mode: Confirmation email sending suppressed.")
                    
            except Exception as e:
                # If confirmation email fails, don't prevent the user from seeing success page
                print(f"Failed to send confirmation email: {e}")
            
            # Add a session variable to ensure the user can access the dashboard
            session['username'] = appointment.email
            
            # Return the verification success page with a link to the dashboard
            return render_template('verification_success.html', appointment=appointment, dashboard_url=url_for('dashboard'))
        else:
            return render_template('verification_error.html', error="Invalid verification token")
    except Exception as e:
        return render_template('verification_error.html', error="Verification link is invalid or has expired")

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Check if user is logged in
    if 'username' not in session:
        flash('Please login first to view your dashboard', 'warning')
        return redirect(url_for('login'))
        
    # Get the actual email from session or fetch it using the username
    email = request.form.get('email') or request.args.get('email')
    
    if not email:
        # Try to get email from session first
        if 'email' in session:
            email = session['email']
        else:
            # Fallback to getting email using the username
            email = get_user_email(session['username'])
            
            # Store email in session for future use
            if email:
                session['email'] = email
            
            # If no email found, use username as fallback
            if not email:
                email = session['username']
    
    # Handle form submissions
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        # Handle profile update
        if form_type == 'profile_update':
            name = request.form.get('name')
            phone = request.form.get('phone')
            
            # Update all appointments for this user with the new name and phone
            try:
                appointments_to_update = Appointment.query.filter_by(email=email).all()
                for appointment in appointments_to_update:
                    appointment.name = name
                    appointment.phone = phone
                db.session.commit()
                
                # Store profile info in session for display
                session['profile_name'] = name
                session['profile_phone'] = phone
                
                flash('Profile updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating profile: {str(e)}', 'error')
    
    appointments = []
    chat_history = []
    profile_name = "Not provided"
    profile_phone = "Not provided"
    
    if email:
        # Get appointments - show all appointments regardless of verification status
        appointments = Appointment.query.filter_by(email=email).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
        
        # Get chat history
        chat_history = ChatHistory.query.filter_by(email=email).order_by(ChatHistory.timestamp.desc()).limit(10).all()
        
        # Get profile info from the most recent appointment or from session
        if 'profile_name' in session and session['profile_name']:
            profile_name = session['profile_name']
        elif appointments and appointments[0].name:
            profile_name = appointments[0].name
            
        if 'profile_phone' in session and session['profile_phone']:
            profile_phone = session['profile_phone']
        elif appointments and appointments[0].phone:
            profile_phone = appointments[0].phone
    
    return render_template('dashboard.html', 
                          email=email, 
                          appointments=appointments, 
                          chat_history=chat_history, 
                          profile_name=profile_name,
                          profile_phone=profile_phone,
                          active_page='dashboard')

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        flash('Please login first to change your password', 'warning')
        return redirect(url_for('login'))
    
    username = session['username']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not all([current_password, new_password, confirm_password]):
        flash('All fields are required', 'error')
        return redirect(url_for('dashboard'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('dashboard'))
    
    # Verify current password
    users = load_users()
    if username not in users:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))
    
    user_data = users[username]
    stored_password = user_data.get('password') if isinstance(user_data, dict) else user_data
    
    if stored_password != current_password:
        flash('Current password is incorrect', 'error')
        return redirect(url_for('dashboard'))
    
    # Update password
    if isinstance(user_data, dict):
        users[username]['password'] = new_password
    else:
        users[username] = {
            'password': new_password,
            'email': get_user_email(username)
        }
    
    if save_users(users):
        flash('Password changed successfully!', 'success')
    else:
        flash('Error changing password. Please try again.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/history', methods=['GET', 'POST'])
def history():
    # Check if user is logged in
    if 'username' not in session:
        flash('Please login first to view your appointment history', 'warning')
        return redirect(url_for('login'))
        
    appointments = []
    email = session['username']
    if request.method == 'POST':
        email = request.form['email']
    appointments = Appointment.query.filter_by(email=email, verified=True).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('history.html', appointments=appointments)

@app.route('/cancel_appointment/<int:id>', methods=['POST'])
def cancel_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    appointment.status = 'cancelled'
    db.session.commit()
    flash('Appointment has been cancelled successfully', 'success')
    # Check if the request came from dashboard or history
    referrer = request.referrer
    email = request.form.get('email')
    if referrer and '/dashboard' in referrer and email:
        return redirect(url_for('dashboard', email=email))
    return redirect(url_for('history'))

@app.route('/complete_appointment/<int:id>', methods=['POST'])
def complete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    appointment.status = 'completed'
    db.session.commit()
    flash('Appointment has been marked as completed', 'success')
    # Check if the request came from dashboard or history
    referrer = request.referrer
    email = request.form.get('email')
    if referrer and '/dashboard' in referrer and email:
        return redirect(url_for('dashboard', email=email))
    return redirect(url_for('history'))

@app.route('/add_notes/<int:id>', methods=['POST'])
def add_notes(id):
    appointment = Appointment.query.get_or_404(id)
    notes = request.form.get('notes')
    if notes:
        appointment.notes = notes
        db.session.commit()
        flash('Notes added successfully', 'success')
    # Check if the request came from dashboard or history
    referrer = request.referrer
    email = request.form.get('email')
    if referrer and '/dashboard' in referrer and email:
        return redirect(url_for('dashboard', email=email))
    return redirect(url_for('history'))



from dotenv import load_dotenv
load_dotenv()
groq_api_key = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key)

def get_chat_history(email: str, limit: int = 3) -> List[Dict[str, str]]:
    """Get recent chat history for context"""
    history = ChatHistory.query.filter_by(email=email).order_by(ChatHistory.timestamp.desc()).limit(limit).all()
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": msg.user_message if i % 2 == 0 else msg.bot_response} 
            for i, msg in enumerate(reversed(history))]


@app.route('/api/chat', methods=['POST'])
def process_chat():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Search for similar health info in vector store
    similar_info = vector_store.search(user_message)
    
    # Get recent chat history for context
    chat_history = get_chat_history(session.get('username'))
    
    # Prepare the prompt for Groq
    system_prompt = """You are a helpful and polite AI health assistant named [Pocket doctor]. You provide accurate, concise, and friendly health-related advice to users.

✅ Behavior Rules:
If the user says greetings like "Hi," "Hello," or "How are you?", respond with:
"Hello! I'm here to help with any health-related concerns. Could you please tell me your symptoms or the health issue you're facing?"

If the user asks something not related to health, respond with:
"I'm designed to assist with health-related questions. Please let me know if you have any health symptoms or medical concerns."

If the user provides a health concern, respond with:
A brief explanation of what it might be
Possible causes (structured in numbered list if needed)
Short, polite advice (what to do next)

Use this structure (example):
A temperature of 101°F (38.3°C) for 3 days with a sore throat may suggest a viral or bacterial infection.
Common causes include:
1. Viral infection – such as a common cold or flu
2. Bacterial infection – like strep throat
To manage your symptoms:
1. Drink plenty of fluids and rest well
2. Gargle with warm salt water
3. Use a humidifier if the air is dry
4. Take paracetamol or ibuprofen to reduce fever and pain
It's best to consult a doctor for a throat exam or tests like a throat swab to confirm the cause.

Please seek immediate care if you develop:
1. Difficulty breathing or swallowing
2. Fever above 103°F (39.4°C)
3. Severe headache, rash, or swelling in the face or throat

Do NOT use asterisks or bullets. Use numbered lists with clear spacing.

If not enough info is provided, ask 1 specific follow-up like:
"Can you please tell me how long you've had this symptom?"

Do NOT repeat questions that have already been answered.
Avoid overwhelming users with too many follow-ups.
Always remain polite, clear, and professional.
"Do not use asterisks (*) for bold, bullet points, or emphasis. Instead, use plain numbers (1, 2, 3) and structured line breaks for lists and headings."
Only ask a maximum of 2–3 focused follow-up questions if necessary to understand the user's health concern. Each follow-up must be specific and relevant. Do not repeat questions already answered.

If the user still doesn't provide enough relevant information after 2–3 follow-ups, respond with:
"You haven't provided enough information to give a complete answer, but here's what I can share based on what I know."
Then provide a general, helpful, and safe response based on the limited information.

If it's a possible emergency, respond immediately with:
"This may be a serious condition. Please seek immediate medical attention or contact emergency services."

**Only recommend a specific doctor and show a booking link after you are confident about the user's disease or main symptom. If you need more information, ask up to 2 follow-up questions first. Once you know the likely disease or symptom, suggest the appropriate doctor and provide a booking link. If the user directly asks to book for a specific disease or symptom, recommend the related doctor and show the booking link immediately.**
"""
    
    # Add similar medical information to the context if available
    context = ""
    if similar_info:
        context = "Relevant medical information:\n" + "\n".join(similar_info)
    
    # Try to extract doctor and department from similar_info
    suggested_doctor = None
    suggested_department = None
    valid_doctors = [
        'Cardiologist', 'Neurologist', 'Dermatologist', 'Orthopedic', 'OrthopedicSurgeon',
        'Rheumatologist', 'Pulmonologist', 'Gastroenterologist', 'ENT', 'Pediatrician',
        'General Physician'
    ]
    greeting_keywords = ['hello', 'hi', 'hey', 'greetings', 'how are you']
    user_message_lower = user_message.strip().lower()
    is_greeting = any(greet in user_message_lower for greet in greeting_keywords)
    if similar_info and not is_greeting:
        for info in similar_info:
            if "is recommended" in info:
                before = info.split("is recommended")[0]
                # Try to extract doctor (last 2 words for 'General Physician', else last word)
                words = before.strip().split()
                if len(words) >= 2 and words[-2] == 'General' and words[-1] == 'Physician':
                    suggested_doctor = 'General Physician'
                else:
                    suggested_doctor = words[-1].replace('.', '')
                # Map doctor to department (simple mapping)
                doctor_department_map = {
                    'Cardiologist': 'Cardiology',
                    'Neurologist': 'Neurology',
                    'Dermatologist': 'Dermatology',
                    'Orthopedic': 'Orthopedics',
                    'OrthopedicSurgeon': 'Orthopedics',
                    'Rheumatologist': 'Orthopedics',
                    'Pulmonologist': 'General',
                    'General Physician': 'General',
                    'Gastroenterologist': 'General',
                    'ENT': 'General',
                    'Pediatrician': 'Pediatrics',
                }
                suggested_department = doctor_department_map.get(suggested_doctor, 'General')
                break

    # Prepare messages for Groq
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add context if available
    if context:
        messages.append({"role": "system", "content": context})
    
    # Add chat history
    messages.extend(chat_history)
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    try:
        # Get response from Groq
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # or another suitable model
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        
        response = completion.choices[0].message.content
        
    except Exception as e:
        print(f"Error with Groq API: {str(e)}")
        # Fallback to basic response if Groq fails
        if similar_info:
            response = "Based on your symptoms, here's what I can tell you:\n\n"
            for info in similar_info:
                response += f"• {info}\n\n"
            response += "Would you like to schedule an appointment with a doctor?"
        else:
            response = "I'm not sure about your symptoms. I recommend consulting with a healthcare professional. Would you like to schedule an appointment?"
    
    # If a doctor is suggested, append a booking link only if it's valid and not a greeting
    if suggested_doctor in valid_doctors and not is_greeting:
        booking_url = url_for('appointment', doctor=suggested_doctor, department=suggested_department)
        response += f"\n\n[Book an appointment with a {suggested_doctor}]({booking_url})"
    
    # Save the chat message to the database
    email = session.get('email') or get_user_email(session.get('username'))
    new_chat = ChatHistory(
        email=email,
        user_message=user_message,
        bot_response=response
    )

    db.session.add(new_chat)
    db.session.commit()
    
    return jsonify({
        'response': response,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/check_availability', methods=['POST'])
def check_availability():
    try:
        data = request.json
        doctor = data.get('doctor')
        date = data.get('date')
        
        if not doctor or not date:
            return jsonify({'error': 'Doctor and date are required', 'booked_times': []}), 400
            
        # Query the database for existing appointments
        booked_appointments = Appointment.query.filter_by(
            doctor=doctor, 
            date=date,
            verified=True  # Only include verified appointments
        ).all()
        
        # Extract the booked times
        booked_times = [appointment.time for appointment in booked_appointments]
        
        return jsonify({
            'doctor': doctor,
            'date': date,
            'booked_times': booked_times
        })
    except Exception as e:
        app.logger.error(f"Error in check_availability: {str(e)}")
        return jsonify({'error': 'Server error', 'booked_times': []}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Only create tables if they don't exist; don't drop!
    app.run(debug=True, port=5000) 
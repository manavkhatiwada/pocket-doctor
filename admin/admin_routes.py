from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from functools import wraps
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, Appointment

# Create admin notes blueprint
admin_notes_bp = Blueprint('admin_notes', __name__, url_prefix='/admin/notes')

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login as admin first', 'warning')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_notes_bp.route('/add/<int:id>', methods=['POST'])
@admin_required
def add_notes(id):
    # Use the app context from the main app for database operations
    with current_app.app_context():
        appointment = Appointment.query.get_or_404(id)
        notes = request.form.get('notes')
        
        if notes:
            appointment.notes = notes
            db.session.commit()
            flash('Notes added successfully', 'success')
    
    return redirect(url_for('admin.appointment_detail', id=id))

@admin_notes_bp.route('/delete/<int:id>', methods=['POST'])
@admin_required
def delete_notes(id):
    # Use the app context from the main app for database operations
    with current_app.app_context():
        appointment = Appointment.query.get_or_404(id)
        appointment.notes = None
        db.session.commit()
        flash('Notes deleted successfully', 'success')
    
    return redirect(url_for('admin.appointment_detail', id=id)) 
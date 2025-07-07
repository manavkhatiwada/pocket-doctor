import json
import os

# Use absolute path for users.json
current_dir = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(current_dir, 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        # Create an empty users file if it doesn't exist
        save_users({})
        return {}
    try:
        with open(USERS_FILE, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        # If the file is corrupted or empty, start with an empty dict
        save_users({})
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as file:
            json.dump(users, file)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def register_user(username, password, email=None):
    if not username or not password:
        return False, "Username and password cannot be empty!"
    
    if email is None:
        email = ""  # Backward compatibility for users without email
    
    users = load_users()
    
    # Check if username already exists
    if username in users:
        return False, "Username already exists!"
    
    # Check if email is already in use (skip if email is empty)
    if email:
        for user, data in users.items():
            if isinstance(data, dict) and data.get('email') == email:
                return False, "Email already registered!"
    
    # Store user data as dictionary with password and email
    users[username] = {
        'password': password,
        'email': email
    }
    
    if save_users(users):
        return True, "Registration successful!"
    else:
        return False, "Error saving user data. Please try again."

def login_user(username, password):
    if not username or not password:
        return False, "Username and password cannot be empty!"
    
    users = load_users()
    
    if username in users:
        # Handle both old format (direct password) and new format (dict with password)
        user_data = users[username]
        
        if isinstance(user_data, dict):
            # New format with email
            if user_data.get('password') == password:
                return True, "Login successful!"
        else:
            # Old format (just password)
            if user_data == password:
                # Upgrade to new format
                users[username] = {
                    'password': password,
                    'email': ""
                }
                save_users(users)
                return True, "Login successful!"
    
    return False, "Invalid username or password!"

def get_user_email(username):
    users = load_users()
    if username in users:
        user_data = users[username]
        if isinstance(user_data, dict):
            return user_data.get('email', "")
    return "" 
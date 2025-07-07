# MyPocketDoctor

A healthcare web application with appointment booking, email verification, and AI chat features.

## Features
- Book doctor appointments
- Email verification system
- Appointment history
- Chat with an AI health assistant
- Modern, responsive UI

## Setup and Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- VS Code (for running with debugger)

### Installation Steps

1. Clone the repository:
```
git clone <repository-url>
cd MyPocketDoctor
```

2. Create a virtual environment (recommended):
```
python -m venv venv
```

3. Activate the virtual environment:
   - Windows:
   ```
   venv\Scripts\activate
   ```
   - macOS/Linux:
   ```
   source venv/bin/activate
   ```

4. Install dependencies:
```
pip install -r requirements.txt
```

## Running the Application

### Using VS Code

1. Open the project in VS Code
2. Make sure you have the Python extension installed
3. Select the "Run and Debug" sidebar (Ctrl+Shift+D)
4. Choose the "Python: Flask" configuration from the dropdown
5. Click the green play button or press F5 to start the application
6. Open your browser and navigate to http://127.0.0.1:5000/

### Using Terminal

Alternatively, you can run the application directly from the terminal:

```
python app.py
```

Then visit http://127.0.0.1:5000/ in your browser.

## Email Configuration

The application has email verification features that are configured as follows:

- Development Mode: Email sending is suppressed but functionality is preserved
- Verification links are automatically shown in the UI for testing purposes

To enable actual email sending (for production):

1. Edit app.py and modify the email configuration:
```python
app.config['MAIL_SUPPRESS_SEND'] = False  # Enable actual email sending
app.config['MAIL_USERNAME'] = 'your.email@gmail.com'  # Your Gmail address
app.config['MAIL_PASSWORD'] = 'your-app-password'     # Your Gmail app password
```

## Database

The application uses SQLite for simplicity. The database is automatically created on first run.

## License

[MIT License](LICENSE) 
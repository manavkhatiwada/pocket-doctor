# MyPocketDoctor Admin Panel

This module provides administrative functionality for the MyPocketDoctor application.

## Features

- **Dashboard**: Overview of system statistics and recent appointments
- **User Management**: View and manage user accounts
- **Appointment Management**: View, update, and manage all appointments
- **Settings**: Configure system settings and admin credentials

## Installation

The admin panel is automatically installed with the main MyPocketDoctor application.

## Usage

1. Access the admin panel at `/admin` or `/admin/login`
2. Login with the default credentials:
   - Username: `admin`
   - Password: `admin123`
3. Change the default password immediately after first login

## Security Notes

- Always change the default admin password
- Admin credentials are stored in `admin_users.json`
- Access to the admin panel should be restricted to authorized personnel only

## Development

To extend the admin functionality:

1. Add new routes to `routes.py`
2. Create templates in the `templates/admin/` directory
3. Register any new blueprints in the main `app.py`

## Structure

```
admin/
├── __init__.py          # Package initialization
├── routes.py            # Main admin routes
├── admin_routes.py      # Additional admin routes
├── admin_users.json     # Admin credentials
└── templates/           # Admin templates
    ├── admin_base.html  # Base template for admin pages
    └── admin/           # Admin-specific templates
        ├── dashboard.html
        ├── login.html
        └── ...
``` 
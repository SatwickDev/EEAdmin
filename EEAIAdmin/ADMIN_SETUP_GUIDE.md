# EEAI Admin Setup Guide

**Last Updated**: Current Implementation Complete

## Overview

The EEAI application now includes an admin role system to control access to sensitive operations. Only admin users can:
- Upload and delete files
- Connect and disconnect databases/repositories
- Manage other users (future feature)

## Initial Setup

### 1. Update Existing Users
If you have existing users in the database, run this script to give them the default 'user' role:

```bash
python update_user_roles.py
```

### 2. Create Your First Admin User
Run the admin creation script:

```bash
python create_admin_user.py
```

This will prompt you for:
- First Name
- Last Name
- Email
- Password

### 3. Environment Variables
Set these environment variables for production:

```bash
# MongoDB connection
export MONGO_URI="mongodb://localhost:27017/"
export DB_NAME="trade_finance_db"

# API base URL
export EEAI_BASE_URL="http://localhost:5000"

# Admin setup key (change this in production!)
export ADMIN_SETUP_KEY="your-secure-setup-key-here"
```

## Admin-Protected Operations

The following operations now require admin privileges:

### File Operations
- **DELETE** `/api/user-manuals/<file_name>` - Delete uploaded manuals
- **POST** `/api/compliance/upload` - Upload compliance documents

### Repository Operations
- **POST** `/api/repositories/<repo_id>/connect` - Connect to a repository
- **POST** `/api/repositories/<repo_id>/disconnect` - Disconnect from a repository

## How It Works

1. **Authentication**: Users log in normally through `/auth/login`
2. **Role Check**: The system checks the user's role from the database
3. **Admin Decorator**: Protected routes use `@admin_required` decorator
4. **Error Handling**: Non-admin users receive a 403 Forbidden error

## User Roles

- **user**: Default role for regular users
  - Can use the chat interface
  - Can view documents
  - Can query data
  
- **admin**: Administrative role
  - All user permissions plus:
  - Upload/delete files
  - Connect/disconnect databases
  - Manage repositories

## Admin Management Page

### Access the Admin Panel
1. Login as an admin user
2. Navigate to `/admin` or click the "Admin" link in the navigation (only visible to admins)
3. From here you can:
   - View all users
   - Create new users (with role selection)
   - Edit user details and roles
   - Delete users
   - View user statistics

### Admin Page Features
- **User Statistics**: Total users, admin count, regular users, active users
- **User Management**: Full CRUD operations on users
- **Search & Filter**: Search users by name/email, filter by role
- **Role Assignment**: Change user roles between 'user' and 'admin'

## Frontend Integration

The user's role is included in the authentication response:

```json
{
  "success": true,
  "user": {
    "id": "...",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com",
    "role": "admin"
  }
}
```

Frontend applications should:
1. Store the user role from login response
2. Show/hide admin features based on role
3. Handle 403 errors gracefully

### AI Chat Modern UI Updates

The `ai_chat_modern.html` template now includes:
1. **Admin Navigation**: Admin menu link (visible only to admins)
2. **Role-Based UI**: Automatic hiding of sensitive features for non-admin users:
   - Upload manual button
   - Delete manual buttons
   - Repository connect/disconnect buttons
3. **Client-Side Protection**: JavaScript checks prevent unauthorized actions
4. **Dynamic Updates**: MutationObservers ensure UI updates when content loads

## Security Notes

1. **Change the Setup Key**: The default setup key `EEAI-ADMIN-SETUP-2025` should be changed in production
2. **Secure Admin Creation**: The `/auth/create-admin` endpoint should be disabled after initial setup
3. **Audit Logging**: All admin actions are logged with user details
4. **Session Security**: Admin sessions follow the same security rules as regular users

## Troubleshooting

### "Admin privileges required" Error
- Ensure the user has 'admin' role in the database
- Check that the session is valid
- Verify the user is properly logged in

### Cannot Create Admin User
- Check the setup key is correct
- Ensure the API is running
- Verify MongoDB connection

### Existing Users Have No Role
- Run `update_user_roles.py` to migrate users
- Check MongoDB connection settings

## Repository Management

### Default Repositories
The system includes three default repositories that admins can connect:

1. **Trade Finance Repository**
   - Letters of Credit documents
   - Bank Guarantees
   - Trade Documents (Bills of Lading, Commercial Invoices)
   - Compliance Rules (UCP600, SWIFT)

2. **Treasury Repository**
   - FX Operations
   - Investment Portfolio
   - Risk Management
   - Treasury Policies

3. **Cash Management Repository**
   - Cash Flow Reports
   - Liquidity Management
   - Payment Processing
   - Bank Accounts

### Setting Up Repositories
Run the repository setup script:

```bash
python create_default_repositories.py
```

### Repository Access Control
- **Admins**: Can connect/disconnect repositories and upload documents
- **Users**: Can query connected repositories but cannot change connections

Once an admin connects a repository, all users can:
- Query documents from the connected repository
- Use uploaded manuals in their queries
- See which repository is currently connected

### Quick Setup Guide

1. Create an admin user:
```bash
python create_admin_quick.py
# Choose option 2 for quick setup (admin@eeai.com / admin123)
```

2. Create default repositories:
```bash
python create_default_repositories.py
```

3. Login as admin and:
   - Navigate to AI Chat interface
   - Connect to desired repository (Trade Finance, Treasury, or Cash Management)
   - Upload any additional training manuals

4. Regular users can then:
   - Login and access the AI Chat
   - Query against the connected repository
   - Use any uploaded manuals for enhanced responses
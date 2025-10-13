# EEAI Role System Guide

## Overview

The EEAI system now supports an extended role-based access control (RBAC) system with 6 distinct roles, each with specific permissions.

## Available Roles

### 1. Super Administrator (`super_admin`)
- **Description**: Full system access, can manage all users and system settings
- **Permissions**:
  - Manage all users
  - Manage repositories
  - Upload documents
  - Delete documents
  - System configuration
  - View all analytics
  - Manage roles

### 2. Administrator (`admin`)
- **Description**: Can manage repositories and documents
- **Permissions**:
  - Manage repositories
  - Upload documents
  - Delete documents
  - View analytics
  - Manage basic users

### 3. Manager (`manager`)
- **Description**: Can upload documents and view extended analytics
- **Permissions**:
  - Upload documents
  - View analytics
  - View all repositories
  - Export data

### 4. Analyst (`analyst`)
- **Description**: Can query and analyze data across repositories
- **Permissions**:
  - Query all repositories
  - View analytics
  - Export data
  - Create reports

### 5. Standard User (`user`)
- **Description**: Basic query access to connected repositories
- **Permissions**:
  - Query connected repository
  - View own history

### 6. Viewer (`viewer`)
- **Description**: Read-only access to specific data
- **Permissions**:
  - View public data
  - View limited analytics

## Admin Management Interface

### Accessing Admin Panel
1. Login with an admin role (super_admin, admin, or manager)
2. Navigate to `/admin` or click "Admin" in navigation
3. Access the enhanced admin management interface

### Features
- **User Management Tab**:
  - View all users with their roles
  - Change user roles via dropdown
  - Create new users with role assignment
  - Edit user details
  - Delete users
  - Search and filter users

- **Roles & Permissions Tab**:
  - View all system roles
  - See detailed permissions for each role
  - Visual role distribution chart
  - Permission tags for clarity

### Quick Setup

1. **Run the role setup script**:
```bash
python add_admin_and_roles.py
```

2. **Choose option 6 for complete setup**:
- Creates roles collection
- Adds predefined admin users
- Updates existing users with permissions

3. **Default Admin Users Created**:
- `superadmin@eeai.com` (password: SuperAdmin@123) - Super Admin
- `trade.admin@eeai.com` (password: TradeAdmin@123) - Admin
- `treasury.manager@eeai.com` (password: TreasuryMgr@123) - Manager
- `cash.analyst@eeai.com` (password: CashAnalyst@123) - Analyst

## Using Permissions in Code

### Check for Admin Access
```python
@admin_required  # Allows super_admin, admin, and manager roles
def admin_only_route():
    pass
```

### Check for Specific Permission
```python
@permission_required('upload_documents')
def upload_route():
    pass
```

### Frontend Role Checking
```javascript
// In Vue.js components
if (user.role === 'admin' || user.role === 'super_admin') {
    // Show admin features
}

// Check specific permissions
if (user.permissions.includes('upload_documents')) {
    // Show upload button
}
```

## Migration Guide

### Update Existing Users
If you have existing users, run:
```bash
python add_admin_and_roles.py
# Choose option 5: Update existing users with permissions
```

### Manual Role Assignment
1. Login to admin panel
2. Go to User Management tab
3. Use dropdown to change user roles
4. Changes are saved automatically

## Security Notes

1. **Role Hierarchy**: super_admin > admin > manager > analyst > user > viewer
2. **Permission Inheritance**: Higher roles don't automatically inherit lower role permissions
3. **Audit Trail**: All role changes are logged
4. **Session Security**: Role changes require re-authentication on next login

## API Endpoints

### Role Management
- `GET /api/admin/users` - List all users (admin only)
- `POST /api/admin/users` - Create new user with role
- `PUT /api/admin/users/{id}` - Update user details
- `PUT /api/admin/users/{id}/role` - Update user role only
- `DELETE /api/admin/users/{id}` - Delete user

### Permission Checking
- `GET /auth/protected` - Returns user info with role and permissions
- Frontend automatically checks permissions on login

## Best Practices

1. **Principle of Least Privilege**: Assign minimum required role
2. **Regular Audits**: Review user roles periodically
3. **Role Assignment**: Use Manager role for department heads
4. **Analytics Access**: Use Analyst role for data teams
5. **External Users**: Use Viewer role for limited access
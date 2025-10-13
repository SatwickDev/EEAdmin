# EEAI Quick Setup Guide

## Prerequisites
1. Ensure MongoDB is running
2. Ensure all Python dependencies are installed
3. Start the Flask server

## Setup Steps

### 1. Start the Application
```bash
# In one terminal, start the Flask server
python run.py
```

### 2. Create Admin User
```bash
# In another terminal, create admin user
python create_admin_auto.py

# Or use the interactive version:
python create_admin_quick.py
# Choose option 2 for quick setup (admin@eeai.com / admin123)
```

### 3. Create Default Repositories
```bash
# Create the three default repositories
python create_repositories_auto.py

# Or use the interactive version:
python create_default_repositories.py
```

### 4. Login and Configure
1. Open browser to http://localhost:5000/
2. Login with:
   - Email: admin@eeai.com
   - Password: admin123
3. Navigate to AI Chat interface
4. As admin, you can:
   - Connect to Trade Finance, Treasury, or Cash Management repository
   - Upload training manuals
   - These will be available for all users

### 5. Regular User Access
Regular users can:
- Login and access AI Chat
- Query the connected repository
- Use uploaded manuals
- Cannot change repository connections or upload files

## Default Credentials (CHANGE IN PRODUCTION!)
- Admin Email: admin@eeai.com
- Admin Password: admin123

## Available Repositories
1. **Trade Finance** - LC, Bank Guarantees, Trade Documents
2. **Treasury** - FX, Investments, Risk Management
3. **Cash Management** - Cash Flow, Liquidity, Payments
# Admin Login Steps

## You're Getting "Authentication Required" Because:
You need to be logged in first before accessing `/admin`. Follow these steps:

## Step 1: Login First
1. Go to: **http://localhost:5000/**
2. Login with your existing account:
   - Email: ilyashussain9@gmail.com
   - Password: (your password)

## Step 2: Update Your Account to Admin

### Option A: Using MongoDB Shell (Recommended)
```bash
# Open MongoDB shell
mongo

# Switch to database
use trade_finance_db

# Update YOUR account to admin
db.users.updateOne(
  {email: "ilyashussain9@gmail.com"},
  {$set: {
    role: "admin",
    permissions: [
      "manage_repositories",
      "upload_documents", 
      "delete_documents",
      "view_analytics",
      "manage_basic_users"
    ]
  }}
)

# Verify it worked
db.users.findOne({email: "ilyashussain9@gmail.com"})
# Should show: role: "admin"
```

### Option B: Using MongoDB Compass GUI
1. Open MongoDB Compass
2. Connect to localhost:27017
3. Go to: trade_finance_db → users
4. Find your user (ilyashussain9@gmail.com)
5. Click Edit
6. Change `role` from "user" to "admin"
7. Add the permissions array
8. Save

## Step 3: Logout and Login Again
1. After updating your role in MongoDB
2. Logout from the web interface (if logged in)
3. Login again with same credentials
4. NOW you should see "Admin" in the navigation

## Step 4: Access Admin Panel
1. Click "Admin" in navigation
2. OR go directly to: http://localhost:5000/admin
3. You should now see the admin management panel

## Alternative: Create a New Admin Account

If updating doesn't work, create a new admin in MongoDB:

```javascript
// In MongoDB shell
use trade_finance_db

// First, let's see what password hash format is used
db.users.findOne({}, {passwordHash: 1})

// Create new admin (you'll need to generate password hash)
db.users.insertOne({
  firstName: "Admin",
  lastName: "User", 
  email: "admin@eeai.com",
  passwordHash: "copy_a_hash_from_existing_user", // TEMPORARY
  role: "admin",
  createdAt: new Date(),
  isActive: true,
  permissions: [
    "manage_repositories",
    "upload_documents",
    "delete_documents", 
    "view_analytics",
    "manage_basic_users"
  ]
})
```

## Quick Troubleshooting

### Still getting "Authentication required"?
- Make sure you're logged in first at http://localhost:5000/
- Check browser console for any errors
- Try clearing cookies and logging in again

### Getting "Admin privileges required" instead?
- Your account is recognized but not admin
- Go back to Step 2 and update role in MongoDB
- Make sure to logout and login again after role change

### Can't see "Admin" link after login?
- The role wasn't updated properly
- Check in MongoDB: `db.users.findOne({email: "your-email"})`
- Should show `role: "admin"`

## The Key Points:
1. **You must be logged in first** (that's why you see "Authentication required")
2. **Your logged-in account must have admin role**
3. **After changing role in DB, logout and login again**

The `/admin` page has two checks:
- First: Are you logged in? (Currently failing here)
- Second: Are you an admin?

You need to pass both checks!
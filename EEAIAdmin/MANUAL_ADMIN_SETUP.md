# Manual Admin Setup Instructions

Since the server is running on a different network configuration, here are manual steps to set up admin access:

## Option 1: Update Existing User to Admin

### MongoDB Shell Commands
```bash
# Connect to MongoDB
mongo

# Switch to the database
use trade_finance_db

# Find the user by email
db.users.findOne({email: "ilyashussain9@gmail.com"})

# Update the user's role to admin
db.users.updateOne(
  {email: "ilyashussain9@gmail.com"},
  {$set: {role: "admin"}}
)

# Verify the update
db.users.findOne({email: "ilyashussain9@gmail.com"})
```

## Option 2: Use MongoDB Compass
1. Open MongoDB Compass
2. Connect to your MongoDB instance
3. Navigate to `trade_finance_db` > `users` collection
4. Find the user with email "ilyashussain9@gmail.com"
5. Edit the document and add/update field: `role: "admin"`
6. Save the changes

## Option 3: Create Admin via API (if server allows external connections)
```python
import requests

# Try with the actual server address
response = requests.post(
    "http://YOUR_SERVER_IP:5000/auth/create-admin",
    json={
        "firstName": "Admin",
        "lastName": "User",
        "email": "admin@eeai.com",
        "password": "admin123",
        "setupKey": "EEAI-ADMIN-SETUP-2025"
    }
)
print(response.json())
```

## Creating Default Repositories

### MongoDB Shell Commands
```javascript
use trade_finance_db

// Insert Trade Finance repository
db.repositories.insertOne({
  id: "trade_finance",
  name: "Trade Finance",
  description: "Repository for trade finance documents including Letters of Credit, Bank Guarantees, and trade compliance documents",
  type: "trade_finance",
  collections: [
    {
      name: "Letters of Credit",
      description: "LC documents and related trade finance instruments",
      document_count: 0
    },
    {
      name: "Bank Guarantees",
      description: "Bank guarantee documents and compliance checks",
      document_count: 0
    },
    {
      name: "Trade Documents",
      description: "Bills of Lading, Commercial Invoices, and other trade documents",
      document_count: 0
    },
    {
      name: "Compliance Rules",
      description: "UCP600, SWIFT, and other compliance rule documents",
      document_count: 0
    }
  ],
  created_at: new Date(),
  updated_at: new Date(),
  status: "active",
  connected: false,
  connected_users: []
})

// Insert Treasury repository
db.repositories.insertOne({
  id: "treasury",
  name: "Treasury",
  description: "Repository for treasury management including foreign exchange, investments, and risk management",
  type: "treasury",
  collections: [
    {
      name: "FX Operations",
      description: "Foreign exchange transactions and hedging documents",
      document_count: 0
    },
    {
      name: "Investment Portfolio",
      description: "Investment policies, portfolio reports, and analytics",
      document_count: 0
    },
    {
      name: "Risk Management",
      description: "Risk assessment reports and mitigation strategies",
      document_count: 0
    },
    {
      name: "Treasury Policies",
      description: "Internal treasury policies and procedures",
      document_count: 0
    }
  ],
  created_at: new Date(),
  updated_at: new Date(),
  status: "active",
  connected: false,
  connected_users: []
})

// Insert Cash Management repository
db.repositories.insertOne({
  id: "cash_management",
  name: "Cash Management",
  description: "Repository for cash management operations including liquidity, cash flow, and payment processing",
  type: "cash_management",
  collections: [
    {
      name: "Cash Flow Reports",
      description: "Daily, weekly, and monthly cash flow reports",
      document_count: 0
    },
    {
      name: "Liquidity Management",
      description: "Liquidity forecasts and optimization strategies",
      document_count: 0
    },
    {
      name: "Payment Processing",
      description: "Payment instructions and transaction records",
      document_count: 0
    },
    {
      name: "Bank Accounts",
      description: "Bank account management and reconciliation",
      document_count: 0
    }
  ],
  created_at: new Date(),
  updated_at: new Date(),
  status: "active",
  connected: false,
  connected_users: []
})

// Verify repositories were created
db.repositories.find().pretty()
```

## After Setup

1. **Current user (ilyashussain9@gmail.com) becomes admin**:
   - Can access /admin page
   - Can upload manuals in AI Chat
   - Can connect/disconnect repositories

2. **Login and test**:
   - Go to AI Chat interface
   - You should see repository connect/disconnect buttons
   - You should see the upload manual button
   - Admin link should appear in navigation

3. **Connect a repository**:
   - Choose Trade Finance, Treasury, or Cash Management
   - Click Connect button
   - All users will then be able to query this repository

## Verification

To verify the user has admin role:
```javascript
// In MongoDB shell
use trade_finance_db
db.users.findOne({email: "ilyashussain9@gmail.com"})
// Should show: role: "admin"
```

To verify repositories exist:
```javascript
db.repositories.count()
// Should return 3
```
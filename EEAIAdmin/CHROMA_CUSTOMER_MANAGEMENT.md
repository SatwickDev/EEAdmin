# Chroma DB Per-Customer Management Guide

## Overview

This guide explains how to enable/disable ChromaDB services for individual customers or globally in your multi-tenant application. The system is based on `repository_config` MongoDB collection which stores Chroma configuration per customer.

---

## Architecture

### Configuration Storage

Chroma configuration is stored in MongoDB collection: **`repository_config`**

**Document Structure:**
```json
{
  "_id": "ObjectId",
  "type": "chromadb",
  "host": "localhost",
  "port": 8000,
  "is_active": true,
  "enabled_for_all": false,
  "customers": ["bank1", "bank2"],
  "allowed_customers": ["bank1", "bank2"],
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T10:00:00Z"
}
```

**Fields:**
- `type`: Always `"chromadb"` for Chroma configuration
- `host`: Chroma server hostname (default: `localhost`)
- `port`: Chroma server port (default: `8000`)
- `is_active`: Boolean to activate/deactivate Chroma globally
- `enabled_for_all`: If `true`, all customers can use Chroma
- `customers` / `allowed_customers`: List of customer IDs allowed to use Chroma (if `enabled_for_all` is `false`)

---

## Admin API Endpoints

### 1. Get All Chroma Configurations

**Endpoint:** `GET /api/admin/repository_config`

**Authentication:** Admin user only (checked via `check_admin_access()`)

**Response:**
```json
{
  "success": true,
  "configs": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "type": "chromadb",
      "host": "localhost",
      "port": 8000,
      "is_active": true,
      "enabled_for_all": false,
      "customers": ["bank1", "bank2"]
    }
  ]
}
```

**Example cURL:**
```bash
curl -X GET http://localhost:5000/api/admin/repository_config \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json"
```

---

### 2. Create or Update Chroma Configuration

**Endpoint:** `POST/PUT /api/admin/repository_config`

**Authentication:** Admin user only

**Request Body:**
```json
{
  "type": "chromadb",
  "host": "localhost",
  "port": 8000,
  "is_active": true,
  "enabled_for_all": false,
  "customers": ["bank1", "bank2", "bank3"]
}
```

**Response:**
```json
{
  "success": true,
  "matched_count": 1,
  "upserted_id": "507f1f77bcf86cd799439011"
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "localhost",
    "port": 8000,
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank2"]
  }'
```

---

## Use Cases & Examples

### Use Case 1: Enable Chroma for All Customers

**MongoDB Query:**
```javascript
db.repository_config.updateOne(
  { type: "chromadb" },
  {
    $set: {
      type: "chromadb",
      host: "localhost",
      port: 8000,
      is_active: true,
      enabled_for_all: true,
      customers: [],
      updated_at: new Date()
    }
  },
  { upsert: true }
)
```

**Admin API Request:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "localhost",
    "port": 8000,
    "is_active": true,
    "enabled_for_all": true,
    "customers": []
  }'
```

---

### Use Case 2: Disable Chroma for a Specific Customer

**MongoDB Query:**
```javascript
db.repository_config.updateOne(
  { type: "chromadb" },
  {
    $set: {
      enabled_for_all: false,
      customers: ["bank1", "bank3"]  // bank2 is excluded
    }
  }
)
```

**Admin API Request:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank3"]
  }'
```

---

### Use Case 3: Disable Chroma Globally

**MongoDB Query:**
```javascript
db.repository_config.updateOne(
  { type: "chromadb" },
  {
    $set: {
      is_active: false,
      updated_at: new Date()
    }
  }
)
```

**Admin API Request:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": false
  }'
```

---

### Use Case 4: Switch Chroma to Different Host

**MongoDB Query:**
```javascript
db.repository_config.updateOne(
  { type: "chromadb" },
  {
    $set: {
      host: "chroma-prod.example.com",
      port: 9000,
      updated_at: new Date()
    }
  }
)
```

**Admin API Request:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "chroma-prod.example.com",
    "port": 9000,
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank2", "bank3"]
  }'
```

---

## Programmatic Usage

### Check if Chroma is Enabled for a Customer

**Python Code:**
```python
from app.utils.chroma_manager import is_chroma_enabled_for_customer
from app import db

customer_id = "bank1"
enabled = is_chroma_enabled_for_customer(customer_id=customer_id, db=db)

if enabled:
    print(f"Chroma is enabled for {customer_id}")
else:
    print(f"Chroma is disabled for {customer_id}")
```

---

### Get Chroma Client for a Customer

**Python Code:**
```python
from app.utils.chroma_manager import get_chroma_client_for_customer, get_request_customer_id
from app import db
from flask import request

# Option 1: From request context
customer_id = get_request_customer_id(request)
chroma_client = get_chroma_client_for_customer(customer_id=customer_id, db=db)

if chroma_client:
    # Use Chroma
    collection = chroma_client.get_or_create_collection("my_collection")
    print(f"Connected to Chroma for {customer_id}")
else:
    print(f"Chroma is not available for {customer_id}")
```

---

### How Customer ID is Resolved

The system resolves customer ID in this order:

1. **Request Header:** `X-Customer-ID`
2. **Query Parameter:** `?customer_id=bank1`
3. **Session Variable:** `session['customer_id']` or `session['repository_id']`
4. **Environment Variable:** (if no request context)

**Example:**
```bash
# Via Header
curl -H "X-Customer-ID: bank1" http://localhost:5000/api/some-endpoint

# Via Query Parameter
curl http://localhost:5000/api/some-endpoint?customer_id=bank1

# Via Session (automatically set on login)
```

---

## Behavior & Fallback

### What Happens When Chroma is Disabled for a Customer?

1. **Manual Document Indexing:** Skipped with log entry `QUERY_SKIPPED`
2. **Manual Document Queries:** Empty results returned, execution continues
3. **Error Handling:** Graceful errors logged; application continues normally

**Log Example:**
```
DEBUG: Chroma is not available for customer bank2 - skipping index operation
DEBUG: Manual collection query skipped for bank2 (Chroma disabled)
```

---

### Connection Efficiency

- **Per-Request:** Only ONE MongoDB connection read per request (for `repository_config` lookup)
- **Reuse:** Flask app's persistent `db` connection used when available
- **Fallback:** Temporary connection created only if app context unavailable
- **No Caching:** Config is read fresh each request (allows real-time changes)

---

## Monitoring & Debugging

### Check Current Chroma Status

**MongoDB Query:**
```javascript
db.repository_config.findOne({ type: "chromadb" })
```

**Python Script:**
```python
from pymongo import MongoClient
import json

client = MongoClient("mongodb://localhost:27017/")
db = client["finai_chatbot"]
config = db.repository_config.find_one({"type": "chromadb"})

if config:
    print("Current Chroma Configuration:")
    print(json.dumps(config, indent=2, default=str))
else:
    print("No Chroma configuration found")
```

---

### Verify Customer Access

**Python Script:**
```python
from app.utils.chroma_manager import is_chroma_enabled_for_customer
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["finai_chatbot"]

customers = ["bank1", "bank2", "bank3"]
for cust_id in customers:
    enabled = is_chroma_enabled_for_customer(customer_id=cust_id, db=db)
    status = "✓ ENABLED" if enabled else "✗ DISABLED"
    print(f"{cust_id}: {status}")
```

---

## Initial Setup

### 1. Create Default Chroma Configuration

Run this once during application setup:

**MongoDB Command:**
```javascript
db.repository_config.insertOne({
  type: "chromadb",
  host: "localhost",
  port: 8000,
  is_active: true,
  enabled_for_all: true,
  customers: [],
  created_at: new Date(),
  updated_at: new Date()
})
```

**Python Script:**
```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["finai_chatbot"]

# Create default config
db.repository_config.update_one(
    {"type": "chromadb"},
    {
        "$set": {
            "type": "chromadb",
            "host": "localhost",
            "port": 8000,
            "is_active": True,
            "enabled_for_all": True,
            "customers": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    },
    upsert=True
)
print("Default Chroma configuration created")
```

---

## Troubleshooting

### Issue: Chroma client is None for a customer

**Check:**
1. Is Chroma server running on the configured host/port?
2. Is the customer ID in the allowlist?
3. Is `is_active` set to `true` and `enabled_for_all` true or customer in list?

**Debug:**
```python
from app.utils.chroma_manager import is_chroma_enabled_for_customer
from app import db

cust_id = "bank1"
print(f"Enabled: {is_chroma_enabled_for_customer(cust_id, db)}")

# Check config
config = db.repository_config.find_one({"type": "chromadb"})
print(f"Config: {config}")
```

---

### Issue: Changes not taking effect immediately

**Cause:** Config is read fresh per request. Restart the application if caching is enabled.

**Solution:** No caching by default; changes should be instant.

---

## Performance Considerations

- **Startup:** ~50ms per request (one MongoDB query for config)
- **Chroma Operations:** Only executed if enabled for customer
- **Memory:** Minimal impact (no caching, no connection pooling overhead)
- **Scalability:** Scales to thousands of customers (O(1) lookup per request)

---

## Security Notes

- **Admin Endpoints:** Protected by `check_admin_access()` — requires admin email
- **Customer Isolation:** Each customer can only access their own enabled collections
- **No Credentials in Config:** Host/port stored; credentials must be set via environment
- **Audit Trail:** Consider adding audit logging to track config changes

---

## Summary

| Task | Method |
|------|--------|
| Enable for all | `POST /api/admin/repository_config` with `enabled_for_all: true` |
| Enable for specific customers | `POST /api/admin/repository_config` with customer list |
| Disable globally | `POST /api/admin/repository_config` with `is_active: false` |
| Check status | `GET /api/admin/repository_config` |
| Programmatic check | `is_chroma_enabled_for_customer(cust_id, db)` |
| Get client | `get_chroma_client_for_customer(cust_id, db)` |

---

## Additional Resources

- **Chroma Documentation:** https://docs.trychroma.com/
- **MongoDB Queries:** See examples in this guide
- **Flask Request Context:** Customer ID extracted automatically from headers/params

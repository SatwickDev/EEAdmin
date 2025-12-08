# Quick Reference: Enable/Disable Chroma for Customers

## TL;DR - Three Ways to Manage Chroma

### Option 1: Python Setup Script (Easiest)

```bash
# Enable for all customers
python setup_chroma_config.py --enable-all

# Enable for specific customers
python setup_chroma_config.py --customers bank1,bank2,bank3

# Disable globally
python setup_chroma_config.py --disable
```

### Option 2: Admin API Endpoints (For web UI)

**Enable for all:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": true,
    "enabled_for_all": true
  }'
```

**Enable for specific customers:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank2"]
  }'
```

**Disable globally:**
```bash
curl -X POST http://localhost:5000/api/admin/repository_config \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": false
  }'
```

**Check status:**
```bash
curl -X GET http://localhost:5000/api/admin/repository_config
```

### Option 3: MongoDB Direct (Advanced)

```javascript
// Enable for all customers
db.repository_config.updateOne(
  { type: "chromadb" },
  {
    $set: {
      is_active: true,
      enabled_for_all: true,
      customers: []
    }
  },
  { upsert: true }
)

// Enable for specific customers
db.repository_config.updateOne(
  { type: "chromadb" },
  {
    $set: {
      is_active: true,
      enabled_for_all: false,
      customers: ["bank1", "bank2", "bank3"]
    }
  },
  { upsert: true }
)

// Disable globally
db.repository_config.updateOne(
  { type: "chromadb" },
  { $set: { is_active: false } }
)

// Check current status
db.repository_config.findOne({ type: "chromadb" })
```

---

## Quick Scenarios

| Scenario | Command |
|----------|---------|
| **Enable Chroma for all** | `python setup_chroma_config.py --enable-all` |
| **Disable bank2 only** | `python setup_chroma_config.py --customers bank1,bank3` |
| **Turn off Chroma completely** | `python setup_chroma_config.py --disable` |
| **Add new customer (bank4)** | `python setup_chroma_config.py --customers bank1,bank2,bank3,bank4` |
| **Switch to prod Chroma server** | Edit MongoDB doc: change `host: "chroma-prod.example.com"` |
| **Check who has access** | Run tests: `python test_chroma_customer_management.py` |

---

## What Gets Disabled?

When Chroma is **disabled for a customer**:

✓ Vector embeddings for manual documents: **Not indexed**
✓ Manual document retrieval: **Skipped gracefully**
✓ Chroma queries: **Return empty results**
✓ Application: **Continues working normally**

**Logs show:** `DEBUG: Chroma is not available for customer X - skipping...`

---

## Testing & Verification

### Run Full Test Suite
```bash
python test_chroma_customer_management.py
```

This tests:
- ✓ MongoDB connection
- ✓ Enable all customers
- ✓ Enable specific customers only
- ✓ Disable globally
- ✓ Client resolution
- ✓ Configuration retrieval
- ✓ Admin endpoint simulation

### Quick Verification
```python
from app.utils.chroma_manager import is_chroma_enabled_for_customer
from app import db

# Check bank1
if is_chroma_enabled_for_customer("bank1", db):
    print("✓ bank1 can use Chroma")
else:
    print("✗ bank1 is disabled")
```

---

## Common Issues & Fixes

### Issue: Changes not taking effect
**Solution:** Changes are instant (no caching). Restart only if caching is enabled.

### Issue: Chroma client is None
**Check:**
1. Is Chroma server running? (`curl localhost:8000/api/v1/heartbeat`)
2. Is customer in allowlist? (Check MongoDB doc)
3. Is `is_active: true`?

### Issue: "Admin access required" error
**Solution:** API requires admin login. Check `check_admin_access()` function for admin emails.

---

## Files Included

| File | Purpose |
|------|---------|
| `CHROMA_CUSTOMER_MANAGEMENT.md` | Full documentation with examples |
| `setup_chroma_config.py` | CLI tool to enable/disable Chroma |
| `test_chroma_customer_management.py` | Comprehensive test suite |
| `curl_examples.sh` | Copy-paste curl commands |
| `CHROMA_QUICK_REFERENCE.md` | This file |

---

## Next Steps

1. **Initial Setup:**
   ```bash
   python setup_chroma_config.py --enable-all
   ```

2. **Test:**
   ```bash
   python test_chroma_customer_management.py
   ```

3. **For Each Customer:**
   ```bash
   python setup_chroma_config.py --customers bank1,bank2,bank3
   ```

4. **Monitor:**
   Check application logs for `Chroma` messages

---

## Support

For issues:
1. Check MongoDB: `db.repository_config.findOne({ type: "chromadb" })`
2. Check logs: Search for `chroma_manager`
3. Run tests: `python test_chroma_customer_management.py`
4. See full docs: `CHROMA_CUSTOMER_MANAGEMENT.md`

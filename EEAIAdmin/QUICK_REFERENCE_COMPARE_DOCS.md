# Quick Reference: `/api/compare-documents`

## 🎯 What It Does

Compares uploaded documents against required documents and returns:
- ✅ **Matched** documents (with confidence score)
- ❌ **Missing** documents (required but not uploaded)
- ⚠️ **Extra** documents (uploaded but not required)

---

## 🔌 Quick Integration

### Frontend Code (Vue.js)

```javascript
async compareDocuments() {
  const required = this.getAllRequiredDocuments();
  const uploaded = this.results.map(r => ({
    documentType: r.documentType,
    fileName: r.fileName,
    classification: r.classification
  }));

  const res = await fetch('/api/compare-documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      required_documents: required,
      uploaded_documents: uploaded
    })
  });

  const result = await res.json();
  console.log(`Matched: ${result.summary.matched}`);
  console.log(`Missing: ${result.summary.missing}`);
  console.log(`Completeness: ${result.summary.completeness}%`);
}
```

---

## 📋 Request Format

```javascript
{
  "required_documents": [
    { "name": "Commercial Invoice", "priority": "Mandatory", "description": "..." },
    { "name": "Bill of Lading", "priority": "Mandatory", "description": "..." }
  ],
  "uploaded_documents": [
    { "documentType": "Invoice", "fileName": "inv.pdf", "classification": {...} },
    { "documentType": "Bill of Lading", "fileName": "bol.pdf", "classification": {...} }
  ]
}
```

---

## 📊 Response Format

```javascript
{
  "success": true,
  "comparison": {
    "matched": [...],      // Documents that matched
    "missing": [...],      // Required but not uploaded
    "extra": [...]         // Uploaded but not required
  },
  "summary": {
    "total_required": 3,
    "total_uploaded": 2,
    "matched": 2,
    "missing": 1,
    "extra": 0,
    "completeness": 66.7,  // Percentage
    "status": "incomplete" // complete | mostly_complete | incomplete | complete_with_extra
  }
}
```

---

## 🎯 Match Confidence Levels

| Level | Score | Reason |
|-------|-------|--------|
| Exact Match | 1.0 | Document type exactly matches |
| Fuzzy Match | 0.95 | One type contains the other |
| Alias Match | 0.90 | Using document aliases (B/L → Bill of Lading) |
| Sub-type Match | 0.85 | Classification sub_type matches |
| Filename Match | 0.75 | Filename contains document name |
| No Match | < 0.70 | Not included in results |

---

## 📌 Common Document Aliases

| Type | Aliases |
|------|---------|
| Commercial Invoice | invoice, proforma invoice, sales invoice |
| Bill of Lading | b/l, bl, ocean bol, sea waybill |
| Packing List | packing slip, pack list, packaging |
| Certificate of Origin | origin cert, coo, c/o |
| Insurance Cert | insurance policy, insurance doc |
| Bank Guarantee | bg, guarantee, sblc |
| Letter of Credit | lc, l/c, documentary credit |

---

## ✅ Typical Workflow

```
User uploads documents
         ↓
System classifies documents
         ↓
Call /api/compare-documents
         ↓
Display Results:
  ✅ 3 matched documents
  ❌ 1 missing (Packing List)
  ⚠️ 0 extra documents
  📈 75% complete
         ↓
User uploads Packing List
         ↓
Call /api/compare-documents again
         ↓
Display Results:
  ✅ 4 matched documents
  ❌ 0 missing
  ⚠️ 0 extra documents
  📈 100% complete ✅
```

---

## 🚀 Usage Examples

### Example 1: Check If Documents Are Complete

```javascript
const result = await fetch('/api/compare-documents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    required_documents: [
      { name: "Invoice", priority: "Mandatory" },
      { name: "BOL", priority: "Mandatory" },
      { name: "Packing List", priority: "Mandatory" }
    ],
    uploaded_documents: [
      { documentType: "Invoice", fileName: "inv.pdf" },
      { documentType: "Bill of Lading", fileName: "bol.pdf" }
    ]
  })
}).then(r => r.json());

if (result.summary.missing === 0) {
  console.log("✅ All documents uploaded!");
} else {
  console.log(`❌ Missing ${result.summary.missing} documents`);
}
```

### Example 2: Show Missing Documents to User

```javascript
const result = await compareDocuments();

if (result.comparison.missing.length > 0) {
  const missing = result.comparison.missing
    .map(m => m.document.name)
    .join(', ');
  alert(`Missing documents: ${missing}`);
}
```

### Example 3: Calculate Upload Progress

```javascript
const result = await compareDocuments();
const progress = result.summary.completeness;

document.querySelector('.progress-bar').style.width = progress + '%';
document.querySelector('.progress-text').innerText = `${Math.round(progress)}% complete`;
```

---

## 🔧 Testing

### Quick Test with curl

```bash
curl -X POST http://localhost:5000/api/compare-documents \
  -H "Content-Type: application/json" \
  -d '{
    "required_documents": [
      {"name": "Invoice", "priority": "Mandatory"}
    ],
    "uploaded_documents": [
      {"documentType": "Invoice", "fileName": "inv.pdf"}
    ]
  }'
```

### Test with Python Script

```bash
python test_compare_documents_endpoint.py
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| Nothing matches | Check document names spelling, use `COMPARE_DOCUMENTS_API.md` aliases section |
| Low confidence | Try uploading with classification data (documentType, fileName) |
| "Missing" not detected | Verify required_documents array format |
| API error | Check logs in server output, verify JSON format |

---

## 📚 Full Documentation

See `COMPARE_DOCUMENTS_API.md` for:
- Complete API reference
- All response field explanations
- Advanced examples
- Error handling patterns
- Integration strategies

---

## 📝 Summary

**Endpoint**: `/api/compare-documents`  
**Method**: POST  
**Purpose**: Compare uploaded vs required documents  
**Status**: ✅ Ready to use  
**Files**: `app/routes.py`  
**Test**: `test_compare_documents_endpoint.py`  
**Docs**: `COMPARE_DOCUMENTS_API.md`

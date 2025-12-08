# Compare Documents API

## Endpoint: `/api/compare-documents`

This endpoint compares uploaded documents against required documents and returns matching status, missing documents, and extra documents.

## Method
**POST**

## Purpose
Compare a list of uploaded documents against a list of required documents to identify:
- **Matched**: Documents that successfully match required documents
- **Missing**: Required documents that were not uploaded
- **Extra**: Uploaded documents that are not in the required list

---

## Request Body

```json
{
  "required_documents": [
    {
      "name": "Commercial Invoice",
      "priority": "Mandatory",
      "description": "Invoice details from supplier"
    },
    {
      "name": "Bill of Lading",
      "priority": "Mandatory",
      "description": "Ocean Bill of Lading for shipment"
    },
    {
      "name": "Packing List",
      "priority": "Mandatory",
      "description": "Detailed packing and contents"
    }
  ],
  "uploaded_documents": [
    {
      "documentType": "Invoice",
      "fileName": "invoice_2024.pdf",
      "classification": {
        "category": "Financial Processes",
        "sub_type": "Commercial Invoice"
      }
    },
    {
      "documentType": "Bill of Lading",
      "fileName": "bol_ocean.pdf",
      "classification": {
        "category": "Transport Processes",
        "sub_type": "Ocean Bill of Lading"
      }
    }
  ]
}
```

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `required_documents` | Array | Yes | List of required documents from LC or purchase order |
| `uploaded_documents` | Array | Yes | List of documents uploaded by user |

### Required Document Fields
- `name` (string): Document name (e.g., "Commercial Invoice")
- `priority` (string): "Mandatory" or "Optional"
- `description` (string, optional): Document description

### Uploaded Document Fields
- `documentType` (string): Classified document type
- `fileName` (string): Original filename
- `classification` (object, optional): Classification details with `category`, `sub_type`

---

## Response

### Success Response

```json
{
  "success": true,
  "comparison": {
    "matched": [
      {
        "required": {
          "name": "Commercial Invoice",
          "priority": "Mandatory",
          "description": "Invoice details from supplier"
        },
        "uploaded": {
          "documentType": "Invoice",
          "fileName": "invoice_2024.pdf",
          "classification": {...}
        },
        "confidence": 1.0,
        "reason": "Exact match on document type",
        "uploaded_index": 0
      },
      {
        "required": {
          "name": "Bill of Lading",
          "priority": "Mandatory",
          "description": "Ocean Bill of Lading for shipment"
        },
        "uploaded": {
          "documentType": "Bill of Lading",
          "fileName": "bol_ocean.pdf",
          "classification": {...}
        },
        "confidence": 1.0,
        "reason": "Exact match on document type",
        "uploaded_index": 1
      }
    ],
    "missing": [
      {
        "document": {
          "name": "Packing List",
          "priority": "Mandatory",
          "description": "Detailed packing and contents"
        },
        "reason": "Not uploaded",
        "priority": "Mandatory"
      }
    ],
    "extra": []
  },
  "summary": {
    "total_required": 3,
    "total_uploaded": 2,
    "matched": 2,
    "missing": 1,
    "extra": 0,
    "completeness": 66.7,
    "status": "incomplete"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

---

## Response Fields

### Matched Documents
| Field | Type | Description |
|-------|------|-------------|
| `required` | Object | The required document specification |
| `uploaded` | Object | The uploaded document that matched |
| `confidence` | Number | Match confidence (0.0 to 1.0) |
| `reason` | String | Explanation of why/how it matched |
| `uploaded_index` | Number | Index in uploaded_documents array |

### Missing Documents
| Field | Type | Description |
|-------|------|-------------|
| `document` | Object | The required document that is missing |
| `reason` | String | Why it's missing (always "Not uploaded") |
| `priority` | String | Priority level (Mandatory/Optional) |

### Extra Documents
| Field | Type | Description |
|-------|------|-------------|
| `document` | Object | The uploaded document not in requirements |
| `reason` | String | Why it's extra (always "Not in required documents list") |

### Summary
| Field | Type | Description |
|-------|------|-------------|
| `total_required` | Number | Total required documents |
| `total_uploaded` | Number | Total uploaded documents |
| `matched` | Number | Number of matched documents |
| `missing` | Number | Number of missing required documents |
| `extra` | Number | Number of extra uploaded documents |
| `completeness` | Number | Percentage of required documents found (0-100) |
| `status` | String | Overall status: "complete", "complete_with_extra", "mostly_complete", "incomplete" |

---

## Match Confidence Levels

The endpoint uses intelligent matching with the following confidence tiers:

| Confidence | Reason |
|------------|--------|
| **1.0 (100%)** | Exact match on document type |
| **0.95 (95%)** | Type contains or is contained in requirement (fuzzy match) |
| **0.90 (90%)** | Alias match (e.g., "Bill of Lading" matches "B/L") |
| **0.85 (85%)** | Sub-type match from classification |
| **0.75 (75%)** | Filename contains document name |
| **< 0.70 (< 70%)** | No match (not included in results) |

---

## Usage Examples

### Example 1: Simple Invoice and BOL Comparison

```bash
curl -X POST http://localhost:5000/api/compare-documents \
  -H "Content-Type: application/json" \
  -d '{
    "required_documents": [
      {"name": "Commercial Invoice", "priority": "Mandatory"},
      {"name": "Bill of Lading", "priority": "Mandatory"}
    ],
    "uploaded_documents": [
      {"documentType": "Invoice", "fileName": "invoice.pdf"},
      {"documentType": "Bill of Lading", "fileName": "bol.pdf"}
    ]
  }'
```

### Example 2: Finding Missing Documents

```javascript
const response = await fetch('/api/compare-documents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    required_documents: [
      { name: "Commercial Invoice", priority: "Mandatory" },
      { name: "Packing List", priority: "Mandatory" },
      { name: "Insurance Certificate", priority: "Optional" }
    ],
    uploaded_documents: [
      { documentType: "Invoice", fileName: "inv.pdf" }
    ]
  })
});

const result = await response.json();

if (result.success) {
  console.log(`Missing: ${result.comparison.missing.length} documents`);
  result.comparison.missing.forEach(m => {
    console.log(`  - ${m.document.name} (${m.priority})`);
  });
}
```

### Example 3: Using Frontend Data

```javascript
// From your document_classification_overlay.html
const requiredDocs = this.getAllRequiredDocuments();
const uploadedDocs = this.results.map(r => ({
  documentType: r.documentType,
  fileName: r.fileName,
  classification: {
    category: r.classification?.category,
    sub_type: r.classification?.sub_type
  }
}));

const response = await fetch('/api/compare-documents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    required_documents: requiredDocs,
    uploaded_documents: uploadedDocs
  })
});
```

---

## Integration in Frontend

### In `document_classification_overlay.html`

```javascript
async compareDocuments() {
  const requiredDocs = this.getAllRequiredDocuments();
  const uploadedDocs = this.results.map(r => ({
    documentType: r.documentType,
    fileName: r.fileName,
    classification: r.classification
  }));

  try {
    const response = await fetch('/api/compare-documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        required_documents: requiredDocs,
        uploaded_documents: uploadedDocs
      })
    });

    const result = await response.json();
    
    if (result.success) {
      console.log('✅ Matched:', result.comparison.matched.length);
      console.log('❌ Missing:', result.comparison.missing.length);
      console.log('⚠️ Extra:', result.comparison.extra.length);
      console.log('📈 Completeness:', result.summary.completeness + '%');
      
      this.documentComparisonResult = result;
    }
  } catch (error) {
    console.error('Error comparing documents:', error);
  }
}
```

---

## Document Aliases

The endpoint recognizes the following document aliases:

| Primary Name | Aliases |
|--------------|---------|
| Commercial Invoice | invoice, proforma invoice, sales invoice, commercial inv |
| Bill of Lading | b/l, bl, ocean bill of lading, sea waybill, bol |
| Packing List | packing slip, packaging list, pack list, packing |
| Certificate of Origin | origin certificate, coo, c/o |
| Insurance Certificate | insurance policy, insurance doc, insurance |
| Inspection Certificate | inspection report, quality certificate, inspection |
| Weight Certificate | weight list, weighing certificate, weight |
| Quality Certificate | quality report, inspection certificate, quality |
| Bank Guarantee | bg, guarantee, standby letter of credit, sblc |
| Letter of Credit | lc, l/c, documentary credit |
| Cargo Insurance | marine insurance, shipment insurance, cargo cover |

---

## Error Handling

```javascript
try {
  const response = await fetch('/api/compare-documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({...})
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const result = await response.json();
  
  if (!result.success) {
    console.error('API Error:', result.error);
    // Handle error
  } else {
    // Process results
    if (result.summary.status === 'incomplete') {
      console.warn('Not all required documents uploaded');
    }
  }
} catch (error) {
  console.error('Request failed:', error);
}
```

---

## Backend Logging

The endpoint logs detailed information:

- Incoming required and uploaded document counts
- Each document being searched for
- Match attempts with confidence scores
- Final summary statistics (matched, missing, extra counts)
- Overall completeness percentage

View logs in your application output to debug matching issues.

---

## Notes

- Matches require minimum confidence of **0.7 (70%)**
- The endpoint prevents double-matching (each uploaded document matches at most one required document)
- Matching is prioritized by confidence (best matches first)
- Aliases significantly improve matching accuracy
- Status values: `complete`, `complete_with_extra`, `mostly_complete`, `incomplete`

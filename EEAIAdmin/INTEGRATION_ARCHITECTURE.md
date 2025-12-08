# Document Comparison Endpoint - Integration Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue.js)                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ document_classification_overlay.html                         │   │
│  │ - User uploads documents                                     │   │
│  │ - Documents classified → results[]                           │   │
│  │ - compareUploadedDocuments() called automatically            │   │
│  │ - Results displayed to user                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     │ POST /api/compare-documents
                     │ {
                     │   required_documents: [...],
                     │   uploaded_documents: [...]
                     │ }
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend Flask API (routes.py)                    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ compare_documents() Endpoint                                │   │
│  │                                                             │   │
│  │ Phase 1: Pattern-Based Matching (100ms)                   │   │
│  │  ├─ Exact match (1.0 confidence)                          │   │
│  │  ├─ Fuzzy match (0.95)                                    │   │
│  │  ├─ Alias match (0.90)                                    │   │
│  │  ├─ Sub-type match (0.85)                                 │   │
│  │  └─ Filename match (0.75)                                 │   │
│  │                                                             │   │
│  │ Phase 2: Identify Missing & Extra (<50ms)                 │   │
│  │                                                             │   │
│  │ Phase 3: Calculate Statistics (<10ms)                     │   │
│  │                                                             │   │
│  │ Phase 4: LLM Analysis (8-12 seconds) ⭐ NEW               │   │
│  │  ├─ Send context to GPT-4o                                │   │
│  │  ├─ LLM analyzes document importance                      │   │
│  │  ├─ LLM assesses compliance risks                         │   │
│  │  ├─ LLM generates recommendations                         │   │
│  │  └─ Graceful fallback if LLM unavailable                  │   │
│  │                                                             │   │
│  │ Return enriched response                                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Azure OpenAI Service (LLM Analysis)                         │   │
│  │ - Model: GPT-4o                                             │   │
│  │ - Temperature: 0.7                                          │   │
│  │ - Max Tokens: 2000                                          │   │
│  │ - Purpose: Intelligent document analysis                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     │ HTTP 200 OK
                     │ {
                     │   success: true,
                     │   comparison: {...},
                     │   summary: {...},
                     │   llm_analysis: {
                     │     document_matching_rationale: "...",
                     │     missing_documents_analysis: "...",
                     │     risk_assessment: "...",
                     │     next_steps: "...",
                     │     recommendations: [...]
                     │   }
                     │ }
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue.js)                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Display Results to User                                     │   │
│  │ - Show matching documents ✅                               │   │
│  │ - Show missing documents ❌                                │   │
│  │ - Show extra documents ⚠️                                 │   │
│  │ - Display LLM recommendations 🤖                           │   │
│  │ - Show risk assessment                                     │   │
│  │ - Show completeness %                                      │   │
│  │ - Enable actions (download list, upload more, etc.)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Detailed Request/Response Flow

### Request
```
POST /api/compare-documents
Content-Type: application/json

{
  "required_documents": [
    {
      "name": "Commercial Invoice",
      "priority": "Mandatory",
      "description": "..."
    },
    {
      "name": "Bill of Lading",
      "priority": "Mandatory",
      "description": "..."
    },
    {
      "name": "Certificate of Origin",
      "priority": "Mandatory",
      "description": "..."
    }
  ],
  "uploaded_documents": [
    {
      "documentType": "Commercial Invoice",
      "fileName": "INV-2025-001.pdf",
      "classification": {...}
    },
    {
      "documentType": "Bill of Lading",
      "fileName": "BL-MSC-2025.pdf",
      "classification": {...}
    }
  ]
}
```

### Processing Phases

#### Phase 1: Pattern Matching (100ms)
```
For each required document:
  For each uploaded document:
    Calculate match confidence:
    - If type == name → confidence = 1.0 ✅ EXACT
    - If type contains name → confidence = 0.95 ✅ FUZZY
    - If name is alias for type → confidence = 0.90 ✅ ALIAS
    - If sub_type matches → confidence = 0.85 ✅ SUBTYPE
    - If filename contains name → confidence = 0.75 ✅ FILENAME
    - If confidence > 0.70 → ADD TO MATCHED
    
Result: matched[] array
```

#### Phase 2: Missing & Extra (50ms)
```
missing[] = required docs not in matched[]
extra[] = uploaded docs not in matched[]
```

#### Phase 3: Statistics (10ms)
```
total_required = len(required_documents)
matched_count = len(matched)
missing_count = len(missing)
extra_count = len(extra)
completeness = (matched_count / total_required) * 100
status = determine_status(missing_count, extra_count)
```

#### Phase 4: LLM Analysis (8-12 seconds) ⭐
```
BUILD PROMPT:
  ├─ System: "You are a trade finance specialist"
  ├─ User: Full context of all documents
  ├─ User: Matched/missing/extra docs
  └─ User: Request analysis structure

SEND TO GPT-4o:
  ├─ Model: GPT-4o
  ├─ Temperature: 0.7
  ├─ Max Tokens: 2000
  └─ Timeout: 60s

PARSE RESPONSE:
  ├─ Extract JSON from response
  ├─ Fields: rationale, analysis, risk, recommendations
  └─ Graceful fallback on error

RETURN RESULT:
  └─ llm_analysis object included
```

### Response
```
HTTP 200 OK
Content-Type: application/json

{
  "success": true,
  "comparison": {
    "matched": [
      {
        "required": {...},
        "uploaded": {...},
        "confidence": 1.0,
        "reason": "Exact match"
      }
    ],
    "missing": [
      {
        "document": {...},
        "priority": "Mandatory"
      }
    ],
    "extra": [...]
  },
  "summary": {
    "total_required": 3,
    "total_uploaded": 2,
    "matched": 2,
    "missing": 1,
    "extra": 0,
    "completeness": 66.7,
    "status": "incomplete"
  },
  "llm_analysis": {
    "document_matching_rationale": "Commercial Invoice and Bill of Lading matched exactly...",
    "missing_documents_analysis": "Certificate of Origin is CRITICAL for LC compliance...",
    "risk_assessment": "HIGH RISK: Missing 1 critical document...",
    "next_steps": "1. Contact chamber of commerce for Certificate of Origin...",
    "recommendations": [
      "Obtain Certificate of Origin immediately",
      "Verify all document dates match LC terms",
      "Submit complete package to bank"
    ]
  }
}
```

---

## 🎯 Matching Algorithm Flowchart

```
START: compare_documents()
  │
  ├─→ Load request JSON
  │    │
  │    ├─ required_documents[]
  │    └─ uploaded_documents[]
  │
  ├─→ FOR EACH required document
  │    │
  │    ├─→ FOR EACH uploaded document
  │    │    │
  │    │    ├─ Calculate confidence score
  │    │    │  ├─ Exact match? 1.0
  │    │    │  ├─ Fuzzy match? 0.95
  │    │    │  ├─ Alias match? 0.90
  │    │    │  ├─ Sub-type? 0.85
  │    │    │  └─ Filename? 0.75
  │    │    │
  │    │    └─ If confidence > 0.70
  │    │       └─ Mark as best match
  │    │
  │    └─ If best_match found
  │       └─ Add to matched[]
  │
  ├─→ Find missing (required not in matched)
  │
  ├─→ Find extra (uploaded not matched)
  │
  ├─→ Calculate summary stats
  │
  ├─→ CALL GPT-4o FOR ANALYSIS ⭐
  │    │
  │    ├─ Build analysis prompt
  │    ├─ Send to Azure OpenAI
  │    ├─ Parse LLM response
  │    └─ Include llm_analysis in response
  │
  └─→ Return jsonify({
       success: true,
       comparison: {...},
       summary: {...},
       llm_analysis: {...}
     })
```

---

## 📊 Data Flow Diagram

```
┌──────────────────┐
│  User Uploads    │
│  Documents       │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────┐
│  Document Classifier    │
│  - Identifies type      │
│  - Extracts features    │
│  - Creates results[]    │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Compare Documents      │
│  - Matching (Phase 1)   │
│  - Missing/Extra (P2)   │
│  - Stats (Phase 3)      │
│  - LLM Analysis (P4) ⭐ │
└────────┬────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
┌────────┐  ┌──────────────┐
│Backend │  │Azure OpenAI  │
│Result  │  │(GPT-4o) ⭐   │
└────┬───┘  └──────┬───────┘
     │             │
     │ LLM Result  │
     └────┬────────┘
          │
          ▼
     ┌─────────────┐
     │ Enhanced    │
     │ Response    │
     │ with LLM    │
     │ Analysis ⭐ │
     └─────┬───────┘
           │
           ▼
     ┌──────────────────┐
     │Display to User   │
     │ - Matches        │
     │ - Missing        │
     │ - Risks          │
     │ - Recommendations│
     └──────────────────┘
```

---

## 🔌 API Integration Points

### Frontend → Backend
```javascript
// Call endpoint
fetch('/api/compare-documents', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        required_documents: lcRequiredDocs,
        uploaded_documents: uploadedDocuments
    })
})
.then(r => r.json())
.then(result => {
    // Handle result with LLM analysis
    displayMatches(result.comparison.matched);
    displayMissing(result.comparison.missing);
    displayRisk(result.llm_analysis.risk_assessment);
    showRecommendations(result.llm_analysis.recommendations);
})
```

### Backend → External Services
```python
# Call LLM
response = openai.ChatCompletion.create(
    engine=deployment_name,  # GPT-4o
    messages=[
        {"role": "system", "content": "You are a trade finance specialist"},
        {"role": "user", "content": analysis_prompt}
    ],
    temperature=0.7,
    max_tokens=2000
)

llm_analysis = json.loads(response.choices[0].message.content)
```

---

## ⏱️ Timing Breakdown

```
Total Request Time: ~8-12 seconds

├─ Request parsing: 10ms
├─ Phase 1 (Matching): 100ms
├─ Phase 2 (Missing/Extra): 50ms  
├─ Phase 3 (Statistics): 10ms
├─ Phase 4 (LLM):
│  ├─ LLM API call: 8-12 seconds
│  ├─ Response parsing: 100ms
│  └─ Error handling: <10ms
├─ Response formatting: 50ms
└─ Response serialization: 10ms

Critical Path: LLM API call (8-12 seconds)
Other operations: <300ms
```

---

## 🔒 Error Handling Flow

```
START: compare_documents()
  │
  ├─→ Try:
  │    ├─ Validate request
  │    ├─ Parse JSON
  │    ├─ Run matching
  │    ├─ Run statistics
  │    │
  │    └─→ Try LLM:
  │         ├─ Build prompt
  │         ├─ Call GPT-4o
  │         ├─ Parse response
  │         │
  │         └─→ Catch LLM Error:
  │              ├─ Log error
  │              ├─ Set llm_analysis.error
  │              ├─ Use fallback rationale
  │              └─ Continue (don't fail)
  │
  └─→ Catch General Error:
       ├─ Log full traceback
       └─ Return 500 error

RESULT: Response with or without LLM analysis
```

---

## 📈 Scalability

| Metric | Limit | Notes |
|--------|-------|-------|
| Required Docs | 100 | Pattern matching is O(n*m) |
| Uploaded Docs | 100 | Linear with required docs |
| Concurrent Requests | 10+ | Depends on LLM quota |
| LLM Token Budget | 2000 | Per request |
| Total Timeout | 60s | Includes LLM call |
| Response Size | <100KB | Typical 20-50KB |

---

## 🎯 Next Steps for Frontend

1. **Display Matched Documents**
   ```javascript
   result.comparison.matched.forEach(match => {
       console.log(`✅ ${match.required.name} (${match.confidence}%)`);
   });
   ```

2. **Show Missing Documents with Priority**
   ```javascript
   const critical = result.comparison.missing
       .filter(m => m.priority === 'Mandatory');
   showAlert(`${critical.length} CRITICAL documents missing`);
   ```

3. **Display Risk Assessment**
   ```javascript
   if (result.llm_analysis.risk_assessment.includes('HIGH')) {
       showWarning(result.llm_analysis.risk_assessment);
   }
   ```

4. **Show Recommendations**
   ```javascript
   result.llm_analysis.recommendations.forEach((rec, i) => {
       console.log(`${i+1}. ${rec}`);
   });
   ```

5. **Enable Actions**
   - Download missing list button
   - Upload more documents button
   - Contact bank button
   - Proceed anyway button

---

**Architecture Version**: 2.0  
**Date**: November 27, 2025  
**Status**: Production Ready ✅

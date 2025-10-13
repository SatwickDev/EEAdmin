# Repository Connection Guide

## Overview
This guide explains how repositories should be connected to forms and when they should NOT be connected (like in the dashboard).

## Key Principle
- **Forms** need repository connections to save/retrieve data
- **Dashboards** should NOT have fixed repository connections (they're navigation points)
- **AI Chat Dashboard** should NOT be tied to a specific repository

## 1. AI Chat Dashboard (`ai_chat_dashboard.html`)
**Repository Connection**: ❌ NONE - This is a navigation dashboard
```javascript
// NO REPOSITORY_CONFIG should be defined here
// This page navigates TO different repository forms
function navigateToForm(repository) {
    sessionStorage.setItem('selectedRepository', repository);
    // Navigate to the appropriate form
}
```

## 2. Trade Finance Forms
These forms MUST connect to the Trade Finance repository:

### LC Form (`trade_finance_lc_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'trade_finance',
    repository_name: 'Trade Finance',
    repository_type: 'import_lc',
    collection: 'trade_finance_data'
};
```

### Bank Guarantee Form (`trade_finance_guarantee_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'trade_finance',
    repository_name: 'Trade Finance',
    repository_type: 'bank_guarantee',
    collection: 'trade_finance_data'
};
```

## 3. Treasury Management Form (`treasury_management_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'treasury',
    repository_name: 'Treasury',
    repository_type: 'treasury_management',
    collection: 'treasury_data'
};
```

## 4. Cash Management Form (`cash_management_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'cash_management',
    repository_name: 'Cash Management',
    repository_type: 'cash_management',
    collection: 'cash_management_data'
};
```

## Repository Connection Flow

```
AI Chat Dashboard (No Repository)
        ↓
    User Selects Repository
        ↓
    Store in sessionStorage
        ↓
    Navigate to Form
        ↓
Form Loads with REPOSITORY_CONFIG
        ↓
    Connect to Repository
        ↓
    Enable Data Operations
```

## Chatbot Integration
When opening chatbot from a form, pass repository context:

```javascript
// From a FORM (with repository)
const params = new URLSearchParams({
    repository_id: REPOSITORY_CONFIG.repository_id,
    repository_name: REPOSITORY_CONFIG.repository_name,
    repository_type: REPOSITORY_CONFIG.repository_type,
    source: 'form_name'
});
chatbotFrame.src = `/ai_chat_modern_overylay?${params.toString()}`;
```

```javascript
// From DASHBOARD (no repository)
// Don't pass repository parameters - chatbot will be generic
chatbotFrame.src = '/ai_chat_modern_overylay';
```

## Smart Capture Integration
Smart capture should receive repository context ONLY from forms:

```javascript
// From a FORM (with repository)
const params = new URLSearchParams({
    repository_type: REPOSITORY_CONFIG.repository_name,
    repository_id: REPOSITORY_CONFIG.repository_id,
    form_type: REPOSITORY_CONFIG.form_type,
    context: 'specific_form_context'
});
iframe.src = `/document-classification-overlay?${params.toString()}`;
```

## Summary of Repository Connections

| Page | Has Repository? | Repository ID | Purpose |
|------|----------------|---------------|---------|
| ai_chat_dashboard.html | ❌ NO | None | Navigation hub |
| trade_finance_dashboard.html | ❌ NO | None | Trade finance navigation |
| trade_finance_lc_form.html | ✅ YES | trade_finance | LC data operations |
| trade_finance_guarantee_form.html | ✅ YES | trade_finance | Guarantee data operations |
| treasury_management_form.html | ✅ YES | treasury | Treasury data operations |
| cash_management_form.html | ✅ YES | cash_management | Cash data operations |

## Implementation Checklist

✅ **Correctly Connected Forms:**
- trade_finance_lc_form.html
- trade_finance_guarantee_form.html (fixed)
- treasury_management_form.html
- cash_management_form.html

❌ **Should NOT Have Repository:**
- ai_chat_dashboard.html
- trade_finance_dashboard.html
- Any other dashboard pages

## Testing Repository Connections

1. **Form Test**: Open a form, check console for:
   ```
   Repository context loaded: {repository_id: "...", ...}
   ```

2. **Dashboard Test**: Open dashboard, should NOT see repository config in console

3. **Navigation Test**: From dashboard, select a repository and navigate to form
   - Check sessionStorage has 'selectedRepository'
   - Form should load with correct repository

4. **Chatbot Test**: Open chatbot from form
   - Should show repository name in chatbot header
   - Should have access to repository-specific data

5. **Smart Capture Test**: Open smart capture from form
   - Should extract data for the specific form type
   - Should auto-fill form fields correctly
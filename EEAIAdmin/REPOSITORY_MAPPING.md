# Repository Configuration Mapping

This document shows the correct repository configuration for each form in the application.

## Trade Finance Forms

### 1. Trade Finance Dashboard (`trade_finance_dashboard.html`)
- **Repository ID**: `trade_finance`
- **Repository Name**: Trade Finance
- **Repository Type**: N/A (dashboard, not a form)
- **Collection**: `trade_finance_data`

### 2. LC Form (`trade_finance_lc_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'trade_finance',
    repository_name: 'Trade Finance',
    repository_type: 'import_lc',
    collection: 'trade_finance_data',
    selected_from_dashboard: true/false
};
```

### 3. Bank Guarantee Form (`trade_finance_guarantee_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'trade_finance',
    repository_name: 'Trade Finance',
    repository_type: 'bank_guarantee',
    form_type: 'bank_guarantee',
    collection: 'trade_finance_data',
    selected_from_dashboard: true/false
};
```

## Treasury Management Form (`treasury_management_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'treasury',
    repository_name: 'Treasury',
    repository_type: 'treasury_management',
    collection: 'treasury_data',
    selected_from_dashboard: true/false
};
```

## Cash Management Form (`cash_management_form.html`)
```javascript
const REPOSITORY_CONFIG = {
    repository_id: 'cash_management',
    repository_name: 'Cash Management',
    repository_type: 'cash_management',
    collection: 'cash_management_data',
    selected_from_dashboard: true/false
};
```

## Key Points

1. **Trade Finance Forms** all share the same `repository_id: 'trade_finance'` but have different `repository_type` values:
   - LC Form: `repository_type: 'import_lc'`
   - Bank Guarantee: `repository_type: 'bank_guarantee'`

2. **Treasury Management** uses:
   - `repository_id: 'treasury'`
   - `repository_type: 'treasury_management'`

3. **Cash Management** uses:
   - `repository_id: 'cash_management'`
   - `repository_type: 'cash_management'`

## Chatbot Integration

When opening the chatbot from any form, the repository context is passed via URL parameters:
```javascript
const params = new URLSearchParams({
    repository_id: REPOSITORY_CONFIG.repository_id,
    repository_name: REPOSITORY_CONFIG.repository_name,
    repository_type: REPOSITORY_CONFIG.repository_type,
    source: 'form_name'
});
chatbotFrame.src = `/ai_chat_modern_overylay?${params.toString()}`;
```

## Smart Capture Integration

Smart capture should receive the repository context:
```javascript
const params = new URLSearchParams({
    repository_type: REPOSITORY_CONFIG.repository_name,
    repository_id: REPOSITORY_CONFIG.repository_id,
    form_type: REPOSITORY_CONFIG.form_type,
    context: 'specific_form_context'
});
iframe.src = `/document-classification-overlay?${params.toString()}`;
```

## Storage Keys

Draft storage uses repository-specific keys:
- Trade Finance LC: `draft_trade_finance_import_lc`
- Trade Finance Guarantee: `draft_trade_finance_bank_guarantee`
- Treasury: `treasury_draft_treasury_forex` (or other tabs)
- Cash Management: `cash_draft_cash_management_liquidity` (or other tabs)

## API Endpoints

Form submissions use repository-specific endpoints:
- Trade Finance: `/api/repository/trade_finance/{type}/submit`
- Treasury: `/api/repository/treasury/{type}/submit`
- Cash Management: `/api/repository/cash_management/{type}/submit`
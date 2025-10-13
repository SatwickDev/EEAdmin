# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
EEAI is a Flask-based AI application for trade finance, treasury, and cash management with document processing, compliance checking, and AI-powered chatbot capabilities.

## Architecture
- **Backend**: Flask application with routes in `app/routes.py`
- **Frontend**: HTML templates in `app/templates/` with modern JavaScript and CSS
- **Database**: MongoDB for document storage, Oracle for trade finance data, ChromaDB for vector search
- **AI Integration**: Azure OpenAI for LLM, Azure Computer Vision for OCR
- **Utils**: Core functionality in `app/utils/` including RAG, compliance, and document processing

## Common Development Commands

### Running the Application
```bash
# Start Flask server (runs on port 5001)
python run.py

# Using virtual environment on Windows
.venv/Scripts/python.exe run.py
```

### Testing
```bash
# Run specific test files (Windows virtual environment)
.venv/Scripts/python.exe test_forms_navigation.py
.venv/Scripts/python.exe test_transaction_flow.py
.venv/Scripts/python.exe test_handler_direct.py
.venv/Scripts/python.exe test_llm_intent_classification.py
```

### Setup & Administration
```bash
# Create admin user
python create_admin_auto.py

# Create default repositories (Trade Finance, Treasury, Cash Management)
python create_repositories_auto.py

# Populate treasury data
python populate_treasury_collections.py
```

## Key Features & Components

### Form Enhancement Requirements
When updating forms (especially trade_finance_guarantee_form.html), ensure:
1. **Smart Capture Integration**: Include document upload/OCR functionality
2. **Chatbot Integration**: Embed AI assistant for form help
3. **Theme Consistency**: Match index.html styling (glass morphism, gradients)
4. **Repository Context**: Forms must connect to appropriate repository

### Smart Capture Feature Structure
- Modal overlay with iframe to document_classification.html
- OCR and data extraction capabilities
- Auto-fill form fields from uploaded documents
- Located in templates with class `smart-capture-*`

### Chatbot Integration Pattern
- Floating chatbot icon with pulse animation
- Modal/overlay window with iframe to ai_chat_modern_overlay
- Repository context passing via postMessage
- Window controls (minimize, maximize, close)

### Repository System
Three default repositories:
1. **Trade Finance** - LC, Bank Guarantees, Trade Documents
2. **Treasury** - FX, Investments, Risk Management  
3. **Cash Management** - Cash Flow, Liquidity, Payments

## CSS/Styling Guidelines
- Use Inter font family
- Glass morphism effects with backdrop-filter
- Gradient backgrounds (primary: #667eea to #764ba2)
- Consistent border-radius (12-32px for cards)
- Shadow effects for depth
- Animations for interactive elements

## API Endpoints Pattern
- Auth routes: `/login`, `/logout`, `/api/auth/*`
- Chat routes: `/chat`, `/ai_chat*`
- Document routes: `/document_classification*`, `/upload`
- Repository routes: `/api/repository/*`
- Forms: `/trade_finance_*`, `/treasury_*`, `/cash_management_*`

## Environment Variables Required
- Azure OpenAI credentials (API key, endpoint, deployment)
- Azure Computer Vision credentials
- MongoDB connection (if using)
- Oracle database credentials (EXIMTRX, CETRX)
- Flask SECRET_KEY

## Important File Locations
- Main routes: `app/routes.py`
- Form templates: `app/templates/trade_finance_*.html`
- Chatbot components: `app/templates/ai_chat_*.html`
- CSS: `app/static/css/`
- JavaScript: `app/static/js/`
- Utils: `app/utils/` (gpt_utils, query_utils, compliance_utils)

## Current User Instructions
The current task involves enhancing trade_finance_guarantee_form.html to:
1. Add smart capture functionality similar to trade_finance_lc_form.html
2. Add chatbot integration with proper repository context
3. Ensure theme consistency with index.html
4. Maintain form field alignment and styling

## Filter Enhancements (from previous CLAUDE.md)
- Add date range filter options:
  - Predefined ranges: 1 day, 1 week, 1 month, last 3 months, 1 year
  - Custom date range selection
  - Ability to add additional data within selected date ranges
/**
 * Chatbot Repository Integration
 * Handles repository-specific context and navigation
 */

class ChatbotRepositoryIntegration {
    constructor() {
        this.currentRepository = null;
        this.repositoryContext = {
            trade_finance: {
                name: 'Trade Finance',
                color: '#667eea',
                icon: 'fa-file-invoice-dollar',
                welcomeMessage: `Welcome to Trade Finance! I can help you with:
                    • Import/Export Letters of Credit
                    • Bank Guarantees  
                    • Trade Documents
                    • Compliance Checks
                    • SWIFT Messages
                    
                    Just tell me what you need, like:
                    "Create an import LC for $50,000"
                    "Check status of LC123456"
                    "I need a bank guarantee"`,
                quickActions: [
                    { label: 'Create Import LC', command: 'create import lc' },
                    { label: 'Create Export LC', command: 'create export lc' },
                    { label: 'Bank Guarantee', command: 'create bank guarantee' },
                    { label: 'Check LC Status', command: 'check lc status' },
                    { label: 'View Documents', command: 'show my documents' }
                ],
                sampleCommands: [
                    'Create import LC for USD 50,000 to ABC Company',
                    'I need a performance guarantee for 100,000 EUR',
                    'Show all active LCs',
                    'Check compliance for LC123456'
                ]
            },
            treasury: {
                name: 'Treasury',
                color: '#10b981',
                icon: 'fa-chart-line',
                welcomeMessage: `Welcome to Treasury Management! I can help you with:
                    • Foreign Exchange Trades
                    • Investments & Fixed Deposits
                    • Derivatives & Hedging
                    • Risk Management
                    • Portfolio Analysis
                    
                    Just tell me what you need, like:
                    "Buy 100,000 USD against EUR"
                    "Create a fixed deposit for 1 million"
                    "Show my FX positions"`,
                quickActions: [
                    { label: 'FX Spot Trade', command: 'create fx spot trade' },
                    { label: 'FX Forward', command: 'create fx forward' },
                    { label: 'Fixed Deposit', command: 'create fixed deposit' },
                    { label: 'View Positions', command: 'show my positions' },
                    { label: 'Risk Report', command: 'generate risk report' }
                ],
                sampleCommands: [
                    'Buy 100,000 USD sell EUR at 1.0950',
                    'Create 6-month fixed deposit for 500,000 USD',
                    'Show all open FX positions',
                    'Calculate VAR for my portfolio'
                ]
            },
            cash_management: {
                name: 'Cash Management',
                color: '#3b82f6',
                icon: 'fa-wallet',
                welcomeMessage: `Welcome to Cash Management! I can help you with:
                    • Payment Processing
                    • Collections & Receivables
                    • Cash Position & Liquidity
                    • Cash Forecasting
                    • Account Management
                    
                    Just tell me what you need, like:
                    "Make payment of 25,000 to XYZ Corp"
                    "Show cash position"
                    "Setup recurring collection"`,
                quickActions: [
                    { label: 'Make Payment', command: 'make payment' },
                    { label: 'Cash Position', command: 'show cash position' },
                    { label: 'Setup Collection', command: 'setup collection' },
                    { label: 'Cash Forecast', command: 'generate cash forecast' },
                    { label: 'Account Balance', command: 'show account balances' }
                ],
                sampleCommands: [
                    'Pay 25,000 USD to ABC Company account 123456789',
                    'Show cash position for all accounts',
                    'Setup monthly collection from Customer XYZ',
                    'Forecast cash flow for next 30 days'
                ]
            }
        };
        
        this.initializeListeners();
    }
    
    initializeListeners() {
        // Listen for messages from parent window (dashboard)
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type) {
                this.handleMessage(event.data);
            }
        });
        
        // Check if we're in an iframe and request context
        if (window.parent !== window) {
            this.requestRepositoryContext();
        }
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'set_repository_context':
                this.setRepositoryContext(data.repository);
                if (data.welcomeMessage) {
                    this.displayWelcomeMessage(data.welcomeMessage, data.suggestedActions);
                }
                break;
                
            case 'repository_change':
                this.setRepositoryContext(data.repository);
                this.notifyRepositoryChange(data.repository);
                break;
                
            case 'set_intent':
                this.handleIntent(data.intent, data.repository);
                break;
                
            case 'navigate_to_form':
                this.navigateToForm(data.formType, data.formData);
                break;
        }
    }
    
    setRepositoryContext(repository) {
        this.currentRepository = repository;
        const context = this.repositoryContext[repository];
        
        if (context) {
            // Update UI theme
            this.updateTheme(context);
            
            // Update header
            this.updateHeader(context);
            
            // Store in session
            sessionStorage.setItem('activeRepository', repository);
            
            // Add repository badge to messages
            this.addRepositoryBadge(context);
        }
    }
    
    updateTheme(context) {
        // Update CSS variables for repository theme
        const root = document.documentElement;
        if (root) {
            root.style.setProperty('--repository-color', context.color);
            
            // Update header if exists
            const header = document.querySelector('.chat-header, .chatbot-header');
            if (header) {
                header.style.background = `linear-gradient(135deg, ${context.color} 0%, ${context.color}dd 100%)`;
            }
        }
    }
    
    updateHeader(context) {
        // Add repository indicator to header
        const headerTitle = document.querySelector('.header-title, h3');
        if (headerTitle && !headerTitle.querySelector('.repo-badge')) {
            const badge = document.createElement('span');
            badge.className = 'repo-badge';
            badge.style.cssText = `
                background: ${context.color};
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
                margin-left: 10px;
                font-weight: 500;
            `;
            badge.textContent = context.name;
            headerTitle.appendChild(badge);
        }
    }
    
    displayWelcomeMessage(message, suggestedActions) {
        // Add welcome message to chat
        const messageContainer = document.querySelector('.messages-container, .chat-messages');
        if (messageContainer) {
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'message assistant-message welcome-message';
            welcomeDiv.innerHTML = `
                <div class="message-content" style="background: linear-gradient(135deg, ${this.repositoryContext[this.currentRepository]?.color}22 0%, transparent 100%); border-left: 3px solid ${this.repositoryContext[this.currentRepository]?.color};">
                    <div style="white-space: pre-wrap;">${message}</div>
                    ${suggestedActions ? this.createActionButtons(suggestedActions) : ''}
                </div>
            `;
            messageContainer.appendChild(welcomeDiv);
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
    }
    
    createActionButtons(actions) {
        const context = this.repositoryContext[this.currentRepository];
        if (!context) return '';
        
        const buttons = context.quickActions.map(action => `
            <button class="quick-action-btn" onclick="sendMessage('${action.command}')" style="
                background: ${context.color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                margin: 4px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.3s;
            " onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'">
                ${action.label}
            </button>
        `).join('');
        
        return `
            <div class="quick-actions" style="margin-top: 15px;">
                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Quick Actions:</div>
                <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                    ${buttons}
                </div>
            </div>
        `;
    }
    
    addRepositoryBadge(context) {
        // Add visual indicator for repository context
        const inputArea = document.querySelector('.input-area, .chat-input-container');
        if (inputArea && !inputArea.querySelector('.context-indicator')) {
            const indicator = document.createElement('div');
            indicator.className = 'context-indicator';
            indicator.style.cssText = `
                background: ${context.color}15;
                color: ${context.color};
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                margin-bottom: 8px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            `;
            indicator.innerHTML = `
                <i class="fas ${context.icon}"></i>
                <span>Active: ${context.name}</span>
            `;
            inputArea.insertBefore(indicator, inputArea.firstChild);
        }
    }
    
    handleIntent(intent, repository) {
        // Set repository if provided
        if (repository) {
            this.setRepositoryContext(repository);
        }
        
        // Handle specific intents
        const intentMessages = {
            'creation': 'I\'ll help you create a transaction. What would you like to create?',
            'query': 'I\'ll help you search. What are you looking for?',
            'report': 'I\'ll generate a report for you. What type of report do you need?',
            'help': 'How can I assist you today?'
        };
        
        const message = intentMessages[intent] || 'How can I help you?';
        this.displayWelcomeMessage(message, []);
    }
    
    notifyRepositoryChange(repository) {
        const context = this.repositoryContext[repository];
        if (context) {
            const message = `Switched to ${context.name}. ${context.welcomeMessage}`;
            this.displayWelcomeMessage(message, context.quickActions.map(a => a.label));
        }
    }
    
    requestRepositoryContext() {
        // Request context from parent window
        window.parent.postMessage({
            type: 'request_repository_context'
        }, '*');
    }
    
    navigateToForm(formType, formData) {
        // Send navigation request to parent
        window.parent.postMessage({
            type: 'navigate_to_form',
            formType: formType,
            formData: formData
        }, '*');
    }
    
    // Helper function to send messages with repository context
    sendMessageWithContext(message) {
        const contextPrefix = this.currentRepository ? 
            `[Repository: ${this.repositoryContext[this.currentRepository]?.name}] ` : '';
        
        return contextPrefix + message;
    }
    
    // Get repository-specific help
    getRepositoryHelp() {
        const context = this.repositoryContext[this.currentRepository];
        if (!context) {
            return 'Please select a repository to get started.';
        }
        
        return `
            **${context.name} - Available Commands:**
            
            ${context.sampleCommands.map(cmd => `• ${cmd}`).join('\n')}
            
            You can also ask questions like:
            • Show all pending transactions
            • What's my exposure limit?
            • Generate monthly report
            • Help with ${context.name.toLowerCase()}
        `;
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.chatbotRepoIntegration = new ChatbotRepositoryIntegration();
});

// Global helper for sending messages
function sendMessage(message) {
    const input = document.querySelector('input[type="text"], textarea');
    if (input) {
        input.value = message;
        const event = new KeyboardEvent('keypress', { key: 'Enter', keyCode: 13 });
        input.dispatchEvent(event);
        
        // Fallback - click send button
        const sendBtn = document.querySelector('.send-button, button[type="submit"]');
        if (sendBtn) sendBtn.click();
    }
}
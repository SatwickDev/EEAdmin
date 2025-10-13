// Smart Chat JavaScript
class SmartBankingChat {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.currentSuggestions = [];
        this.messageInput = document.getElementById('message-input');
        this.messagesContainer = document.getElementById('messages-container');
        this.suggestionsPanel = document.getElementById('suggestions-panel');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.sendButton = document.getElementById('send-button');
        
        this.initializeEventListeners();
        this.loadTemplates();
        this.setupAutoResize();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    initializeEventListeners() {
        // Form submissions
        document.getElementById('transaction-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.processTransaction();
        });

        document.getElementById('beneficiary-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addBeneficiary();
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.input-wrapper')) {
                this.hideSuggestions();
            }
        });
    }

    setupAutoResize() {
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });
    }

    autoResizeTextarea() {
        const textarea = this.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    async handleInput(event) {
        const inputValue = event.target.value;
        
        if (inputValue.length > 2) {
            // Get smart suggestions
            try {
                const response = await fetch('/api/conversation/suggestions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        input_text: inputValue,
                        transaction_type: this.detectTransactionType(inputValue)
                    })
                });

                const data = await response.json();
                if (data.success) {
                    this.showSuggestions(data.suggestions);
                }
            } catch (error) {
                console.error('Error getting suggestions:', error);
            }
        } else {
            this.hideSuggestions();
        }
    }

    detectTransactionType(input) {
        const lowerInput = input.toLowerCase();
        
        if (lowerInput.includes('transfer') || lowerInput.includes('send')) {
            return 'transfer';
        } else if (lowerInput.includes('payment') || lowerInput.includes('pay')) {
            return 'payment';
        } else if (lowerInput.includes('deposit')) {
            return 'deposit';
        } else if (lowerInput.includes('withdraw')) {
            return 'withdrawal';
        }
        
        return 'general';
    }

    showSuggestions(suggestions) {
        if (!suggestions || suggestions.length === 0) {
            this.hideSuggestions();
            return;
        }

        const suggestionsHTML = suggestions.map(suggestion => `
            <div class="suggestion-item" onclick="chat.applySuggestion(${JSON.stringify(suggestion).replace(/"/g, '&quot;')})">
                <div class="suggestion-icon ${suggestion.type}">
                    <i class="fas fa-${this.getSuggestionIcon(suggestion.type)}"></i>
                </div>
                <div class="suggestion-content">
                    <div class="suggestion-title">${suggestion.title}</div>
                    <div class="suggestion-desc">${suggestion.description}</div>
                </div>
            </div>
        `).join('');

        this.suggestionsPanel.innerHTML = suggestionsHTML;
        this.suggestionsPanel.style.display = 'block';
        this.currentSuggestions = suggestions;
    }

    getSuggestionIcon(type) {
        switch(type) {
            case 'template': return 'file-alt';
            case 'beneficiary': return 'user';
            case 'pattern': return 'history';
            default: return 'lightbulb';
        }
    }

    applySuggestion(suggestion) {
        if (suggestion.type === 'beneficiary') {
            this.applyBeneficiarySuggestion(suggestion);
        } else if (suggestion.type === 'template') {
            this.applyTemplateSuggestion(suggestion);
        } else if (suggestion.type === 'pattern') {
            this.applyPatternSuggestion(suggestion);
        }
        
        this.hideSuggestions();
    }

    applyBeneficiarySuggestion(suggestion) {
        const message = `Transfer to ${suggestion.data.name} (${suggestion.data.account_number}) at ${suggestion.data.bank_name}`;
        this.messageInput.value = message;
        this.messageInput.focus();
    }

    applyTemplateSuggestion(suggestion) {
        if (suggestion.data && Object.keys(suggestion.data).length > 0) {
            this.openTransactionForm();
            this.fillFormWithData(suggestion.data);
        } else {
            this.messageInput.value = suggestion.title;
            this.messageInput.focus();
        }
    }

    applyPatternSuggestion(suggestion) {
        if (suggestion.data && Object.keys(suggestion.data).length > 0) {
            this.openTransactionForm();
            this.fillFormWithData(suggestion.data);
        }
    }

    fillFormWithData(data) {
        const formFields = {
            'beneficiary-name': data.beneficiary_name || data.name,
            'account-number': data.account_number,
            'bank-name': data.bank_name,
            'amount': data.amount,
            'purpose': data.purpose || data.description
        };

        Object.entries(formFields).forEach(([fieldId, value]) => {
            const field = document.getElementById(fieldId);
            if (field && value) {
                field.value = value;
            }
        });
    }

    hideSuggestions() {
        this.suggestionsPanel.style.display = 'none';
    }

    handleKeyPress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        this.addMessageToChat(message, 'user');
        this.messageInput.value = '';
        this.autoResizeTextarea();
        this.hideSuggestions();
        
        this.showTypingIndicator();
        this.sendButton.disabled = true;

        try {
            // Send message to backend
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.addMessageToChat(data.response, 'assistant');
                
                // Save to conversation history
                await this.saveToConversationHistory(message, data.response);
            } else {
                this.addMessageToChat('Sorry, I encountered an error. Please try again.', 'assistant');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessageToChat('Sorry, I encountered an error. Please try again.', 'assistant');
        } finally {
            this.hideTypingIndicator();
            this.sendButton.disabled = false;
        }
    }

    async saveToConversationHistory(message, response) {
        try {
            await fetch('/api/conversation/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    response: response,
                    session_id: this.sessionId,
                    message_type: 'chat'
                })
            });
        } catch (error) {
            console.error('Error saving conversation:', error);
        }
    }

    addMessageToChat(message, sender) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}`;
        
        const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageElement.innerHTML = `
            <div class="message-content">
                <div>${this.formatMessage(message)}</div>
                <div class="message-time">${currentTime}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    formatMessage(message) {
        // Basic markdown-like formatting
        return message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    async loadTemplates() {
        try {
            const response = await fetch('/api/conversation/templates');
            const data = await response.json();
            
            if (data.success) {
                this.displayTemplates(data.templates);
            }
        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }

    displayTemplates(templates) {
        const templatesList = document.getElementById('templates-list');
        
        if (!templates || templates.length === 0) {
            templatesList.innerHTML = '<p style="color: #718096; font-size: 12px;">No templates yet</p>';
            return;
        }

        const templatesHTML = templates.slice(0, 5).map(template => `
            <div class="template-item" onclick="chat.useTemplate('${template._id}')">
                <div class="template-title">${template.title}</div>
                <div class="template-desc">${template.category} • Used ${template.usage_count} times</div>
            </div>
        `).join('');

        templatesList.innerHTML = templatesHTML;
    }

    async useTemplate(templateId) {
        try {
            const response = await fetch(`/api/conversation/templates?template_id=${templateId}`);
            const data = await response.json();
            
            if (data.success && data.template) {
                this.fillFormWithData(data.template.data);
                this.openTransactionForm();
            }
        } catch (error) {
            console.error('Error using template:', error);
        }
    }

    // Modal Functions
    openTransactionForm() {
        document.getElementById('transaction-modal').style.display = 'flex';
    }

    openBeneficiaryForm() {
        document.getElementById('beneficiary-modal').style.display = 'flex';
    }

    closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    async processTransaction() {
        const formData = {
            beneficiary_name: document.getElementById('beneficiary-name').value,
            account_number: document.getElementById('account-number').value,
            bank_name: document.getElementById('bank-name').value,
            amount: parseFloat(document.getElementById('amount').value),
            purpose: document.getElementById('purpose').value
        };

        try {
            // Save as template for future use
            await this.saveTemplate('Transaction Template', formData, 'transaction');
            
            // Process the transaction
            const message = `Process transaction: ${formData.amount} to ${formData.beneficiary_name} (${formData.account_number}) at ${formData.bank_name} for ${formData.purpose}`;
            
            this.addMessageToChat(message, 'user');
            this.closeModal('transaction-modal');
            
            // Send to AI for processing
            await this.sendTransactionToAI(formData);
            
        } catch (error) {
            console.error('Error processing transaction:', error);
            alert('Error processing transaction. Please try again.');
        }
    }

    async sendTransactionToAI(transactionData) {
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: `Process this transaction: ${JSON.stringify(transactionData)}`,
                    session_id: this.sessionId,
                    message_type: 'transaction',
                    metadata: transactionData
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.addMessageToChat(data.response, 'assistant');
            }
        } catch (error) {
            console.error('Error sending transaction to AI:', error);
            this.addMessageToChat('Transaction submitted successfully. Processing...', 'assistant');
        } finally {
            this.hideTypingIndicator();
        }
    }

    async addBeneficiary() {
        const beneficiaryData = {
            name: document.getElementById('new-beneficiary-name').value,
            account_number: document.getElementById('new-account-number').value,
            bank_name: document.getElementById('new-bank-name').value,
            swift_code: document.getElementById('new-swift-code').value
        };

        try {
            const response = await fetch('/api/conversation/beneficiary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(beneficiaryData)
            });

            const data = await response.json();
            
            if (data.success) {
                this.addMessageToChat(`Beneficiary ${beneficiaryData.name} added successfully!`, 'assistant');
                this.closeModal('beneficiary-modal');
                document.getElementById('beneficiary-form').reset();
            } else {
                alert('Error adding beneficiary. Please try again.');
            }
        } catch (error) {
            console.error('Error adding beneficiary:', error);
            alert('Error adding beneficiary. Please try again.');
        }
    }

    async showBeneficiarySuggestions(query) {
        if (query.length < 2) {
            document.getElementById('beneficiary-suggestions').style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/api/conversation/beneficiaries?q=${encodeURIComponent(query)}&limit=5`);
            const data = await response.json();
            
            if (data.success && data.beneficiaries.length > 0) {
                const suggestionsHTML = data.beneficiaries.map(beneficiary => `
                    <div class="auto-fill-item" onclick="chat.fillBeneficiaryData('${beneficiary._id}')">
                        <strong>${beneficiary.name}</strong><br>
                        <small>${beneficiary.account_number} • ${beneficiary.bank_name}</small>
                    </div>
                `).join('');

                const suggestionsDiv = document.getElementById('beneficiary-suggestions');
                suggestionsDiv.innerHTML = suggestionsHTML;
                suggestionsDiv.style.display = 'block';
            }
        } catch (error) {
            console.error('Error getting beneficiary suggestions:', error);
        }
    }

    async fillBeneficiaryData(beneficiaryId) {
        try {
            const response = await fetch(`/api/conversation/beneficiaries`);
            const data = await response.json();
            
            if (data.success) {
                const beneficiary = data.beneficiaries.find(b => b._id === beneficiaryId);
                if (beneficiary) {
                    document.getElementById('beneficiary-name').value = beneficiary.name;
                    document.getElementById('account-number').value = beneficiary.account_number;
                    document.getElementById('bank-name').value = beneficiary.bank_name;
                    document.getElementById('beneficiary-suggestions').style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error filling beneficiary data:', error);
        }
    }

    async saveTemplate(title, data, category) {
        try {
            await fetch('/api/conversation/template', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title,
                    data: data,
                    category: category,
                    keywords: Object.values(data).filter(v => typeof v === 'string')
                })
            });
        } catch (error) {
            console.error('Error saving template:', error);
        }
    }

    // Utility Functions
    clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            this.messagesContainer.innerHTML = '';
        }
    }

    async exportChat() {
        try {
            const response = await fetch(`/api/conversation/history?session_id=${this.sessionId}`);
            const data = await response.json();
            
            if (data.success) {
                const chatData = data.conversations.map(conv => ({
                    timestamp: conv.timestamp,
                    message: conv.message,
                    response: conv.response
                }));
                
                const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `chat_history_${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('Error exporting chat:', error);
        }
    }

    viewTransactionHistory() {
        this.messageInput.value = "Show my transaction history";
        this.sendMessage();
    }

    generateReport() {
        this.messageInput.value = "Generate my monthly transaction report";
        this.sendMessage();
    }
}

// Global functions for HTML onclick events
let chat;

function handleKeyPress(event) {
    chat.handleKeyPress(event);
}

function handleInput(event) {
    chat.handleInput(event);
}

function sendMessage() {
    chat.sendMessage();
}

function openTransactionForm() {
    chat.openTransactionForm();
}

function openBeneficiaryForm() {
    chat.openBeneficiaryForm();
}

function closeModal(modalId) {
    chat.closeModal(modalId);
}

function viewTransactionHistory() {
    chat.viewTransactionHistory();
}

function generateReport() {
    chat.generateReport();
}

function clearChat() {
    chat.clearChat();
}

function exportChat() {
    chat.exportChat();
}

function showBeneficiarySuggestions(query) {
    chat.showBeneficiarySuggestions(query);
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    chat = new SmartBankingChat();
});
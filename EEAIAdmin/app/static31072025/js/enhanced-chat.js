// Enhanced Chat JavaScript with Export Functionality

class EnhancedChat {
    constructor() {
        this.messages = [];
        this.currentSessionId = this.generateSessionId();
        this.isRecording = false;
        this.recognition = null;
        this.isDarkMode = localStorage.getItem('theme') === 'dark';
        this.initializeChat();
        this.setupEventListeners();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    initializeChat() {
        // Initialize theme
        if (this.isDarkMode) {
            document.body.classList.add('dark-mode');
        }
        this.updateThemeUI();

        // Initialize speech recognition if available
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
        }
    }

    setupEventListeners() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');

        // Auto-resize textarea
        messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateSendButtonState();
        });

        // Send on Enter
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Send button click
        sendBtn.addEventListener('click', () => this.sendMessage());

        // Voice button
        document.getElementById('voice-btn').addEventListener('click', () => this.toggleVoiceRecording());

        // Attach file button
        document.querySelector('.attach-btn').addEventListener('click', () => this.attachFile());

        // FAB button
        document.querySelector('.fab-btn').addEventListener('click', () => this.toggleFabMenu());

        // Close FAB menu on outside click
        document.addEventListener('click', (e) => {
            const fabContainer = document.querySelector('.fab-container');
            const fabMenu = document.getElementById('fab-menu');
            
            if (!fabContainer.contains(e.target) && fabMenu.classList.contains('active')) {
                fabMenu.classList.remove('active');
            }
        });

        // Export buttons
        document.querySelectorAll('.export-btn').forEach(btn => {
            btn.addEventListener('click', () => this.exportToExcel());
        });

        document.querySelectorAll('.pdf-btn').forEach(btn => {
            btn.addEventListener('click', () => this.exportToPDF());
        });

        document.querySelectorAll('.report-btn').forEach(btn => {
            btn.addEventListener('click', () => this.generateReport());
        });
    }

    autoResizeTextarea() {
        const textarea = document.getElementById('message-input');
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    updateSendButtonState() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        if (messageInput.value.trim()) {
            sendBtn.classList.add('active');
            sendBtn.disabled = false;
        } else {
            sendBtn.classList.remove('active');
            sendBtn.disabled = true;
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) return;

        // Add user message
        this.addMessage(message, 'user');
        this.messages.push({ role: 'user', content: message, timestamp: new Date() });

        // Clear input
        messageInput.value = '';
        this.autoResizeTextarea();
        this.updateSendButtonState();

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Call your API here
            const response = await this.callAPI(message);
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add AI response
            this.addMessage(response.content, 'assistant', response.isHtml);
            this.messages.push({ role: 'assistant', content: response.content, timestamp: new Date() });
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
        }
    }

    async callAPI(message) {
        // Placeholder for actual API call
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    content: `This is a response to: "${message}". In production, this would call your actual API.`,
                    isHtml: false
                });
            }, 1500);
        });
    }

    addMessage(content, role, isHtml = false) {
        const messagesContainer = document.getElementById('messages-container');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = role === 'user' 
            ? '<i class="fas fa-user"></i>' 
            : '<i class="fas fa-robot"></i>';

        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-role">${role === 'user' ? 'You' : 'AI Assistant'}</div>
                <div class="message-text">${isHtml ? content : this.escapeHtml(content)}</div>
                <div class="message-time">${time}</div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Add typewriter effect for assistant messages
        if (role === 'assistant' && !isHtml) {
            this.typewriterEffect(messageDiv.querySelector('.message-text'), content);
        }
    }

    typewriterEffect(element, text, speed = 20) {
        element.textContent = '';
        let index = 0;

        const cursor = document.createElement('span');
        cursor.className = 'typewriter-cursor';
        cursor.textContent = '|';
        element.appendChild(cursor);

        const type = () => {
            if (index < text.length) {
                if (element.contains(cursor)) {
                    element.removeChild(cursor);
                }
                element.textContent += text.charAt(index);
                element.appendChild(cursor);
                index++;
                setTimeout(type, speed + Math.random() * 30);
            } else {
                if (element.contains(cursor)) {
                    element.removeChild(cursor);
                }
            }
        };

        type();
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('messages-container');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant';
        typingDiv.id = 'typing-indicator';

        typingDiv.innerHTML = `
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-role">AI Assistant</div>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
        `;

        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    toggleVoiceRecording() {
        const voiceBtn = document.getElementById('voice-btn');
        
        if (!this.recognition) {
            this.showNotification('Voice recognition is not supported in your browser', 'error');
            return;
        }

        if (this.isRecording) {
            this.recognition.stop();
            this.isRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        } else {
            this.recognition.start();
            this.isRecording = true;
            voiceBtn.classList.add('recording');
            voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';

            this.recognition.onresult = (event) => {
                let finalTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript + ' ';
                    }
                }
                
                if (finalTranscript) {
                    const messageInput = document.getElementById('message-input');
                    messageInput.value += finalTranscript;
                    this.autoResizeTextarea();
                    this.updateSendButtonState();
                }
            };

            this.recognition.onerror = () => {
                this.isRecording = false;
                voiceBtn.classList.remove('recording');
                voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                this.showNotification('Voice recognition error', 'error');
            };
        }
    }

    attachFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.pdf,.docx,.txt,.jpg,.jpeg,.png,.xlsx,.csv';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileUpload(file);
            }
        };
        input.click();
    }

    handleFileUpload(file) {
        this.showNotification(`File "${file.name}" selected. Upload functionality to be implemented.`, 'info');
    }

    toggleFabMenu() {
        const menu = document.getElementById('fab-menu');
        menu.classList.toggle('active');
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
        this.updateThemeUI();
    }

    updateThemeUI() {
        const icon = document.getElementById('theme-icon');
        const text = document.getElementById('theme-text');
        if (this.isDarkMode) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            text.textContent = 'Light';
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
            text.textContent = 'Dark';
        }
    }

    // Export Functions
    exportToExcel() {
        const data = this.prepareExportData();
        let csv = 'Role,Message,Time\n';
        
        data.forEach(msg => {
            csv += `"${msg.role}","${msg.content.replace(/"/g, '""')}","${msg.time}"\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `chat_export_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        
        this.showNotification('Chat exported to Excel successfully', 'success');
    }

    exportToPDF() {
        // In production, you would use a library like jsPDF
        const content = this.messages.map(msg => {
            const time = new Date(msg.timestamp).toLocaleTimeString();
            return `${msg.role.toUpperCase()} (${time}): ${msg.content}`;
        }).join('\n\n');

        const blob = new Blob([content], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `chat_export_${new Date().toISOString().split('T')[0]}.txt`;
        link.click();
        
        this.showNotification('Chat exported as text (PDF export requires jsPDF library)', 'info');
    }

    generateReport() {
        const report = {
            sessionId: this.currentSessionId,
            totalMessages: this.messages.length,
            userMessages: this.messages.filter(m => m.role === 'user').length,
            aiMessages: this.messages.filter(m => m.role === 'assistant').length,
            startTime: this.messages[0]?.timestamp || new Date(),
            endTime: this.messages[this.messages.length - 1]?.timestamp || new Date()
        };

        const reportText = `
Chat Session Report
==================
Session ID: ${report.sessionId}
Total Messages: ${report.totalMessages}
User Messages: ${report.userMessages}
AI Messages: ${report.aiMessages}
Start Time: ${new Date(report.startTime).toLocaleString()}
End Time: ${new Date(report.endTime).toLocaleString()}
        `;

        const blob = new Blob([reportText], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `chat_report_${new Date().toISOString().split('T')[0]}.txt`;
        link.click();
        
        this.showNotification('Report generated successfully', 'success');
    }

    prepareExportData() {
        return this.messages.map(msg => ({
            role: msg.role === 'user' ? 'You' : 'AI Assistant',
            content: msg.content,
            time: new Date(msg.timestamp).toLocaleString()
        }));
    }

    clearChat() {
        if (confirm('Are you sure you want to clear the chat?')) {
            this.messages = [];
            document.getElementById('messages-container').innerHTML = '';
            this.addMessage('Chat cleared. How can I help you today?', 'assistant');
            this.toggleFabMenu();
        }
    }

    startNewChat() {
        this.currentSessionId = this.generateSessionId();
        this.messages = [];
        document.getElementById('messages-container').innerHTML = '';
        this.addMessage('Hello! I\'m starting a new conversation. How can I help you today?', 'assistant');
        this.toggleFabMenu();
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.enhancedChat = new EnhancedChat();
});

// Export global functions for HTML onclick handlers
window.toggleTheme = () => window.enhancedChat.toggleTheme();
window.sendMessage = () => window.enhancedChat.sendMessage();
window.toggleVoiceRecording = () => window.enhancedChat.toggleVoiceRecording();
window.attachFile = () => window.enhancedChat.attachFile();
window.toggleFabMenu = () => window.enhancedChat.toggleFabMenu();
window.startNewChat = () => window.enhancedChat.startNewChat();
window.clearChat = () => window.enhancedChat.clearChat();
window.exportChat = () => window.enhancedChat.exportToExcel();
window.showSettings = () => window.enhancedChat.showNotification('Settings panel to be implemented', 'info');
window.exportToExcel = () => window.enhancedChat.exportToExcel();
window.exportToPDF = () => window.enhancedChat.exportToPDF();
window.generateReport = () => window.enhancedChat.generateReport();
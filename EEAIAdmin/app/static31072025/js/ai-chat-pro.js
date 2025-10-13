// AI Chat Pro - Professional Bot Application
class AIChatPro {
    constructor() {
        this.currentSessionId = null;
        this.isRecording = false;
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.currentUtterance = null;
        this.theme = localStorage.getItem('theme') || 'light';
        
        this.init();
    }

    init() {
        // Hide loading screen after initialization
        setTimeout(() => {
            document.getElementById('loading-screen').classList.add('hidden');
        }, 1000);

        // Initialize theme
        this.applyTheme(this.theme);

        // Setup event listeners
        this.setupEventListeners();

        // Initialize speech recognition
        this.initializeSpeechRecognition();

        // Load sessions
        this.loadSessions();

        // Update UI state
        this.updateEmptyState();
        this.updateSendButton();

        // Auto-resize textarea
        this.setupAutoResize();

        // Initialize tooltips
        this.initializeTooltips();
    }

    setupEventListeners() {
        // Message input
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('input', () => {
            this.updateSendButton();
            this.autoResize();
        });

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for new chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.createNewChat();
            }
            
            // Ctrl/Cmd + / for focus input
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                messageInput.focus();
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }

    // Loading States
    showMessageSkeleton() {
        const skeleton = `
            <div class="message assistant skeleton-message">
                <div class="message-wrapper">
                    <div class="skeleton skeleton-avatar"></div>
                    <div class="message-content" style="width: 100%;">
                        <div class="skeleton skeleton-text short"></div>
                        <div class="skeleton skeleton-text long"></div>
                        <div class="skeleton skeleton-text medium"></div>
                    </div>
                </div>
            </div>
        `;
        
        const container = document.getElementById('messages-container');
        container.insertAdjacentHTML('beforeend', skeleton);
        this.scrollToBottom();
    }

    removeMessageSkeleton() {
        const skeleton = document.querySelector('.skeleton-message');
        if (skeleton) {
            skeleton.remove();
        }
    }

    // Message Handling
    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message) return;

        // Clear input
        input.value = '';
        this.updateSendButton();
        this.autoResize();

        // Add user message
        this.addMessage(message, 'user');

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send to API
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId,
                    include_context: true
                })
            });

            const data = await response.json();
            
            // Hide typing indicator
            this.hideTypingIndicator();

            if (data.error) {
                this.showToast('Error', data.error, 'error');
                return;
            }

            // Add assistant message with animation
            this.addMessage(data.response, 'assistant', true);

            // Update session
            this.currentSessionId = data.session_id;
            this.loadSessions();

        } catch (error) {
            this.hideTypingIndicator();
            this.showToast('Error', 'Failed to send message', 'error');
            console.error('Error:', error);
        }
    }

    addMessage(content, role, animate = false) {
        const container = document.getElementById('messages-container');
        const messageId = `msg-${Date.now()}`;
        
        const messageHtml = `
            <div class="message ${role}" id="${messageId}">
                <div class="message-wrapper">
                    <div class="message-avatar">
                        ${role === 'user' ? 'U' : 'AI'}
                    </div>
                    <div class="message-content">
                        <div class="message-role">${role}</div>
                        <div class="message-text">
                            ${animate ? '<span class="typing-text"></span><span class="cursor">|</span>' : this.formatMessage(content)}
                        </div>
                        <div class="message-actions">
                            <button class="message-action" onclick="aiChat.copyMessage('${messageId}')">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                            ${role === 'assistant' ? `
                                <button class="message-action" onclick="aiChat.speakMessage('${messageId}')">
                                    <i class="fas fa-volume-up"></i> Speak
                                </button>
                                <button class="message-action" onclick="aiChat.regenerateMessage('${messageId}')">
                                    <i class="fas fa-redo"></i> Regenerate
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', messageHtml);
        this.scrollToBottom();
        this.updateEmptyState();

        // Animate text if needed
        if (animate) {
            this.typewriterEffect(messageId, content);
        }
    }

    typewriterEffect(messageId, text) {
        const element = document.querySelector(`#${messageId} .typing-text`);
        const cursor = document.querySelector(`#${messageId} .cursor`);
        let index = 0;
        
        const formattedText = this.formatMessage(text);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = formattedText;
        const plainText = tempDiv.textContent || tempDiv.innerText;
        
        const type = () => {
            if (index < plainText.length) {
                element.textContent += plainText.charAt(index);
                index++;
                setTimeout(type, 20);
            } else {
                cursor.style.display = 'none';
                element.parentElement.innerHTML = formattedText;
            }
        };
        
        type();
    }

    formatMessage(content) {
        // Convert markdown to HTML
        content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
        content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        content = content.replace(/\n/g, '<br>');
        
        return content;
    }

    // Typing Indicator
    showTypingIndicator() {
        const indicator = `
            <div class="typing-indicator" id="typing-indicator">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
                <span>AI is thinking...</span>
            </div>
        `;
        
        const container = document.getElementById('messages-container');
        container.insertAdjacentHTML('beforeend', indicator);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Speech Recognition
    initializeSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onresult = (event) => {
                let finalTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript + ' ';
                    }
                }
                
                if (finalTranscript) {
                    const input = document.getElementById('message-input');
                    input.value += finalTranscript;
                    this.updateSendButton();
                    this.autoResize();
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.stopVoiceRecording();
                this.showToast('Error', 'Speech recognition failed', 'error');
            };
        }
    }

    toggleVoiceRecording() {
        if (this.isRecording) {
            this.stopVoiceRecording();
        } else {
            this.startVoiceRecording();
        }
    }

    startVoiceRecording() {
        if (!this.recognition) {
            this.showToast('Not Supported', 'Speech recognition is not supported in your browser', 'warning');
            return;
        }
        
        try {
            this.recognition.start();
            this.isRecording = true;
            const voiceBtn = document.getElementById('voice-btn');
            voiceBtn.classList.add('recording');
            voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.showToast('Error', 'Failed to start voice recording', 'error');
        }
    }

    stopVoiceRecording() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
            this.isRecording = false;
            const voiceBtn = document.getElementById('voice-btn');
            voiceBtn.classList.remove('recording');
            voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    }

    // Speech Synthesis
    speakMessage(messageId) {
        const messageEl = document.querySelector(`#${messageId} .message-text`);
        if (!messageEl) return;
        
        const text = messageEl.textContent || messageEl.innerText;
        this.speakText(text);
    }

    speakText(text) {
        if (!this.synthesis) {
            this.showToast('Not Supported', 'Speech synthesis is not supported in your browser', 'warning');
            return;
        }
        
        // Stop any ongoing speech
        this.stopSpeaking();
        
        this.currentUtterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance.rate = 1.0;
        this.currentUtterance.pitch = 1.0;
        this.currentUtterance.volume = 1.0;
        
        const indicator = document.getElementById('speaking-indicator');
        indicator.classList.add('active');
        
        this.currentUtterance.onend = () => {
            indicator.classList.remove('active');
        };
        
        this.synthesis.speak(this.currentUtterance);
    }

    stopSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
            const indicator = document.getElementById('speaking-indicator');
            indicator.classList.remove('active');
        }
    }

    // UI Actions
    copyMessage(messageId) {
        const messageEl = document.querySelector(`#${messageId} .message-text`);
        if (!messageEl) return;
        
        const text = messageEl.textContent || messageEl.innerText;
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Success', 'Message copied to clipboard', 'success');
        }).catch(() => {
            this.showToast('Error', 'Failed to copy message', 'error');
        });
    }

    regenerateMessage(messageId) {
        // Find the previous user message
        const messageEl = document.getElementById(messageId);
        const prevMessage = messageEl.previousElementSibling;
        
        if (prevMessage && prevMessage.classList.contains('user')) {
            const userText = prevMessage.querySelector('.message-text').textContent;
            // Remove the assistant message
            messageEl.remove();
            // Resend the user message
            this.sendMessage(userText);
        }
    }

    // Session Management
    async loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();
            
            if (data.success) {
                this.renderSessions(data.sessions);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    renderSessions(sessions) {
        const container = document.getElementById('session-list');
        container.innerHTML = '';
        
        sessions.forEach(session => {
            const sessionHtml = `
                <div class="session-item ${session.id === this.currentSessionId ? 'active' : ''}" 
                     onclick="aiChat.loadSession('${session.id}')">
                    <div class="session-title">${session.title || 'New Chat'}</div>
                    <div class="session-meta">
                        <span>${new Date(session.created_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>${session.message_count} messages</span>
                    </div>
                    <button class="session-delete" onclick="event.stopPropagation(); aiChat.deleteSession('${session.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', sessionHtml);
        });
    }

    async loadSession(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}/messages`);
            const data = await response.json();
            
            if (data.success) {
                this.currentSessionId = sessionId;
                this.renderMessages(data.messages);
                this.loadSessions(); // Update active state
            }
        } catch (error) {
            console.error('Error loading session:', error);
            this.showToast('Error', 'Failed to load session', 'error');
        }
    }

    renderMessages(messages) {
        const container = document.getElementById('messages-container');
        container.innerHTML = '';
        
        messages.forEach(msg => {
            this.addMessage(msg.content || msg.message, msg.role, false);
        });
        
        this.updateEmptyState();
    }

    async createNewChat() {
        this.currentSessionId = null;
        const container = document.getElementById('messages-container');
        container.innerHTML = '';
        this.updateEmptyState();
        this.showToast('Success', 'New chat created', 'success');
    }

    async deleteSession(sessionId) {
        if (!confirm('Are you sure you want to delete this chat?')) return;
        
        try {
            const response = await fetch(`/api/sessions/${sessionId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            if (data.success) {
                if (sessionId === this.currentSessionId) {
                    this.createNewChat();
                }
                this.loadSessions();
                this.showToast('Success', 'Chat deleted', 'success');
            }
        } catch (error) {
            console.error('Error deleting session:', error);
            this.showToast('Error', 'Failed to delete chat', 'error');
        }
    }

    // UI Utilities
    updateEmptyState() {
        const container = document.getElementById('messages-container');
        const emptyState = document.getElementById('empty-state');
        
        if (container.children.length === 0) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }
    }

    updateSendButton() {
        const input = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        if (input.value.trim()) {
            sendBtn.classList.add('active');
        } else {
            sendBtn.classList.remove('active');
        }
    }

    setupAutoResize() {
        const input = document.getElementById('message-input');
        input.addEventListener('input', () => this.autoResize());
    }

    autoResize() {
        const input = document.getElementById('message-input');
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    scrollToBottom() {
        const container = document.getElementById('messages-container');
        container.scrollTop = container.scrollHeight;
    }

    // Theme Management
    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.theme);
        localStorage.setItem('theme', this.theme);
    }

    applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        
        // Update theme icon
        const themeBtn = document.querySelector('.chat-action-btn i.fa-moon, .chat-action-btn i.fa-sun');
        if (themeBtn) {
            themeBtn.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    // Toast Notifications
    showToast(title, message, type = 'info') {
        const toastHtml = `
            <div class="toast ${type} animate__animated animate__fadeInRight">
                <div class="toast-icon">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
                </div>
                <div class="toast-content">
                    <div class="toast-title">${title}</div>
                    <div class="toast-message">${message}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        const container = document.getElementById('toast-container');
        container.insertAdjacentHTML('beforeend', toastHtml);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            const toast = container.lastElementChild;
            if (toast) {
                toast.classList.add('animate__fadeOutRight');
                setTimeout(() => toast.remove(), 500);
            }
        }, 5000);
    }

    // Mobile Support
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('open');
    }

    handleResize() {
        if (window.innerWidth > 768) {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.remove('open');
        }
    }

    // File Handling
    attachFile() {
        document.getElementById('file-input').click();
    }

    handleFileSelect(event) {
        const files = event.target.files;
        if (files.length === 0) return;
        
        // Handle file upload
        this.uploadFiles(files);
    }

    async uploadFiles(files) {
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.success) {
                this.showToast('Success', `${files.length} file(s) uploaded`, 'success');
                // Add a message about the uploaded files
                this.addMessage(`Uploaded ${files.length} file(s): ${Array.from(files).map(f => f.name).join(', ')}`, 'user');
            }
        } catch (error) {
            console.error('Error uploading files:', error);
            this.showToast('Error', 'Failed to upload files', 'error');
        }
    }

    // Export Chat
    exportChat() {
        const messages = document.querySelectorAll('.message');
        let content = 'AI Chat Export\n\n';
        
        messages.forEach(msg => {
            const role = msg.classList.contains('user') ? 'User' : 'Assistant';
            const text = msg.querySelector('.message-text').textContent;
            content += `${role}: ${text}\n\n`;
        });
        
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${new Date().toISOString()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.showToast('Success', 'Chat exported', 'success');
    }

    // Settings
    showSettings() {
        // Implement settings modal
        this.showToast('Info', 'Settings coming soon', 'info');
    }

    // Suggestions
    sendSuggestion(text) {
        const input = document.getElementById('message-input');
        input.value = text;
        this.updateSendButton();
        this.autoResize();
        this.sendMessage();
    }

    // Tooltips
    initializeTooltips() {
        // Add tooltips to buttons with title attribute
        const buttons = document.querySelectorAll('[title]');
        buttons.forEach(btn => {
            btn.addEventListener('mouseenter', (e) => {
                // Implement tooltip display
            });
        });
    }
}

// Initialize the chat application
const aiChat = new AIChatPro();

// Global function bindings
window.aiChat = aiChat;
window.sendMessage = () => aiChat.sendMessage();
window.toggleVoiceRecording = () => aiChat.toggleVoiceRecording();
window.stopSpeaking = () => aiChat.stopSpeaking();
window.sendSuggestion = (text) => aiChat.sendSuggestion(text);
window.createNewChat = () => aiChat.createNewChat();
window.toggleSidebar = () => aiChat.toggleSidebar();
window.toggleTheme = () => aiChat.toggleTheme();
window.exportChat = () => aiChat.exportChat();
window.showSettings = () => aiChat.showSettings();
window.attachFile = () => aiChat.attachFile();
window.handleFileSelect = (e) => aiChat.handleFileSelect(e);
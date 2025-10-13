/**
 * Enhanced Chatbot Controls
 * Provides minimize, maximize, close, and drag functionality
 */

class EnhancedChatbot {
    constructor() {
        this.isMaximized = false;
        this.isMinimized = false;
        this.isDragging = false;
        this.currentX = 0;
        this.currentY = 0;
        this.initialX = 0;
        this.initialY = 0;
        this.xOffset = 0;
        this.yOffset = 0;
        
        this.init();
    }
    
    init() {
        // Get elements
        this.overlay = document.getElementById('chatbotOverlay');
        this.window = document.getElementById('chatbotWindow');
        this.header = document.getElementById('chatbotHeader');
        this.iframe = document.getElementById('chatbotFrame');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
    }
    
    setupEventListeners() {
        // Drag functionality
        if (this.header) {
            this.header.addEventListener('mousedown', (e) => this.dragStart(e));
            document.addEventListener('mousemove', (e) => this.drag(e));
            document.addEventListener('mouseup', () => this.dragEnd());
            
            // Touch support for mobile
            this.header.addEventListener('touchstart', (e) => this.dragStart(e), {passive: false});
            document.addEventListener('touchmove', (e) => this.drag(e), {passive: false});
            document.addEventListener('touchend', () => this.dragEnd());
        }
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+C to toggle chatbot
            if (e.ctrlKey && e.shiftKey && e.key === 'C') {
                e.preventDefault();
                this.toggle();
            }
            
            // Escape to close chatbot
            if (e.key === 'Escape' && this.overlay.classList.contains('active')) {
                this.close();
            }
        });
    }
    
    open() {
        this.overlay.classList.add('active');
        this.window.classList.remove('minimized');
        this.isMinimized = false;
        
        // Initialize iframe with repository context if not already loaded
        this.initializeIframeWithRepository();
        
        // Send message to iframe
        this.sendMessage('chatbot_opened');
        
        // Add open animation
        this.window.style.animation = 'slideUp 0.3s ease';
    }
    
    initializeIframeWithRepository() {
        if (!this.iframe.src || this.iframe.src === 'about:blank' || !this.iframe.src.includes('ai_chat_modern')) {
            // Get repository config from global or session storage
            let repositoryConfig = null;
            
            // Try to get from global REPOSITORY_CONFIG if available
            if (typeof REPOSITORY_CONFIG !== 'undefined') {
                repositoryConfig = REPOSITORY_CONFIG;
            } else {
                // Try to get from session storage
                const activeRepo = sessionStorage.getItem('active_repository');
                if (activeRepo) {
                    repositoryConfig = JSON.parse(activeRepo);
                }
            }
            
            // Build URL with repository parameters
            if (repositoryConfig) {
                const params = new URLSearchParams({
                    repository_id: repositoryConfig.repository_id,
                    repository_name: repositoryConfig.repository_name,
                    repository_type: repositoryConfig.repository_type || '',
                    source: 'chatbot_overlay'
                });
                
                this.iframe.src = `/ai_chat_modern?${params.toString()}`;
                
                // Set up load event to send context after iframe loads
                this.iframe.onload = () => {
                    setTimeout(() => {
                        this.iframe.contentWindow.postMessage({
                            type: 'repository_context',
                            repository: repositoryConfig,
                            source: 'chatbot_overlay',
                            connected: true
                        }, '*');
                        console.log('Repository context sent to chatbot overlay');
                    }, 500);
                };
            } else {
                // Load without repository context
                this.iframe.src = '/ai_chat_modern';
            }
        } else {
            // Iframe already loaded, just send updated context
            this.sendRepositoryContext();
        }
    }
    
    sendRepositoryContext() {
        let repositoryConfig = null;
        
        // Try to get from global REPOSITORY_CONFIG if available
        if (typeof REPOSITORY_CONFIG !== 'undefined') {
            repositoryConfig = REPOSITORY_CONFIG;
        } else {
            // Try to get from session storage
            const activeRepo = sessionStorage.getItem('active_repository');
            if (activeRepo) {
                repositoryConfig = JSON.parse(activeRepo);
            }
        }
        
        if (repositoryConfig && this.iframe.contentWindow) {
            this.iframe.contentWindow.postMessage({
                type: 'repository_context',
                repository: repositoryConfig,
                source: 'chatbot_overlay',
                connected: true
            }, '*');
        }
    }
    
    close() {
        this.overlay.classList.remove('active');
        this.isMaximized = false;
        this.isMinimized = false;
        this.window.classList.remove('maximized', 'minimized');
        
        // Reset position
        this.xOffset = 0;
        this.yOffset = 0;
        this.window.style.transform = 'translate(-50%, -50%)';
        
        // Send message to iframe
        this.sendMessage('chatbot_closed');
    }
    
    toggle() {
        if (this.overlay.classList.contains('active')) {
            this.close();
        } else {
            this.open();
        }
    }
    
    minimize() {
        if (this.isMinimized) {
            this.window.classList.remove('minimized');
            this.isMinimized = false;
            
            // Restore maximize state if was maximized
            if (this.isMaximized) {
                this.window.classList.add('maximized');
            }
        } else {
            this.window.classList.add('minimized');
            this.window.classList.remove('maximized');
            this.isMinimized = true;
        }
        
        // Send message to iframe
        this.sendMessage('chatbot_minimized', { minimized: this.isMinimized });
    }
    
    maximize() {
        if (this.isMaximized) {
            this.window.classList.remove('maximized');
            this.isMaximized = false;
        } else {
            this.window.classList.add('maximized');
            this.window.classList.remove('minimized');
            this.isMaximized = true;
            this.isMinimized = false;
        }
        
        // Send message to iframe
        this.sendMessage('chatbot_maximized', { maximized: this.isMaximized });
    }
    
    dragStart(e) {
        // Don't drag if clicking on controls
        if (e.target.closest('.window-controls')) return;
        
        // Get initial position
        const touch = e.type.includes('touch') ? e.touches[0] : e;
        this.initialX = touch.clientX - this.xOffset;
        this.initialY = touch.clientY - this.yOffset;
        
        if (e.target === this.header || this.header.contains(e.target)) {
            this.isDragging = true;
            this.header.style.cursor = 'grabbing';
        }
    }
    
    drag(e) {
        if (this.isDragging) {
            e.preventDefault();
            
            const touch = e.type.includes('touch') ? e.touches[0] : e;
            this.currentX = touch.clientX - this.initialX;
            this.currentY = touch.clientY - this.initialY;
            
            this.xOffset = this.currentX;
            this.yOffset = this.currentY;
            
            // Only allow dragging if not maximized or minimized
            if (!this.isMaximized && !this.isMinimized) {
                this.window.style.transform = `translate(calc(-50% + ${this.currentX}px), calc(-50% + ${this.currentY}px))`;
            }
        }
    }
    
    dragEnd() {
        this.initialX = this.currentX;
        this.initialY = this.currentY;
        this.isDragging = false;
        this.header.style.cursor = 'move';
    }
    
    sendMessage(type, data = {}) {
        if (this.iframe && this.iframe.contentWindow) {
            this.iframe.contentWindow.postMessage({
                type: type,
                ...data,
                timestamp: new Date().toISOString()
            }, '*');
        }
    }
    
    // Handle overlay click
    handleOverlayClick(event) {
        if (event.target === this.overlay) {
            this.close();
        }
    }
}

// Global instance
let chatbot = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    chatbot = new EnhancedChatbot();
});

// Global functions for backward compatibility
function openChatbot() {
    if (chatbot) chatbot.open();
}

function closeChatbot() {
    if (chatbot) chatbot.close();
}

function closeChatbotOnOverlay(event) {
    if (chatbot) chatbot.handleOverlayClick(event);
}

function minimizeChatbot() {
    if (chatbot) chatbot.minimize();
}

function maximizeChatbot() {
    if (chatbot) chatbot.maximize();
}

// Handle messages from iframe
window.addEventListener('message', function(event) {
    if (event.data) {
        switch(event.data.type) {
            case 'close_chatbot':
                closeChatbot();
                break;
            case 'minimize_chatbot':
                minimizeChatbot();
                break;
            case 'maximize_chatbot':
                maximizeChatbot();
                break;
        }
    }
});
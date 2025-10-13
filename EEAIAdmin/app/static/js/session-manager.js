/**
 * Session Manager - Handles chat session operations without manual functionality
 */

class SessionManager {
    constructor() {
        this.sessionsContainer = null;
        this.currentSessionId = localStorage.getItem('currentSessionId');
        this.userId = null;
        this.init();
    }

    init() {
        // Get user ID from page or session
        this.userId = document.getElementById('userId')?.value || 
                     sessionStorage.getItem('userId');
        
        // Create sessions UI container if doesn't exist
        this.createSessionsUI();
        
        // Load sessions on init
        this.loadSessions();
        
        // Set up event listeners
        this.setupEventListeners();
    }

    createSessionsUI() {
        // Check if container already exists
        if (document.getElementById('sessions-container')) {
            this.sessionsContainer = document.getElementById('sessions-container');
            return;
        }
    }

    setupEventListeners() {
        // Session item clicks (delegated)
        this.sessionsContainer?.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent any default link behavior
            const sessionItem = e.target.closest('.session-item');
            const deleteBtn = e.target.closest('.delete-session');
            
            if (deleteBtn && sessionItem) {
                e.stopPropagation();
                const sessionId = sessionItem.dataset.sessionId;
                this.deleteSession(sessionId);
            } else if (sessionItem) {
                e.stopPropagation();
                const sessionId = sessionItem.dataset.sessionId;
                console.log('Session item clicked:', sessionId);
                this.loadSession(sessionId);
            }
        });
    }

    async loadSessions() {
        try {
            this.showLoading();
            
            // Get user_id from localStorage (set during login)
            const userId = localStorage.getItem('user_id');
            const url = userId ? `/api/sessions?user_id=${userId}` : '/api/sessions';
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to load sessions');
            }

            const data = await response.json();
            this.displaySessions(data.sessions);
            
        } catch (error) {
            console.error('Error loading sessions:', error);
            this.showError('Failed to load sessions');
        }
    }

    displaySessions(sessions) {
        if (!sessions || sessions.length === 0) {
            this.sessionsContainer.innerHTML = `
                <div class="no-sessions">
                    <i class="fas fa-comments"></i>
                    <p>No chat sessions found</p>
                </div>
            `;
            return;
        }

        this.sessionsContainer.innerHTML = sessions.map(session => `
            <div class="session-item ${session.session_id === this.currentSessionId ? 'active' : ''}" 
                 data-session-id="${session.session_id}">
                <div class="session-info">
                    <div class="session-title">
                        Session ${this.formatSessionId(session.session_id)}
                    </div>
                    <div class="session-meta">
                        <span class="message-count">
                            <i class="fas fa-comment"></i> ${session.message_count}
                        </span>
                        <span class="last-activity">
                            ${this.formatDate(session.last_activity)}
                        </span>
                    </div>
                </div>
                <button class="delete-session" title="Delete session">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }

    async loadSession(sessionId) {
        try {
            console.log('Loading session:', sessionId);
            const userId = localStorage.getItem('user_id');
            const url = userId ? `/api/sessions/${sessionId}/messages?user_id=${userId}` : `/api/sessions/${sessionId}/messages`;
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load session messages');
            }

            const data = await response.json();
            console.log('Session data loaded:', data);
            
            // Update current session
            this.currentSessionId = sessionId;
            localStorage.setItem('currentSessionId', sessionId);
            
            // Update UI to show active session
            document.querySelectorAll('.session-item').forEach(item => {
                item.classList.toggle('active', item.dataset.sessionId === sessionId);
            });
            
            // Load messages in chat (emit event for chat handler)
            console.log('Dispatching sessionLoaded event with messages:', data.messages);
            window.dispatchEvent(new CustomEvent('sessionLoaded', {
                detail: { sessionId, messages: data.messages }
            }));
            
        } catch (error) {
            console.error('Error loading session:', error);
            this.showError('Failed to load session messages');
        }
    }

    async deleteSession(sessionId) {
        const confirmDelete = confirm('Are you sure you want to delete this session? This cannot be undone.');
        
        if (!confirmDelete) return;

        try {
            const userId = localStorage.getItem('user_id');
            const url = userId ? `/api/sessions/${sessionId}?user_id=${userId}` : `/api/sessions/${sessionId}`;
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to delete session');
            }

            // If deleted session was current, clear it
            if (sessionId === this.currentSessionId) {
                this.currentSessionId = null;
                localStorage.removeItem('currentSessionId');
                window.dispatchEvent(new CustomEvent('sessionDeleted', {
                    detail: { sessionId }
                }));
            }

            // Reload sessions
            this.loadSessions();
            
            this.showSuccess('Session deleted successfully');
            
        } catch (error) {
            console.error('Error deleting session:', error);
            this.showError('Failed to delete session');
        }
    }

    async deleteAllSessions() {
        const confirmDelete = confirm(
            'Are you sure you want to delete ALL chat sessions? This cannot be undone.'
        );
        
        if (!confirmDelete) return;

        try {
            const userId = localStorage.getItem('user_id');
            const url = userId ? `/api/sessions/all?user_id=${userId}` : '/api/sessions/all';
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ confirm: true, user_id: userId }),
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to delete sessions');
            }

            // Clear current session
            this.currentSessionId = null;
            localStorage.removeItem('currentSessionId');
            
            // Notify chat to clear
            window.dispatchEvent(new CustomEvent('allSessionsDeleted'));
            
            // Reload sessions
            this.loadSessions();
            
            this.showSuccess('All sessions deleted successfully');
            
        } catch (error) {
            console.error('Error deleting all sessions:', error);
            this.showError('Failed to delete sessions');
        }
    }

    formatSessionId(sessionId) {
        // Extract readable part from session ID
        const parts = sessionId.split('_');
        if (parts.length >= 2 && parts[1]) {
            const timestamp = parseInt(parts[1]);
            if (!isNaN(timestamp)) {
                return new Date(timestamp).toLocaleString();
            }
        }
        return sessionId.substring(0, 20) + '...';
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        // Less than 1 minute
        if (diff < 60000) {
            return 'Just now';
        }
        
        // Less than 1 hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes} min${minutes > 1 ? 's' : ''} ago`;
        }
        
        // Less than 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }
        
        // More than 24 hours
        return date.toLocaleDateString();
    }

    getRandomLoadingMessage() {
        const messages = [
            'Loading your conversations...',
            'Fetching chat history...',
            'Retrieving your sessions...',
            'Getting your recent chats...',
            'Loading conversation history...'
        ];
        return messages[Math.floor(Math.random() * messages.length)];
    }
    
    showLoading() {
        // Show modern loading design with spinner and skeleton cards
        const loadingHTML = `
            <div class="sessions-loading">
                <div class="loading-spinner"></div>
                <div class="loading-text">${this.getRandomLoadingMessage()}</div>
            </div>
            <div class="session-skeleton">
                <div class="skeleton-content">
                    <div class="skeleton-info">
                        <div class="skeleton-title"></div>
                        <div class="skeleton-meta">
                            <div class="skeleton-meta-item"></div>
                            <div class="skeleton-meta-item"></div>
                        </div>
                    </div>
                    <div class="skeleton-action"></div>
                </div>
            </div>
            <div class="session-skeleton" style="animation-delay: 0.1s;">
                <div class="skeleton-content">
                    <div class="skeleton-info">
                        <div class="skeleton-title"></div>
                        <div class="skeleton-meta">
                            <div class="skeleton-meta-item"></div>
                            <div class="skeleton-meta-item"></div>
                        </div>
                    </div>
                    <div class="skeleton-action"></div>
                </div>
            </div>
            <div class="session-skeleton" style="animation-delay: 0.2s;">
                <div class="skeleton-content">
                    <div class="skeleton-info">
                        <div class="skeleton-title"></div>
                        <div class="skeleton-meta">
                            <div class="skeleton-meta-item"></div>
                            <div class="skeleton-meta-item"></div>
                        </div>
                    </div>
                    <div class="skeleton-action"></div>
                </div>
            </div>
        `;
        this.sessionsContainer.innerHTML = loadingHTML;
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'notification error';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => errorDiv.remove(), 3000);
    }

    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'notification success';
        successDiv.textContent = message;
        document.body.appendChild(successDiv);
        
        setTimeout(() => successDiv.remove(), 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing SessionManager');
    window.sessionManager = new SessionManager();
    
    // Add global click handler to prevent any navigation
    document.addEventListener('click', (e) => {
        // Check if click is within sessions container
        if (e.target.closest('#sessions-container')) {
            const link = e.target.closest('a');
            if (link) {
                e.preventDefault();
                console.log('Prevented link navigation in sessions container');
            }
        }
    }, true);
});

// Export for use in other modules
window.SessionManager = SessionManager;
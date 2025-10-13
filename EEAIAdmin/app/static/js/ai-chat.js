// AI Chat Interface JavaScript
let currentSessionId = null;
let selectedFile = null;
let isDarkMode = false;
let isAuthenticated = false;

// Global repository context
let currentRepositoryContext = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded - Initializing AI Chat');
    initializeTheme();
    checkAuthentication();
    initializeChat();
    setupEventListeners();
    autoResizeTextarea();
    initializeRepositoryContext();
    setupRepositoryClickHandler();

    // Listen for session events from session manager
    window.addEventListener('sessionLoaded', function(event) {
        console.log('sessionLoaded event received:', event.detail);
        const { sessionId, messages } = event.detail;
        currentSessionId = sessionId;
        displaySessionMessages(messages);
    });

    window.addEventListener('sessionDeleted', function(event) {
        const { sessionId } = event.detail;
        if (sessionId === currentSessionId) {
            clearCurrentChat();
        }
    });

    window.addEventListener('allSessionsDeleted', function() {
        clearCurrentChat();
    });
    
    // Listen for messages from parent window
    window.addEventListener('message', function(event) {
        // Handle repository context
        if (event.data && event.data.type === 'repository_context') {
            console.log('Received repository context:', event.data.repository);
            currentRepositoryContext = event.data.repository;
            
            // Ensure we have the proper repository name format
            if (currentRepositoryContext && !currentRepositoryContext.repository_name) {
                // Map repository ID to name
                const repoMap = {
                    'trade_finance': 'Trade Finance',
                    'treasury': 'Treasury',
                    'cash_management': 'Cash Management'
                };
                currentRepositoryContext.repository_name = repoMap[currentRepositoryContext.repository_id] || currentRepositoryContext.repository_id;
            }
            
            // Store in sessionStorage for persistence
            if (currentRepositoryContext) {
                sessionStorage.setItem('active_repository', JSON.stringify(currentRepositoryContext));
                updateRepositoryDisplay();
            }
        }
        
        // Handle form context from parent form
        if (event.data && event.data.type === 'form_context') {
            console.log('Received form context:', event.data.formData);
            // Store the form context for use in messages
            window.currentFormContext = event.data.formData;
            window.currentFormType = event.data.formType;
            
            // Store in sessionStorage for persistence
            sessionStorage.setItem('current_form_data', JSON.stringify(event.data.formData));
            sessionStorage.setItem('current_form_type', event.data.formType);
            
            // Show a subtle indicator that form data is available
            updateFormContextIndicator(event.data.formData);
        }
    });
    
    // Function to update form context indicator
    function updateFormContextIndicator(formData) {
        // Count filled fields
        const filledFields = Object.keys(formData).filter(key => formData[key] && formData[key] !== '').length;
        
        if (filledFields > 0) {
            // Show an indicator in the chat
            const indicator = document.getElementById('form-context-indicator');
            if (!indicator) {
                const header = document.querySelector('.chat-header');
                if (header) {
                    const newIndicator = document.createElement('div');
                    newIndicator.id = 'form-context-indicator';
                    newIndicator.style.cssText = 'padding: 4px 10px; background: rgba(16, 185, 129, 0.1); border-radius: 15px; font-size: 11px; color: #10b981; display: inline-flex; align-items: center; gap: 5px; margin-left: 10px;';
                    newIndicator.innerHTML = `<i class="fas fa-form"></i> Form data available (${filledFields} fields)`;
                    header.appendChild(newIndicator);
                }
            } else {
                indicator.innerHTML = `<i class="fas fa-form"></i> Form data available (${filledFields} fields)`;
            }
        }
    }
});

// Initialize repository context from URL or storage
function initializeRepositoryContext() {
    // First try URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('repository_id')) {
        currentRepositoryContext = {
            repository_id: urlParams.get('repository_id'),
            repository_name: urlParams.get('repository_name'),
            repository_type: urlParams.get('repository_type'),
            source: urlParams.get('source')
        };
        
        // Ensure repository name is set properly
        if (!currentRepositoryContext.repository_name || currentRepositoryContext.repository_name === 'null') {
            const repoMap = {
                'trade_finance': 'Trade Finance',
                'treasury': 'Treasury',
                'cash_management': 'Cash Management'
            };
            currentRepositoryContext.repository_name = repoMap[currentRepositoryContext.repository_id] || currentRepositoryContext.repository_id;
        }
        
        console.log('Initialized repository context from URL:', currentRepositoryContext);
    } else {
        // Fallback to sessionStorage
        const activeRepo = sessionStorage.getItem('active_repository');
        if (activeRepo) {
            currentRepositoryContext = JSON.parse(activeRepo);
            
            // Ensure repository name is set
            if (currentRepositoryContext && !currentRepositoryContext.repository_name) {
                const repoMap = {
                    'trade_finance': 'Trade Finance',
                    'treasury': 'Treasury',
                    'cash_management': 'Cash Management'
                };
                currentRepositoryContext.repository_name = repoMap[currentRepositoryContext.repository_id] || currentRepositoryContext.repository_id;
            }
            
            console.log('Initialized repository context from storage:', currentRepositoryContext);
        }
    }
    
    if (currentRepositoryContext) {
        // Store the updated context with proper repository name
        sessionStorage.setItem('active_repository', JSON.stringify(currentRepositoryContext));
        updateRepositoryDisplay();
    }
}

// Update UI to show connected repository
function updateRepositoryDisplay() {
    if (!currentRepositoryContext) {
        // No repository context - update display to show disconnected
        updateRepositoryStatusDisplay(null, null);
        return;
    }
    
    // Update the repository status display
    updateRepositoryStatusDisplay(currentRepositoryContext.repository_id, currentRepositoryContext.repository_name);
    
    // Update header or create repository indicator
    const header = document.querySelector('.chat-header');
    if (header) {
        let indicator = document.getElementById('repository-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'repository-indicator';
            indicator.style.cssText = 'padding: 5px 15px; background: rgba(102, 126, 234, 0.1); border-radius: 20px; font-size: 12px; color: #667eea; display: inline-flex; align-items: center; gap: 5px;';
            header.appendChild(indicator);
        }
        indicator.innerHTML = `<i class="fas fa-database"></i> Connected to ${currentRepositoryContext.repository_name}`;
    }
}

// Update repository status display element
function updateRepositoryStatusDisplay(repoId, repoName) {
    const statusElement = document.getElementById('repository-connection-status');
    const statusText = document.getElementById('repository-status-text');
    const indicatorElement = document.getElementById('connection-indicator');
    
    if (!statusElement || !statusText) {
        console.log('Repository status elements not found');
        return;
    }
    
    if (repoId && repoName) {
        // Repository is connected
        statusElement.classList.add('connected');
        statusText.textContent = repoName;
        statusText.title = `Connected to: ${repoName}`;
        
        // Add tooltip for full name if truncated
        if (repoName.length > 20) {
            statusText.title = repoName;
            statusText.textContent = repoName.substring(0, 17) + '...';
        }
        
        console.log(`Repository status updated: Connected to ${repoName}`);
    } else {
        // No repository connected
        statusElement.classList.remove('connected');
        statusText.textContent = 'No Repository';
        statusText.title = 'Click to connect a repository';
        
        console.log('Repository status updated: No repository connected');
    }
    
    // Also update the repository manager if available
    if (window.repositoryManager) {
        window.repositoryManager.connectedRepoId = repoId;
        window.repositoryManager.updateConnectionStatusDisplay(repoName);
    }
}

// Setup click handler for repository status
function setupRepositoryClickHandler() {
    const statusElement = document.getElementById('repository-connection-status');
    if (statusElement) {
        statusElement.addEventListener('click', function() {
            // If repository manager exists, use it to show repository list
            if (window.repositoryManager) {
                window.repositoryManager.showRepositoryList();
            } else {
                // Otherwise show a simple repository selection
                showRepositorySelection();
            }
        });
    }
}

// Show simple repository selection dialog
function showRepositorySelection() {
    const repositories = [
        { id: 'trade_finance', name: 'Trade Finance' },
        { id: 'treasury', name: 'Treasury' },
        { id: 'cash_management', name: 'Cash Management' }
    ];
    
    const repoList = repositories.map(repo => 
        `${repo.name} (${repo.id})`
    ).join('\n');
    
    const selection = prompt(`Select a repository to connect:\n${repoList}\n\nEnter repository ID:`, 'trade_finance');
    
    if (selection) {
        const selectedRepo = repositories.find(r => r.id === selection);
        if (selectedRepo) {
            // Set the repository context
            currentRepositoryContext = {
                repository_id: selectedRepo.id,
                repository_name: selectedRepo.name,
                repository_type: selectedRepo.id,
                selected_manually: true
            };
            
            // Store in sessionStorage
            sessionStorage.setItem('active_repository', JSON.stringify(currentRepositoryContext));
            
            // Update display
            updateRepositoryDisplay();
            
            // Show notification
            showNotification(`Connected to ${selectedRepo.name} repository`, 'success');
        }
    }
}

// Check authentication status
async function checkAuthentication() {
    // Check if user_id exists in localStorage (set by login)
    const userId = localStorage.getItem('user_id');
    isAuthenticated = !!userId;

    if (isAuthenticated) {
        // Load user-specific data
        loadUserManuals();
        loadChatHistory();
    } else {
        // Show login prompt in sidebar
        showLoginPrompt();
    }
}

// Initialize theme
function initializeTheme() {
    // Get theme from localStorage
    const savedTheme = localStorage.getItem('theme');
    isDarkMode = savedTheme === 'dark';

    // Apply theme
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        updateThemeUI();
    }
}

// Toggle theme
function toggleTheme() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('dark-mode', isDarkMode);
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    updateThemeUI();
    showNotification(`Switched to ${isDarkMode ? 'dark' : 'light'} mode`, 'info');
}

// Update theme UI
function updateThemeUI() {
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');

    if (isDarkMode) {
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
        themeText.textContent = 'Light';
    } else {
        themeIcon.classList.remove('fa-sun');
        themeIcon.classList.add('fa-moon');
        themeText.textContent = 'Dark';
    }
}

// Initialize chat session
function initializeChat() {
    // Check if there's an existing session or create a new one
    const savedSessionId = localStorage.getItem('currentSessionId');
    if (savedSessionId) {
        currentSessionId = savedSessionId;
        // Try to load conversation from backend, but don't fail if it doesn't work
        loadConversation(currentSessionId).catch(() => {
            console.log('Could not load conversation from backend, starting fresh');
        });
    } else {
        startNewChat();
    }
    
    // Add centered class to input area initially if no messages
    checkInputPosition();
}

// Start a new chat session
function startNewChat() {
    currentSessionId = generateSessionId();
    localStorage.setItem('currentSessionId', currentSessionId);
    clearMessages();
    addWelcomeMessage();
    updateChatTitle('New Chat');
    saveSession();
    checkInputPosition();
}

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Setup event listeners
function setupEventListeners() {
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const fileUploadArea = document.getElementById('file-upload-area');

    // Enter key to send (Shift+Enter for new line)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', autoResizeTextarea);

    // File upload drag and drop
    fileUploadArea.addEventListener('dragover', handleDragOver);
    fileUploadArea.addEventListener('dragleave', handleDragLeave);
    fileUploadArea.addEventListener('drop', handleDrop);

    // Close modal on background click
    document.getElementById('upload-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeUploadModal();
        }
    });
}

// Enhanced auto-resize with smooth animation
function autoResizeTextarea() {
    const textarea = document.getElementById('message-input');
    const inputWrapper = textarea.closest('.input-wrapper');
    
    // Store original height
    const originalHeight = textarea.style.height;
    
    // Reset height to auto to get scrollHeight
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 200);
    
    // Animate height change
    textarea.style.transition = 'height 0.1s ease';
    textarea.style.height = newHeight + 'px';
    
    // Update wrapper padding for better visual balance
    if (newHeight > 40) {
        inputWrapper.style.padding = '12px 12px 12px 20px';
    } else {
        inputWrapper.style.padding = '8px 8px 8px 20px';
    }
    
    // Update character counter
    updateCharacterCounter();
}

// Toggle sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    // On mobile, toggle open class and overlay
    if (window.innerWidth <= 768) {
        sidebar.classList.toggle('open');
        if (sidebar.classList.contains('open')) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    } else {
        sidebar.classList.toggle('collapsed');
    }
}

// Close sidebar (mobile)
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
}

// Show login prompt
function showLoginPrompt() {
    const manualList = document.getElementById('manual-list');
    const chatHistory = document.getElementById('chat-history');

    manualList.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fas fa-lock" style="font-size: 32px; color: var(--text-secondary); margin-bottom: 10px;"></i>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 15px;">Login to access your manuals and chat history</p>
            <button onclick="window.location.href='/main'" style="
                padding: 10px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
            ">Login</button>
        </div>
    `;

    // Clear chat history section
    const existingTitle = chatHistory.querySelector('.section-title');
    chatHistory.innerHTML = '';
    if (existingTitle) {
        chatHistory.appendChild(existingTitle);
    }
}

// Load user manuals
async function loadUserManuals() {
    if (!isAuthenticated) return;
    
    // All users can view manuals

    try {
        const userId = localStorage.getItem('user_id');
        const response = await fetch(`/api/user-manuals${userId ? `?user_id=${userId}` : ''}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            if (response.status === 401) {
                isAuthenticated = false;
                showLoginPrompt();
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        const manualList = document.getElementById('manual-list');
        manualList.innerHTML = '';

        if (data.success && data.manuals.length > 0) {
            data.manuals.forEach(manual => {
                const manualItem = createManualItem(manual);
                manualList.appendChild(manualItem);
            });
        } else {
            manualList.innerHTML = '<div style="color: var(--text-secondary); font-size: 13px; text-align: center;">No manuals uploaded</div>';
        }
    } catch (error) {
        console.error('Error loading manuals:', error);
    }
}

// Create manual item element
function createManualItem(manualName) {
    const div = document.createElement('div');
    div.className = 'manual-item';
    
    // Check if user is admin to show delete button
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    const isAdmin = userInfo.isAdmin === true;
    
    div.innerHTML = `
        <span class="manual-name" title="${manualName}">${manualName}</span>
        ${isAdmin ? `<i class="fas fa-trash delete-manual-btn" onclick="deleteManual('${manualName}')"></i>` : ''}
    `;
    return div;
}

// Delete manual
async function deleteManual(manualName) {
    // Check if user is admin
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    if (userInfo.isAdmin !== true) {
        showNotification('Only administrators can delete manuals', 'error');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete "${manualName}"?`)) {
        return;
    }

    try {
        const userId = localStorage.getItem('user_id');
        const response = await fetch(`/api/user-manuals/${encodeURIComponent(manualName)}${userId ? `?user_id=${userId}` : ''}`, {
            method: 'DELETE',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        if (data.success) {
            loadUserManuals();
            showNotification('Manual deleted successfully', 'success');
        } else {
            showNotification(data.message || 'Failed to delete manual', 'error');
        }
    } catch (error) {
        console.error('Error deleting manual:', error);
        showNotification('Error deleting manual', 'error');
    }
}

// Load chat history
async function loadChatHistory() {
    if (!isAuthenticated) return;

    // Let session manager handle loading sessions
    if (window.sessionManager) {
        window.sessionManager.loadSessions();
    }
}

// Group conversations by session
function groupConversationsBySession(conversations) {
    const sessions = {};

    conversations.forEach(message => {
        const sessionId = message.session_id || 'default';
        if (!sessions[sessionId]) {
            sessions[sessionId] = {
                messages: [],
                firstMessage: message.timestamp,
                lastMessage: message.timestamp,
                title: ''
            };
        }

        sessions[sessionId].messages.push(message);
        sessions[sessionId].lastMessage = message.timestamp;

        // Use first user message as title
        if (message.message && !sessions[sessionId].title) {
            sessions[sessionId].title = message.message.substring(0, 50) +
                (message.message.length > 50 ? '...' : '');
        }
    });

    return sessions;
}

// Create chat history item
function createChatItem(sessionId, session) {
    const div = document.createElement('div');
    div.className = 'chat-item';
    if (sessionId === currentSessionId) {
        div.classList.add('active');
    }

    const date = new Date(session.lastMessage);
    const timeAgo = getTimeAgo(date);

    div.innerHTML = `
        <div class="chat-item-title">${session.title || 'New Chat'}</div>
        <div class="chat-item-time">${timeAgo}</div>
    `;

    div.onclick = (e) => loadConversation(sessionId, e);

    return div;
}

// Get time ago string
function getTimeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
}

// Load specific conversation
async function loadConversation(sessionId, event) {
    currentSessionId = sessionId;
    localStorage.setItem('currentSessionId', sessionId);

    // If not authenticated, try to load from local storage
    if (!isAuthenticated) {
        loadLocalConversation(sessionId);
        return;
    }

    try {
        const response = await fetch(`/api/conversation/history?session_id=${sessionId}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            console.error('Failed to load conversation:', response.status);
            // Fall back to local storage
            loadLocalConversation(sessionId);
            return;
        }

        const data = await response.json();

        // The API returns 'conversations' (plural)
        const conversations = data.conversations || [];

        // Convert conversation format to message format
        const messages = [];
        conversations.forEach(conv => {
            // Add user message if exists
            if (conv.message) {
                messages.push({
                    content: conv.message,
                    role: 'user',
                    timestamp: conv.timestamp
                });
            }
            // Add assistant response if exists
            if (conv.response) {
                messages.push({
                    content: conv.response,
                    role: 'assistant',
                    timestamp: conv.timestamp
                });
            }
        });

        displayConversation(messages);

        // Update active state in sidebar
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });

        // Find and highlight the active chat item
        if (event && event.target) {
            event.target.closest('.chat-item')?.classList.add('active');
        } else {
            // If no event, try to find the chat item by session ID
            document.querySelectorAll('.chat-item').forEach(item => {
                if (item.onclick && item.onclick.toString().includes(sessionId)) {
                    item.classList.add('active');
                }
            });
        }
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

// Load conversation from local storage
function loadLocalConversation(sessionId) {
    const key = `chat_history_${sessionId}`;
    const history = JSON.parse(localStorage.getItem(key) || '[]');
    displayConversation(history);
}

// Display conversation messages
function displayConversation(messages) {
    clearMessages();
    messages.forEach(message => {
        addMessage(message.content, message.role);
    });
    scrollToBottom();
}

// Send message
async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();

    if (!message) return;

    // Disable input
    messageInput.disabled = true;
    document.getElementById('send-btn').disabled = true;

    // Add user message
    addMessage(message, 'user');

    // Clear input
    messageInput.value = '';
    autoResizeTextarea();

    // Show typing indicator
    showTypingIndicator();

    try {
        // Store user message locally first
        storeMessage(message, 'user', true);

        // Use global repository context or get from storage
        let repositoryContext = currentRepositoryContext;
        
        // If not in global, try sessionStorage
        if (!repositoryContext) {
            const activeRepo = sessionStorage.getItem('active_repository');
            if (activeRepo) {
                repositoryContext = JSON.parse(activeRepo);
            }
        }
        
        // Log repository context for debugging
        console.log('Sending message with repository context:', repositoryContext);

        // Send to API
        const userId = localStorage.getItem('user_id');
        const requestBody = {
            query: message,
            session_id: currentSessionId,
            user_id: userId
        };
        
        // Add form context if available
        const formData = sessionStorage.getItem('current_form_data');
        if (formData) {
            try {
                requestBody.form_context = JSON.parse(formData);
                requestBody.form_type = sessionStorage.getItem('current_form_type') || 'import_lc';
            } catch (e) {
                console.log('Could not parse form data:', e);
            }
        }
        
        // Add repository context if available - backend expects 'repository_context' field
        if (repositoryContext) {
            // Backend expects full repository name with "Repository" suffix
            let repoName = repositoryContext.repository_name || '';
            
            // Add "Repository" suffix if not already present
            if (repoName && !repoName.includes('Repository')) {
                repoName = repoName + ' Repository';
            }
            
            // If no name, map from ID
            if (!repoName && repositoryContext.repository_id) {
                const repoMap = {
                    'trade_finance': 'Trade Finance Repository',
                    'treasury': 'Treasury Repository',
                    'cash_management': 'Cash Management Repository'
                };
                repoName = repoMap[repositoryContext.repository_id] || repositoryContext.repository_id;
            }
            
            requestBody.repository_context = repoName;
            
            // Also include full repository object for future use
            requestBody.repository = repositoryContext;
            
            console.log('Sending repository_context:', repoName);
        }
        
        const response = await fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody),
            credentials: 'include'
        });

        const data = await response.json();
        
        // Log the response for debugging
        console.log('Query response:', data);
        
        // Handle error responses
        if (!response.ok) {
            hideTypingIndicator();
            
            // Handle specific error cases
            if (response.status === 400 && (data.intent === 'Train User Manual' || data.intent === 'User Manual Request' || data.intent === 'User Manual')) {
                if (data.response && data.response.includes('No relevant information found')) {
                    addMessage('I couldn\'t find any information in your uploaded manuals. Please make sure you\'ve uploaded relevant manuals first, or try asking a different question.', 'assistant', false, null, false);
                    showNotification('No manuals found for this query', 'warning', 5000);
                    return;
                } else if (data.response && data.response.includes('Please upload a user manual')) {
                    addMessage(data.response, 'assistant', false, null, false);
                    return;
                }
            }
            
            // Generic error handling
            addMessage(data.response || 'An error occurred while processing your request.', 'assistant', false, null, false);
            return;
        }
        
        // Debug logging
        console.log('Response data:', {
            intent: data.intent,
            hasHtml: !!data.html,
            hasResponse: !!data.response,
            outputFormat: data.output_format,
            hasFollowUpQuestions: !!(data.follow_up_questions && data.follow_up_questions.length > 0),
            success: data.success
        });

        // Hide typing indicator
        hideTypingIndicator();

        // Handle follow-up questions if present
        if (data.follow_up_questions && data.follow_up_questions.length > 0 && !data.response) {
            // Create a formatted response with follow-up questions
            const followUpHtml = createFollowUpQuestionsHtml(data.follow_up_questions, data.intent);
            addMessage(followUpHtml, 'assistant', true, 'follow-up');
            storeMessage(followUpHtml, 'assistant', true);
        } else {
            // Check if this is a transaction confirmation with form data ready for population
            if (data.intent === 'Creation Transaction' && data.form_data && !data.awaiting_form_population) {
                // User explicitly requested form population
                console.log('User requested form population:', data.form_data);
                populateTradeFinanceForm(data.form_data);
                
                // Show the response message
                addMessage(data.response || 'Form has been populated with the transaction data.', 'assistant', false, null, false);
                
                // Store the message
                storeMessage(data.response, 'assistant', true);
                
                // Notify parent window if in iframe
                if (window.parent !== window) {
                    window.parent.postMessage({
                        type: 'transaction_populated',
                        formData: data.form_data,
                        transactionType: data.transaction_type || 'import_lc'
                    }, '*');
                }
                
                return;
            }
            
            // Check if transaction is confirmed but awaiting population request
            if (data.intent === 'Creation Transaction' && data.awaiting_form_population) {
                // Just show the message asking if user wants to populate
                addMessage(data.response, 'assistant', false, null, false);
                storeMessage(data.response, 'assistant', true);
                return;
            }
            
            // Add assistant response
            // Check if response contains HTML (like RAG responses)
            let responseContent = data.html || data.response || 'No response generated';
            
            // For Follow-Up Request, check if the response itself is an object
            if (data.intent === 'Follow-Up Request' && typeof responseContent === 'object') {
                responseContent = responseContent.response || JSON.stringify(responseContent);
            }
            
            // Detect HTML content
            let isHtmlResponse = !!(data.html || 
                                     data.output_format === 'html' || 
                                     data.output_format === 'table' ||
                                     (typeof responseContent === 'string' && 
                                      (responseContent.includes('<div') || 
                                       responseContent.includes('<table') || 
                                       responseContent.includes('<html') ||
                                       responseContent.includes('class="'))));

            // Determine message type based on intent and content
            let messageType = null;
            const htmlIntents = ['RAG Request', 'Train User Manual', 'User Manual Request', 'User Manual',
                               'Follow-Up Request', 'Table Request', 'report request', 'Report Request'];
            
            if (data.intent === 'RAG Request' || data.intent === 'Train User Manual' || 
                data.intent === 'User Manual Request' || data.intent === 'User Manual') {
                messageType = 'rag';
            } else if (data.intent === 'Table Request' || data.intent === 'report request' || 
                       data.intent === 'Report Request' || data.output_format === 'table' || 
                       (typeof responseContent === 'string' && responseContent.includes('enhanced-data-table'))) {
                messageType = 'table';
            } else if (data.intent === 'Follow-Up Request') {
                messageType = 'follow-up';
                // Follow-up requests always contain HTML
                isHtmlResponse = true;
            } else if (data.intent === 'Creation Transaction') {
                messageType = 'transaction';
                // Format transaction response with action buttons if present
                if (data.action_buttons) {
                    responseContent = formatTransactionResponse(responseContent, data);
                    isHtmlResponse = true;
                }
            } else if (data.follow_up_questions && data.follow_up_questions.length > 0) {
                messageType = 'follow-up';
            }

            // Force HTML rendering for specific intents
            if (htmlIntents.includes(data.intent)) {
                isHtmlResponse = true;
            }

            // Use typewriter effect only for plain text responses
            const useTypewriter = !isHtmlResponse && 
                                messageType !== 'table' && 
                                messageType !== 'rag' && 
                                messageType !== 'follow-up' &&
                                !htmlIntents.includes(data.intent);
                                
            // Ensure responseContent is a string
            if (typeof responseContent !== 'string') {
                console.warn('Response content is not a string:', responseContent);
                responseContent = JSON.stringify(responseContent);
            }
                                
            addMessage(responseContent, 'assistant', isHtmlResponse, messageType, useTypewriter);

            // Store assistant message locally
            storeMessage(responseContent, 'assistant', true);

            // Add follow-up questions if present with response
            if (data.follow_up_questions && data.follow_up_questions.length > 0 && data.response) {
                const followUpHtml = createFollowUpQuestionsHtml(data.follow_up_questions, data.intent);
                addMessage(followUpHtml, 'assistant', true, 'follow-up');
            }
            // Store complete conversation exchange on backend
            const finalResponseContent = data.html || data.response || 'No response generated';
            await storeConversationExchange(message, finalResponseContent);
        }

        // Update session title if it's the first message
        updateSessionTitle(message);
        
        // Save session to update lastUpdated timestamp
        saveSession();

    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        
        // More specific error messages
        let errorMessage = 'Sorry, I encountered an error. Please try again.';
        if (error.message) {
            if (error.message.includes('network')) {
                errorMessage = 'Network error. Please check your connection and try again.';
            } else if (error.message.includes('timeout')) {
                errorMessage = 'Request timed out. Please try again.';
            }
        }
        
        addMessage(errorMessage, 'assistant', false, null, false);
        showNotification('Error sending message', 'error');
    } finally {
        // Re-enable input
        messageInput.disabled = false;
        document.getElementById('send-btn').disabled = false;
        messageInput.focus();
    }
}

// Store message in conversation history
async function storeMessage(content, role, skipBackend = false) {
    // Store locally first
    storeMessageLocally(content, role);

    // For backend storage, we need to wait for both user message and assistant response
    // So we skip backend storage for now and handle it after getting the response
    if (skipBackend) {
        return;
    }
}

// Store complete conversation exchange (user message + assistant response)
async function storeConversationExchange(userMessage, assistantResponse) {
    try {
        const userId = localStorage.getItem('user_id');
        if (!userId) {
            console.warn('No user_id found, skipping backend storage');
            return;
        }

        const response = await fetch('/api/conversation/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: userMessage,
                response: assistantResponse,
                session_id: currentSessionId,
                message_type: 'chat',
                user_id: userId
            }),
            credentials: 'include'
        });

        if (!response.ok) {
            console.error('Failed to store conversation:', response.status, response.statusText);
            if (response.status === 401 || response.status === 404) {
                console.warn('Backend storage not available, using local storage only');
            }
        } else {
            console.log('Conversation stored successfully');
        }
    } catch (error) {
        console.error('Error storing conversation on backend:', error);
    }
}

// Store message locally
function storeMessageLocally(content, role) {
    const key = `chat_history_${currentSessionId}`;
    const history = JSON.parse(localStorage.getItem(key) || '[]');
    history.push({
        content: content,
        role: role,
        timestamp: new Date().toISOString(),
        session_id: currentSessionId
    });
    // Keep only last 100 messages per session
    if (history.length > 100) {
        history.splice(0, history.length - 100);
    }
    localStorage.setItem(key, JSON.stringify(history));
}

// Add message to chat with improved animations and grouping
function addMessage(content, role, isHtml = false, messageType = null, useTypewriter = false) {
    const messagesContainer = document.getElementById('messages-container');
    
    // Check if we should group with previous message
    const lastMessage = messagesContainer.lastElementChild;
    const shouldGroup = lastMessage && 
                       lastMessage.classList.contains(role) && 
                       !lastMessage.classList.contains('message-group-end');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    // Add animation classes
    messageDiv.classList.add('animate__animated', 'animate__fadeInUp');
    messageDiv.style.animationDuration = '0.3s';

    // Add grouping classes
    if (shouldGroup) {
        messageDiv.classList.add('message-grouped');
        lastMessage.classList.add('message-group-start');
    }

    // Add data-type attribute for styling
    if (messageType) {
        messageDiv.setAttribute('data-type', messageType);
    }

    // Improved avatar with better icons and animations
    const avatar = role === 'user' ?
        '<i class="fas fa-user-circle"></i>' :
        '<i class="fas fa-robot animate__animated animate__pulse animate__infinite"></i>';

    const roleName = role === 'user' ? 'You' : 'AI Assistant';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Check if content is wrapped in markdown code blocks
    let processedContent = content;
    const codeBlockRegex = /```html\s*([\s\S]*?)\s*```/;
    const codeBlockMatch = content.match(codeBlockRegex);
    if (codeBlockMatch) {
        // Extract HTML content from code block
        processedContent = codeBlockMatch[1].trim();
    }
    
    // Check if content contains HTML tags (RAG response or table)
    const hasHtmlContent = processedContent.includes('<div') || processedContent.includes('<table') || processedContent.includes('class="rag-response"');

    // Detect message type if not provided
    if (!messageType && role === 'assistant') {
        if (processedContent.includes('class="rag-response"')) {
            messageType = 'rag';
        } else if (processedContent.includes('<table') || processedContent.includes('enhanced-data-table')) {
            messageType = 'table';
        }
    }

    // Set data-type for CSS styling
    if (messageType) {
        messageDiv.setAttribute('data-type', messageType);
    }

    // Add message status indicator
    const statusIcon = role === 'user' ?
        '<i class="fas fa-check-circle message-status" title="Sent"></i>' :
        '<i class="fas fa-check-double message-status" title="Delivered"></i>';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <div class="message-role">${roleName}</div>
                <div class="message-meta">
                    <span class="message-time">${time}</span>
                    ${statusIcon}
                </div>
            </div>
            <div class="message-text" id="message-text-${Date.now()}"></div>
            <div class="message-actions">
                <button class="message-action-btn" onclick="copyMessage(this)" title="Copy">
                    <i class="fas fa-copy"></i>
                </button>
                ${role === 'assistant' ? `
                    <button class="message-action-btn" onclick="speakMessage(this)" title="Read aloud">
                        <i class="fas fa-volume-up"></i>
                    </button>
                    <button class="message-action-btn" onclick="regenerateMessage(this)" title="Regenerate">
                        <i class="fas fa-redo"></i>
                    </button>
                    <div class="download-actions">
                        <button class="message-action-btn" onclick="downloadAsExcel(this)" title="Download as Excel">
                            <i class="fas fa-file-excel"></i>
                        </button>
                        <button class="message-action-btn" onclick="downloadAsJSON(this)" title="Download as JSON">
                            <i class="fas fa-file-code"></i>
                        </button>
                        <button class="message-action-btn" onclick="downloadAsPDF(this)" title="Download as PDF">
                            <i class="fas fa-file-pdf"></i>
                        </button>
                    </div>
                ` : ''}
            </div>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);

    const messageTextDiv = messageDiv.querySelector('.message-text');

    // Apply typewriter effect for assistant messages if enabled and not HTML
    if (useTypewriter && role === 'assistant' && !hasHtmlContent && !isHtml) {
        // Remove pulse animation during typing
        messageDiv.querySelector('.fa-robot').classList.remove('animate__pulse', 'animate__infinite');
        typewriterEffect(messageTextDiv, processedContent, () => {
            // Add back pulse animation after typing
            messageDiv.querySelector('.fa-robot').classList.add('animate__pulse', 'animate__infinite');
        });
    } else {
        // Regular display for user messages or HTML content
        messageTextDiv.innerHTML = hasHtmlContent || isHtml ? processedContent : escapeHtml(processedContent);

        // Add event listeners for table action buttons if present
        if (hasHtmlContent || isHtml) {
            setupTableEventListeners(messageDiv);
        }
    }

    // Update empty state
    updateEmptyState();

    // Check and update input position
    checkInputPosition();

    // Smooth scroll with easing
    scrollToBottom(true);
}

// Enhanced typewriter effect with callback
function typewriterEffect(element, text, callback, speed = 10) {
    let index = 0;
    element.textContent = '';

    // Add cursor with better animation
    const cursor = document.createElement('span');
    cursor.className = 'typewriter-cursor';
    cursor.innerHTML = '▊';
    element.appendChild(cursor);

    function type() {
        if (index < text.length) {
            // Remove cursor temporarily
            if (element.contains(cursor)) {
                element.removeChild(cursor);
            }

            // Add next character
            element.textContent += text.charAt(index);

            // Re-add cursor
            element.appendChild(cursor);

            index++;

            // Scroll to bottom as text is being typed
            scrollToBottom(true);

            // Variable delay for more natural typing
            let delay = speed;
            // Shorter pause at punctuation
            if (['.', '!', '?'].includes(text.charAt(index - 1))) {
                delay += 50; // Reduced from 100
            } else if ([',', ';', ':'].includes(text.charAt(index - 1))) {
                delay += 25; // Shorter pause for commas
            }
            // Much faster for spaces
            if (text.charAt(index - 1) === ' ') {
                delay = Math.max(1, speed / 3);
            }

            setTimeout(type, delay + Math.random() * 10); // Reduced randomness
        } else {
            // Fade out cursor
            cursor.style.animation = 'cursorFadeOut 0.5s ease forwards';
            setTimeout(() => {
                if (element.contains(cursor)) {
                    element.removeChild(cursor);
                }
                if (callback) callback();
            }, 500);
        }
    }

    type();
}

// Setup event listeners for table action buttons
function setupTableEventListeners(messageDiv) {
    // Handle table action buttons
    const actionButtons = messageDiv.querySelectorAll('.table-action-btn');
    actionButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const btnText = this.textContent.trim();

            if (btnText.includes('Export to Excel') || btnText.includes('Excel')) {
                exportTableToExcel(messageDiv);
            } else if (btnText.includes('Export to PDF') || btnText.includes('PDF')) {
                exportTableToPDF(messageDiv);
            } else if (btnText.includes('Generate Report') || btnText.includes('Report')) {
                generateReport(messageDiv);
            }
        });
    });

    // Handle table search
    const searchInput = messageDiv.querySelector('.table-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterTable(messageDiv, this.value);
        });
    }

    // Handle table filter
    const filterSelect = messageDiv.querySelector('.table-filter');
    if (filterSelect) {
        filterSelect.addEventListener('change', function() {
            filterTableByStatus(messageDiv, this.value);
        });
    }
}

// Export table to Excel
function exportTableToExcel(messageDiv) {
    const table = messageDiv.querySelector('.enhanced-data-table');
    if (!table) return;

    let csv = [];

    // Add title and metadata
    const title = messageDiv.querySelector('.table-title')?.textContent || 'Data';
    csv.push(`"${title}"`);
    csv.push(`"Exported on: ${new Date().toLocaleString()}"`);
    csv.push(''); // Empty line

    // Get headers
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => `"${th.textContent.trim()}"`);
    csv.push(headers.join(','));

    // Get rows with better formatting
    table.querySelectorAll('tbody tr').forEach(row => {
        const rowData = Array.from(row.querySelectorAll('td')).map((td, index) => {
            // Handle status badges specially
            const badge = td.querySelector('.status-badge');
            if (badge) {
                return `"${badge.textContent.trim().toUpperCase()}"`;
            }

            // Handle currency cells - remove currency symbol for Excel
            if (td.classList.contains('currency-cell')) {
                const value = td.textContent.trim().replace(/[^0-9.,]/g, '');
                return value;
            }

            // Handle date cells
            if (td.classList.contains('date-cell')) {
                return `"${td.textContent.trim()}"`;
            }

            // Default formatting
            return `"${td.textContent.trim().replace(/"/g, '""')}"`;
        });
        csv.push(rowData.join(','));
    });

    // Add summary if exists
    const summary = messageDiv.querySelector('.insight-summary');
    if (summary) {
        csv.push(''); // Empty line
        csv.push('"SUMMARY"');
        summary.querySelectorAll('p').forEach(p => {
            csv.push(`"${p.textContent.trim().replace(/"/g, '""')}"`);
        });
    }

    // Add UTF-8 BOM for Excel compatibility
    const BOM = '\uFEFF';
    const csvContent = BOM + csv.join('\n');

    // Download CSV with proper encoding
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    showNotification('Table exported to Excel successfully', 'success');
}

// Export table to PDF
function exportTableToPDF(messageDiv) {
    const table = messageDiv.querySelector('.enhanced-data-table');
    if (!table) return;

    // Create a temporary canvas to capture the table
    html2canvas(table).then(canvas => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('l', 'mm', 'a4'); // landscape orientation

        const imgWidth = 280; // A4 width in landscape
        const imgHeight = (canvas.height * imgWidth) / canvas.width;

        pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, imgHeight);
        pdf.save(`trade_finance_data_${new Date().toISOString().split('T')[0]}.pdf`);

        showNotification('Table exported to PDF successfully', 'success');
    }).catch(() => {
        // Fallback method if html2canvas is not available
        const tableHtml = table.outerHTML;
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Trade Finance Data Export</title>
                    <style>
                        body { font-family: Arial, sans-serif; }
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        .status-badge {
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: bold;
                        }
                        .status-badge.expired { background: #fee2e2; color: #dc2626; }
                        .status-badge.active { background: #d1fae5; color: #059669; }
                        .status-badge.pending { background: #fef3c7; color: #d97706; }
                    </style>
                </head>
                <body>
                    <h2>Trade Finance Data Export</h2>
                    ${tableHtml}
                    <script>
                        window.onload = function() {
                            window.print();
                            window.close();
                        }
                    </script>
                </body>
            </html>
        `);
        printWindow.document.close();
    });
}

// Generate report
function generateReport(messageDiv) {
    const summary = messageDiv.querySelector('.insight-summary');
    if (summary) {
        const reportText = summary.innerText;
        const message = `Generate a detailed report based on the following data:\n\n${reportText}`;
        document.getElementById('message-input').value = message;
        document.getElementById('message-input').focus();
        showNotification('Report request added to message input', 'info');
    }
}

// Filter table by search term
function filterTable(messageDiv, searchTerm) {
    const table = messageDiv.querySelector('.enhanced-data-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');
    const term = searchTerm.toLowerCase();

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
    });
}

// Filter table by status
function filterTableByStatus(messageDiv, status) {
    const table = messageDiv.querySelector('.enhanced-data-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        if (!status) {
            row.style.display = '';
            return;
        }

        const statusBadge = row.querySelector('.status-badge');
        if (statusBadge) {
            const rowStatus = statusBadge.textContent.trim().toLowerCase();
            row.style.display = rowStatus === status.toLowerCase() ? '' : 'none';
        }
    });
}

// Add welcome message
function addWelcomeMessage() {
    const messagesContainer = document.getElementById('messages-container');
    messagesContainer.innerHTML = `
        <div class="message assistant">
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-role">AI Assistant</div>
                <div class="message-text">Hello! I'm your AI assistant for trade finance. I can help you with document analysis, compliance checking, transaction processing, and answer questions about your uploaded manuals. How can I assist you today?</div>
                <div class="message-time">Just now</div>
            </div>
        </div>
    `;
}

// Clear messages
function clearMessages() {
    document.getElementById('messages-container').innerHTML = '';
}

// Check and update input position
function checkInputPosition() {
    const messagesContainer = document.getElementById('messages-container');
    const inputArea = document.querySelector('.input-area');

    if (!messagesContainer || !inputArea) return;

    // Check if there are any user messages
    const userMessages = messagesContainer.querySelectorAll('.message.user');

    if (userMessages.length === 0) {
        // No user messages, center the input
        inputArea.classList.add('centered');
        // Hide empty state when input is centered
        const emptyState = document.getElementById('empty-state');
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        // Hide welcome message when input is centered
        const welcomeMessage = messagesContainer.querySelector('.message.assistant');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
    } else {
        // Has messages, move input to bottom
        inputArea.classList.remove('centered');
        // Show empty state if needed
        const emptyState = document.getElementById('empty-state');
        if (emptyState) {
            emptyState.style.display = '';
        }
        // Show welcome message again
        const welcomeMessage = messagesContainer.querySelector('.message.assistant');
        if (welcomeMessage) {
            welcomeMessage.style.display = '';
        }
    }
}

// Clear current chat
function clearCurrentChat() {
    if (confirm('Are you sure you want to clear this chat?')) {
        clearMessages();
        addWelcomeMessage();
    }
}

// Enhanced typing indicator with better animations
function showTypingIndicator() {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Messages container not found');
        return;
    }

    const existingIndicator = document.getElementById('typing-indicator-message');

    if (existingIndicator) {
        existingIndicator.remove();
    }

    const indicatorDiv = document.createElement('div');
    indicatorDiv.id = 'typing-indicator-message';
    indicatorDiv.className = 'message assistant animate__animated animate__fadeIn';
    indicatorDiv.style.animationDuration = '0.3s';

    // Array of thinking messages for variety
    const thinkingMessages = [
        'Thinking',
        'Processing',
        'Analyzing',
        'Understanding',
        'Formulating response'
    ];
    const randomMessage = thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];

    indicatorDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot animate__animated animate__pulse animate__infinite"></i>
        </div>
        <div class="message-content">
            <div class="message-role">AI Assistant</div>
            <div class="loading-animation">
                <span class="thinking-text">${randomMessage}</span>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
        </div>
    `;

    messagesContainer.appendChild(indicatorDiv);
    scrollToBottom(true);

    // Update empty state
    updateEmptyState();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator-message');
    if (indicator) {
        indicator.remove();
    }
}

// Smooth scroll to bottom with easing
function scrollToBottom(smooth = false) {
    const messagesContainer = document.getElementById('messages-container');
    if (smooth) {
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    } else {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Update chat title
function updateChatTitle(title) {
    const chatTitleElement = document.getElementById('chat-title');
    if (chatTitleElement) {
        chatTitleElement.textContent = title;
    } else {
        console.warn('Chat title element not found');
    }
}

// Update session title
function updateSessionTitle(firstMessage) {
    if (!sessionStorage.getItem(`title_${currentSessionId}`)) {
        const title = firstMessage.substring(0, 30) + '...';
        sessionStorage.setItem(`title_${currentSessionId}`, title);
        updateChatTitle(title);
    }
}

// Save session
function saveSession() {
    const sessions = JSON.parse(localStorage.getItem('chatSessions') || '{}');
    const existingSession = sessions[currentSessionId];

    // Get the first user message as title or use default
    const messages = document.querySelectorAll('.message.user');
    let title = 'New Chat';
    if (messages.length > 0) {
        const firstMessage = messages[0].querySelector('.message-text')?.textContent;
        if (firstMessage) {
            title = firstMessage.substring(0, 50) + (firstMessage.length > 50 ? '...' : '');
        }
    }

    sessions[currentSessionId] = {
        id: currentSessionId,
        title: title,
        created: existingSession?.created || new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
        messageCount: document.querySelectorAll('.message').length
    };
    localStorage.setItem('chatSessions', JSON.stringify(sessions));

    // Notify session manager to refresh
    if (window.sessionManager) {
        window.sessionManager.loadSessions();
    }
}

// Export chat
function exportChat() {
    const messages = document.querySelectorAll('.message');
    let chatText = 'AI Assistant Chat Export\n';
    chatText += '========================\n\n';

    messages.forEach(message => {
        const role = message.querySelector('.message-role').textContent;
        const text = message.querySelector('.message-text').textContent;
        const time = message.querySelector('.message-time').textContent;

        chatText += `${role} (${time}):\n${text}\n\n`;
    });

    const blob = new Blob([chatText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// File upload functions
function openUploadModal() {
    // Check if user is admin
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    if (userInfo.isAdmin !== true) {
        showNotification('Only administrators can upload manuals', 'error');
        return;
    }
    
    document.getElementById('upload-modal').style.display = 'flex';
}

function closeUploadModal() {
    document.getElementById('upload-modal').style.display = 'none';
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('selected-file-info').innerHTML = '';
    document.getElementById('upload-btn').disabled = true;
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        displaySelectedFile(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');

    const file = event.dataTransfer.files[0];
    if (file) {
        selectedFile = file;
        displaySelectedFile(file);
    }
}

function displaySelectedFile(file) {
    const fileInfo = document.getElementById('selected-file-info');
    fileInfo.innerHTML = `
        <div class="selected-file">
            <div class="file-info">
                <i class="fas fa-file"></i>
                <span>${file.name}</span>
            </div>
            <span>${formatFileSize(file.size)}</span>
        </div>
    `;
    document.getElementById('upload-btn').disabled = false;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function uploadManual() {
    console.log('uploadManual called, selectedFile:', selectedFile);
    
    // Check if user is admin
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    if (userInfo.isAdmin !== true) {
        showNotification('Only administrators can upload manuals', 'error');
        closeUploadModal();
        return;
    }
    
    if (!selectedFile) {
        console.error('No file selected');
        showNotification('Please select a file first', 'error');
        return;
    }

    const uploadBtn = document.getElementById('upload-btn');
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="loading"></span>';

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('query', 'train user manual');
    formData.append('user_id', localStorage.getItem('user_id'));
    
    console.log('Uploading file:', selectedFile.name, 'Size:', selectedFile.size);

    try {
        const response = await fetch('/api/trainuser-manuals', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const data = await response.json();
        console.log('Upload response:', data);

        if (data.success || response.ok) {
            showNotification('Manual uploaded successfully!', 'success');
            closeUploadModal();
            loadUserManuals();
            selectedFile = null; // Reset selected file after successful upload
        } else {
            console.error('Upload failed:', data);
            showNotification(data.response || 'Failed to upload manual', 'error');
        }
    } catch (error) {
        console.error('Error uploading manual:', error);
        showNotification('Error uploading manual', 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = 'Upload';
    }
}

// Attach file to message
function attachFile() {
    // Create file input for message attachment
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.docx,.txt,.jpg,.jpeg,.png';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (file) {
            // Handle file attachment for message
            const messageInput = document.getElementById('message-input');
            messageInput.value += `[Attached: ${file.name}]`;
            messageInput.focus();
        }
    };
    input.click();
}

// Enhanced notification system
function showNotification(message, type = 'info', duration = 3000) {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 12px;
            pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'notification animate__animated animate__fadeInRight';
    notification.style.cssText = `
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 300px;
        pointer-events: auto;
        cursor: pointer;
        transition: all 0.3s ease;
    `;

    // Add icon based on type
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    notification.innerHTML = `
        <i class="fas ${icons[type] || icons.info}" style="font-size: 20px;"></i>
        <span style="flex: 1;">${message}</span>
        <i class="fas fa-times" style="opacity: 0.7; cursor: pointer;" onclick="this.parentElement.remove()"></i>
    `;

    // Add hover effect
    notification.onmouseenter = () => {
        notification.style.transform = 'translateX(-10px)';
        notification.style.boxShadow = '0 6px 30px rgba(0, 0, 0, 0.3)';
    };
    notification.onmouseleave = () => {
        notification.style.transform = 'translateX(0)';
        notification.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.2)';
    };

    container.appendChild(notification);

    // Auto remove after duration
    setTimeout(() => {
        notification.classList.remove('animate__fadeInRight');
        notification.classList.add('animate__fadeOutRight');
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add enhanced CSS animations and UI improvements
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    @keyframes cursorFadeOut {
        to {
            opacity: 0;
            transform: scale(0.8);
        }
    }

    /* Message grouping styles */
    .message-grouped {
        margin-top: 4px !important;
    }

    .message-grouped .message-avatar {
        opacity: 0;
    }

    .message-grouped .message-role {
        display: none;
    }

    /* Message actions hover effect */
    .message-actions {
        display: flex;
        gap: 8px;
        opacity: 0;
        transition: opacity 0.2s ease;
        margin-top: 8px;
        flex-wrap: wrap;
        align-items: center;
    }

    .message:hover .message-actions {
        opacity: 1;
    }

    .download-actions {
        display: flex;
        gap: 8px;
        margin-left: 8px;
        padding-left: 8px;
        border-left: 1px solid var(--border-color);
    }

    .message-action-btn {
        background: none;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 12px;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    .message-action-btn:hover {
        background: var(--hover-bg);
        color: var(--text-primary);
        transform: translateY(-1px);
    }

    .message-action-btn i {
        font-size: 14px;
    }

    /* Color coding for download buttons */
    .message-action-btn:has(.fa-file-excel):hover {
        background: #217346;
        color: white;
        border-color: #217346;
    }

    .message-action-btn:has(.fa-file-code):hover {
        background: #007acc;
        color: white;
        border-color: #007acc;
    }

    .message-action-btn:has(.fa-file-pdf):hover {
        background: #dc3545;
        color: white;
        border-color: #dc3545;
    }

    /* Message header improvements */
    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .message-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: var(--text-secondary);
    }

    .message-status {
        font-size: 12px;
        color: var(--accent-color);
    }

    /* Enhanced loading animation */
    .thinking-text {
        color: var(--text-secondary);
        font-size: 14px;
        font-weight: 500;
    }

    /* Character counter */
    .character-counter {
        position: absolute;
        bottom: -20px;
        right: 0;
        font-size: 11px;
        color: var(--text-secondary);
        transition: color 0.2s ease;
    }

    .character-counter.warning {
        color: #f59e0b;
    }

    .character-counter.danger {
        color: #ef4444;
    }

    /* Better focus states */
    .message-input:focus {
        outline: none;
    }

    .input-wrapper:focus-within {
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15),
                    0 4px 20px rgba(102, 126, 234, 0.1) !important;
    }

    /* Smooth theme transitions */
    body, .app-container, .sidebar, .main-content,
    .message, .message-content, .input-wrapper {
        transition: background-color 0.3s ease,
                    color 0.3s ease,
                    border-color 0.3s ease,
                    box-shadow 0.3s ease;
    }

    /* Follow-up Questions Styling */
    .follow-up-container {
        background: var(--secondary-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px;
        margin-top: 8px;
    }

    .follow-up-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 8px;
    }

    .follow-up-header i {
        color: var(--accent-color);
    }

    .follow-up-intro {
        font-size: 14px;
        color: var(--text-secondary);
        margin-bottom: 12px;
    }

    .follow-up-questions {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .follow-up-question {
        padding: 10px 16px;
        background: var(--hover-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 14px;
        color: var(--text-primary);
    }

    .follow-up-question:hover {
        background: var(--primary-bg);
        border-color: var(--accent-color);
        transform: translateX(4px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    /* Enhanced RAG Response Styling */
    .rag-response {
        position: relative;
    }

    .source-info {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 12px;
        padding: 8px 12px;
        background: var(--hover-bg);
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }

    .source-info i {
        color: var(--accent-color);
    }

    /* Better mobile touch targets */
    @media (max-width: 768px) {
        .message-action-btn,
        .action-btn,
        .attach-btn,
        .voice-btn,
        .send-btn {
            min-width: 44px;
            min-height: 44px;
        }

        .follow-up-question {
            padding: 12px 16px;
            font-size: 15px;
        }
    }
`;
document.head.appendChild(style);

// Session management functions
function refreshSessions() {
    if (window.sessionManager) {
        window.sessionManager.loadSessions();
    }
}

function deleteAllSessions() {
    if (window.sessionManager) {
        window.sessionManager.deleteAllSessions();
    }
}

function displaySessionMessages(messages) {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Messages container not found');
        return;
    }

    messagesContainer.innerHTML = '';

    messages.forEach(msg => {
        // The API returns 'content' field, but older messages might have 'message' field
        const messageText = String(msg.content || msg.message || '');
        // Check if this is an HTML message (RAG response)
        const isHtml = messageText.includes('<div') || messageText.includes('<table') || messageText.includes('class="rag-response"');
        // Don't use typewriter effect when loading existing messages
        addMessage(messageText, msg.role, isHtml, null, false);
    });

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Voice Recording Functionality
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recognition = null;

// Initialize Speech Recognition
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = function(event) {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            const messageInput = document.getElementById('message-input');
            if (finalTranscript) {
                messageInput.value += finalTranscript;
            } else {
                // Show interim results
                const currentValue = messageInput.value;
                const lastSpace = currentValue.lastIndexOf(' ');
                messageInput.value = currentValue.substring(0, lastSpace + 1) + interimTranscript;
            }

            updateSendButtonState();
            autoResizeTextarea();
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            stopVoiceRecording();
        };
    }
}

// Toggle Voice Recording
function toggleVoiceRecording() {
    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

// Start Voice Recording
function startVoiceRecording() {
    const voiceBtn = document.getElementById('voice-btn');

    // Initialize speech recognition if not already done
    if (!recognition) {
        initializeSpeechRecognition();
    }

    if (recognition) {
        try {
            recognition.start();
            isRecording = true;
            voiceBtn.classList.add('recording');
            voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
        } catch (error) {
            console.error('Error starting speech recognition:', error);
        }
    } else {
        alert('Speech recognition is not supported in your browser.');
    }
}

// Stop Voice Recording
function stopVoiceRecording() {
    const voiceBtn = document.getElementById('voice-btn');

    if (recognition && isRecording) {
        recognition.stop();
        isRecording = false;
        voiceBtn.classList.remove('recording');
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
}

// Speech Synthesis
let currentUtterance = null;
let isSpeaking = false;

// Speak text using Web Speech API
function speakText(text) {
    if ('speechSynthesis' in window) {
        // Stop any ongoing speech
        stopSpeaking();

        // Remove HTML tags and clean text
        const cleanText = text.replace(/<[^>]*>/g, '').trim();

        currentUtterance = new SpeechSynthesisUtterance(cleanText);
        currentUtterance.rate = 1.0;
        currentUtterance.pitch = 1.0;
        currentUtterance.volume = 1.0;

        // Show speaking indicator
        const speakingIndicator = document.getElementById('speaking-indicator');
        speakingIndicator.classList.add('active');
        isSpeaking = true;

        currentUtterance.onend = function() {
            speakingIndicator.classList.remove('active');
            isSpeaking = false;
        };

        currentUtterance.onerror = function(event) {
            console.error('Speech synthesis error:', event);
            speakingIndicator.classList.remove('active');
            isSpeaking = false;
        };

        window.speechSynthesis.speak(currentUtterance);
    }
}

// Stop Speaking
function stopSpeaking() {
    if ('speechSynthesis' in window && isSpeaking) {
        window.speechSynthesis.cancel();
        const speakingIndicator = document.getElementById('speaking-indicator');
        speakingIndicator.classList.remove('active');
        isSpeaking = false;
    }
}

// Send Suggestion
function sendSuggestion(text) {
    const messageInput = document.getElementById('message-input');
    // Decode HTML entities if present
    const decodedText = text.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&');
    messageInput.value = decodedText;
    updateSendButtonState();
    messageInput.focus();
    sendMessage();
}

// Enhanced send button state with animation
function updateSendButtonState() {
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const hasContent = messageInput.value.trim().length > 0;

    if (hasContent && !sendBtn.classList.contains('active')) {
        sendBtn.classList.add('active', 'animate__animated', 'animate__bounceIn');
        sendBtn.style.animationDuration = '0.3s';
        setTimeout(() => {
            sendBtn.classList.remove('animate__animated', 'animate__bounceIn');
        }, 300);
    } else if (!hasContent && sendBtn.classList.contains('active')) {
        sendBtn.classList.add('animate__animated', 'animate__bounceOut');
        sendBtn.style.animationDuration = '0.3s';
        setTimeout(() => {
            sendBtn.classList.remove('active', 'animate__animated', 'animate__bounceOut');
        }, 300);
    }

    // Update placeholder based on content
    if (hasContent) {
        messageInput.placeholder = 'Press Enter to send...';
    } else {
        messageInput.placeholder = 'Message AI Assistant...';
    }
}

// Update empty state visibility
function updateEmptyState() {
    const messagesContainer = document.getElementById('messages-container');
    const emptyState = document.getElementById('empty-state');

    if (messagesContainer && emptyState) {
        if (messagesContainer.children.length === 0) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }
    }
}

// Download message content as Excel
function downloadAsExcel(button) {
    const messageDiv = button.closest('.message');
    const messageText = messageDiv.querySelector('.message-text');
    const content = extractContentForDownload(messageText);

    // Convert to CSV format for Excel
    let csvContent = '';

    // If content has tables, convert to CSV
    const tables = messageText.querySelectorAll('table');
    if (tables.length > 0) {
        tables.forEach((table, index) => {
            if (index > 0) csvContent += '\n\n';

            // Process headers
            const headers = table.querySelectorAll('thead th');
            if (headers.length > 0) {
                csvContent += Array.from(headers).map(th => `"${th.textContent.trim()}"`).join(',') + '\n';
            }

            // Process rows
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                csvContent += Array.from(cells).map(td => `"${td.textContent.trim()}"`).join(',') + '\n';
            });
        });
    } else {
        // Plain text content
        csvContent = content.text;
    }

    downloadFile(csvContent, 'chat-export.csv', 'text/csv');
    showNotification('Downloaded as CSV', 'success');
}

// Download message content as JSON
function downloadAsJSON(button) {
    const messageDiv = button.closest('.message');
    const messageText = messageDiv.querySelector('.message-text');
    const content = extractContentForDownload(messageText);

    const jsonData = {
        timestamp: new Date().toISOString(),
        role: messageDiv.classList.contains('user') ? 'user' : 'assistant',
        content: content.text,
        html: content.html,
        tables: content.tables
    };

    downloadFile(JSON.stringify(jsonData, null, 2), 'chat-export.json', 'application/json');
    showNotification('Downloaded as JSON', 'success');
}

// Download message content as PDF
async function downloadAsPDF(button) {
    const messageDiv = button.closest('.message');
    const messageText = messageDiv.querySelector('.message-text');

    try {
        // Create a form data object
        const formData = new FormData();
        formData.append('content', messageText.innerHTML);
        formData.append('type', 'chat_message');

        const response = await fetch('/api/export/pdf', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'chat-export.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showNotification('Downloaded as PDF', 'success');
        } else {
            // Fallback: Simple PDF generation using browser print
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>Chat Export</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                    </style>
                </head>
                <body>
                    ${messageText.innerHTML}
                </body>
                </html>
            `);
            printWindow.document.close();
            printWindow.print();
            showNotification('Use print dialog to save as PDF', 'info');
        }
    } catch (error) {
        console.error('Error downloading PDF:', error);
        showNotification('Error downloading PDF', 'error');
    }
}

// Extract content from message for download
function extractContentForDownload(messageText) {
    const tables = [];
    const tableElements = messageText.querySelectorAll('table');

    tableElements.forEach(table => {
        const tableData = [];
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        if (headers.length > 0) {
            tableData.push(headers);
        }

        table.querySelectorAll('tbody tr').forEach(row => {
            const rowData = Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim());
            tableData.push(rowData);
        });

        tables.push(tableData);
    });

    return {
        text: messageText.textContent.trim(),
        html: messageText.innerHTML,
        tables: tables
    };
}

// Download file utility
function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Override addMessage to include speech synthesis option
const originalAddMessage = addMessage;
addMessage = function(content, role, isHtml = false, messageType = null, useTypewriter = false) {
    originalAddMessage(content, role, isHtml, messageType, useTypewriter);

    // Update empty state
    updateEmptyState();

    // Auto-speak AI responses if enabled
    if (role === 'assistant' && localStorage.getItem('autoSpeak') === 'true') {
        speakText(content);
    }
};

// Add event listener for message input
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('input', updateSendButtonState);
        messageInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });

        // Add focus/blur animations
        messageInput.addEventListener('focus', function() {
            this.closest('.input-wrapper').classList.add('focused');
        });

        messageInput.addEventListener('blur', function() {
            this.closest('.input-wrapper').classList.remove('focused');
        });
    }

    // Initialize speech recognition
    initializeSpeechRecognition();

    // Update empty state on load
    updateEmptyState();

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            messageInput?.focus();
        }

        // Ctrl/Cmd + / to toggle theme
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            toggleTheme();
        }

        // Escape to clear input
        if (e.key === 'Escape' && document.activeElement === messageInput) {
            messageInput.value = '';
            updateSendButtonState();
        }
    });

    // Add character counter
    addCharacterCounter();
});

// Create HTML for follow-up questions
function createFollowUpQuestionsHtml(questions, intent) {
    const questionsList = questions.map(q =>
        `<li class="follow-up-question" onclick="sendSuggestion('${q.replace(/'/g, "\\'")}')">${q}</li>`
    ).join('');

    return `
        <div class="follow-up-container">
            <div class="follow-up-header">
                <i class="fas fa-question-circle"></i>
                <span>Follow-up Questions</span>
            </div>
            <p class="follow-up-intro">Please select one of the following options or type your own response:</p>
            <ul class="follow-up-questions">
                ${questionsList}
            </ul>
        </div>
    `;
}

// Add new UI helper functions
function copyMessage(button) {
    const messageText = button.closest('.message-content').querySelector('.message-text').textContent;
    navigator.clipboard.writeText(messageText).then(() => {
        showNotification('Message copied to clipboard', 'success');

        // Animate button
        button.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => {
            button.innerHTML = '<i class="fas fa-copy"></i>';
        }, 2000);
    });
}

function speakMessage(button) {
    const messageText = button.closest('.message-content').querySelector('.message-text').textContent;
    speakText(messageText);
}

function regenerateMessage(button) {
    const messageDiv = button.closest('.message');
    const previousMessage = messageDiv.previousElementSibling;

    if (previousMessage && previousMessage.classList.contains('user')) {
        const userText = previousMessage.querySelector('.message-text').textContent;

        // Remove the current assistant message
        messageDiv.remove();

        // Resend the user's message
        const messageInput = document.getElementById('message-input');
        messageInput.value = userText;
        sendMessage();
    }
}

function addCharacterCounter() {
    const inputContainer = document.querySelector('.input-container');
    if (inputContainer && !document.getElementById('character-counter')) {
        const counter = document.createElement('div');
        counter.id = 'character-counter';
        counter.className = 'character-counter';
        inputContainer.appendChild(counter);
        updateCharacterCounter();
    }
}

function updateCharacterCounter() {
    const messageInput = document.getElementById('message-input');
    const counter = document.getElementById('character-counter');
    if (messageInput && counter) {
        const length = messageInput.value.length;
        const maxLength = 4000;

        counter.textContent = `${length}/${maxLength}`;

        // Update color based on length
        counter.classList.remove('warning', 'danger');
        if (length > maxLength * 0.8) {
            counter.classList.add('warning');
        }
        if (length > maxLength * 0.95) {
            counter.classList.add('danger');
        }

        // Show/hide based on content
        counter.style.opacity = length > 0 ? '1' : '0';
    }
}

// Export functions for global access
window.toggleVoiceRecording = toggleVoiceRecording;
window.stopSpeaking = stopSpeaking;
window.sendSuggestion = sendSuggestion;
window.copyMessage = copyMessage;
window.speakMessage = speakMessage;
window.regenerateMessage = regenerateMessage;
window.deleteManual = deleteManual;
window.openUploadModal = openUploadModal;
window.closeUploadModal = closeUploadModal;
window.uploadManual = uploadManual;
window.startNewChat = startNewChat;
window.toggleSidebar = toggleSidebar;
window.toggleTheme = toggleTheme;
window.clearCurrentChat = clearCurrentChat;
window.exportChat = exportChat;
window.refreshSessions = refreshSessions;
window.deleteAllSessions = deleteAllSessions;

// Function to format transaction response with action buttons
function formatTransactionResponse(content, data) {
    // Convert markdown to HTML if needed
    if (typeof content === 'string' && !content.includes('<')) {
        // Simple markdown to HTML conversion
        content = content
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>')
            .replace(/• /g, '• ');
    }
    
    let html = `<div class="transaction-response">`;
    html += `<div class="transaction-content">${content}</div>`;
    
    // Add action buttons if present
    if (data.action_buttons && data.action_buttons.length > 0) {
        html += `<div class="transaction-actions" style="margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap;">`;
        data.action_buttons.forEach(button => {
            const icon = getButtonIcon(button.action);
            const btnClass = getButtonClass(button.action);
            const dataStr = JSON.stringify(button.data || {}).replace(/"/g, '&quot;');
            html += `
                <button class="transaction-btn ${btnClass}" 
                        style="padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: 500; display: inline-flex; align-items: center; gap: 6px; background: ${getBtnBackground(btnClass)}; color: white;"
                        onclick="handleTransactionAction('${button.action}', '${dataStr}')">
                    ${icon} ${button.label}
                </button>
            `;
        });
        html += `</div>`;
    }
    
    html += `</div>`;
    return html;
}

// Get icon for transaction action button
function getButtonIcon(action) {
    const icons = {
        'confirm_transaction': '<i class="fas fa-check"></i>',
        'cancel_transaction': '<i class="fas fa-times"></i>',
        'modify_transaction': '<i class="fas fa-edit"></i>',
        'new_transaction': '<i class="fas fa-plus"></i>',
        'view_status': '<i class="fas fa-eye"></i>',
        'download_confirmation': '<i class="fas fa-download"></i>'
    };
    return icons[action] || '<i class="fas fa-arrow-right"></i>';
}

// Get CSS class for transaction action button  
function getButtonClass(action) {
    if (action.includes('confirm') || action.includes('submit')) return 'btn-success';
    if (action.includes('cancel') || action.includes('delete')) return 'btn-danger';
    if (action.includes('modify') || action.includes('edit')) return 'btn-warning';
    return 'btn-primary';
}

// Get button background color
function getBtnBackground(btnClass) {
    const colors = {
        'btn-success': '#10b981',
        'btn-danger': '#ef4444', 
        'btn-warning': '#f59e0b',
        'btn-primary': '#6366f1'
    };
    return colors[btnClass] || colors['btn-primary'];
}

// Handle transaction action button clicks
async function handleTransactionAction(action, dataStr) {
    try {
        let data = {};
        try {
            data = JSON.parse(dataStr.replace(/&quot;/g, '"'));
        } catch (e) {
            console.warn('Could not parse action data:', e);
        }
        
        let message = '';
        
        switch(action) {
            case 'confirm_transaction':
                message = 'proceed and submit';
                break;
            case 'cancel_transaction':
                message = 'cancel transaction';
                break;
            case 'modify_transaction':
                message = 'modify transaction';
                break;
            case 'new_transaction':
                message = 'create new transaction';
                break;
            case 'view_status':
                message = `show status of transaction ${data.id || ''}`;
                break;
            case 'download_confirmation':
                message = `download confirmation for ${data.id || ''}`;
                break;
            case 'populate_form':
                // Handle form population
                handleFormPopulation(data);
                return; // Don't send a message, just populate the form
            case 'cancel_population':
                showNotification('Form population cancelled', 'info');
                return;
            default:
                message = action.replace(/_/g, ' ');
        }
        
        // Send the action as a message
        const inputField = document.getElementById('message-input');
        inputField.value = message;
        await sendMessage();
        
    } catch (error) {
        console.error('Error handling transaction action:', error);
        showNotification('Error processing action', 'error');
    }
}

// Repository Management Functions
// Using RepositoryManager from repository-manager.js
// Repository manager is already initialized and loaded in repository-manager.js

// Function to populate trade finance form with transaction data
function populateTradeFinanceForm(formData) {
    try {
        console.log('Populating form with data:', formData);
        
        // Check if we're in an iframe (embedded in a form page)
        if (window.parent !== window) {
            // Send message to parent window to populate form
            window.parent.postMessage({
                type: 'POPULATE_LC_FORM',
                data: formData,
                source: 'ai_chat'
            }, '*');
            showNotification('Form populated successfully!', 'success');
        } else {
            // If not in iframe, store data and show notification
            sessionStorage.setItem('pending_form_data', JSON.stringify(formData));
            showNotification('Transaction data ready. Navigate to the form to see populated fields.', 'info');
        }
    } catch (error) {
        console.error('Error populating form:', error);
        showNotification('Failed to populate form', 'error');
    }
}

// Function to handle form population (generic)
function handleFormPopulation(formData) {
    try {
        // Check if we're in an iframe (embedded in a form page)
        if (window.parent !== window) {
            // Send message to parent window to populate form
            window.parent.postMessage({
                type: 'POPULATE_FORM',
                data: formData,
                source: 'ai_chat'
            }, '*');
            showNotification('Form populated successfully!', 'success');
        } else {
            // If not in iframe, try to navigate to the form page with data
            const formType = formData.transaction_type || 'import_lc';
            const params = new URLSearchParams();
            params.append('populate', JSON.stringify(formData));
            
            // Determine the form URL based on transaction type
            let formUrl = '/trade_finance_lc_form';
            if (formType === 'bank_guarantee') {
                formUrl = '/trade_finance_guarantee_form';
            }
            
            // Navigate to form with data
            window.location.href = `${formUrl}?${params.toString()}`;
        }
    } catch (error) {
        console.error('Error populating form:', error);
        showNotification('Failed to populate form', 'error');
    }
}

// Add file attachment function and file handling functions to global scope
window.attachFile = attachFile;
window.handleTransactionAction = handleTransactionAction;
window.handleFormPopulation = handleFormPopulation;
window.handleFileSelect = handleFileSelect;
window.handleDragOver = handleDragOver;
window.handleDragLeave = handleDragLeave;
window.handleDrop = handleDrop;

// Expose selectedFile so it can be accessed from other scripts
Object.defineProperty(window, 'selectedFile', {
    get: function() { return selectedFile; },
    set: function(value) { selectedFile = value; }
});
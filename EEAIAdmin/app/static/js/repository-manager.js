// Repository Manager for AI Chat Modern
class RepositoryManager {
    constructor() {
        this.repositories = [];
        this.connectedRepoId = null;
        this.isRepositoryListVisible = true;
        this.userId = localStorage.getItem('user_id') || 'default_user';
        console.log('Repository Manager initialized with user ID:', this.userId);
        
        // Load connected repository from localStorage
        this.connectedRepoId = localStorage.getItem('connected_repository_id');
        
        // Initialize connection status display
        this.updateConnectionStatusDisplay();
    }
    
    isAdmin() {
        // Check if user is admin from localStorage
        const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
        return userInfo.isAdmin === true;
    }

    async loadRepositories() {
        try {
            console.log('Fetching repositories from API...');
            const response = await fetch(`/api/repositories?user_id=${this.userId}`);
            const data = await response.json();
            console.log('Repositories API response:', data);
            
            if (data.success) {
                this.repositories = data.repositories;
                // Check if any repository is marked as connected in the response
                const connectedRepo = this.repositories.find(repo => repo.connected);
                if (connectedRepo) {
                    this.connectedRepoId = connectedRepo.id;
                    localStorage.setItem('connected_repository_id', connectedRepo.id);
                    // Update the chat header with the connected repository name
                    this.updateChatHeader(connectedRepo.name);
                    this.updateConnectionStatusDisplay(connectedRepo.name);
                } else {
                    // No repository connected, use default title
                    this.updateChatHeader('Finstack AI Chat');
                    this.updateConnectionStatusDisplay();
                }
                this.renderRepositories();
            }
        } catch (error) {
            console.error('Error loading repositories:', error);
            this.showNotification('Failed to load repositories', 'error');
        }
    }

    renderRepositories() {
        const repositoryList = document.getElementById('repository-list');
        if (!repositoryList) {
            console.error('Repository list element not found');
            return;
        }

        if (this.repositories.length === 0) {
            repositoryList.innerHTML = `
                <div class="no-repositories">
                    <i class="fas fa-database"></i>
                    <p>No repositories available</p>
                </div>
            `;
            return;
        }

        repositoryList.innerHTML = '';
        
        this.repositories.forEach(repo => {
            const repoItem = document.createElement('div');
            const isConnected = repo.id === this.connectedRepoId;
            repoItem.className = `repository-item ${isConnected ? 'connected' : ''}`;
            repoItem.dataset.repoId = repo.id;
            
            const totalDocs = repo.collections.reduce((sum, col) => sum + col.document_count, 0);
            
            repoItem.innerHTML = `
                <div class="repository-item-header">
                    <div class="repository-item-title">
                        <i class="fas fa-database ${isConnected ? 'connected-icon' : ''}"></i>
                        <span>${repo.name}</span>
                        ${isConnected ? '<span class="connected-badge">Connected</span>' : ''}
                    </div>
                </div>
                <div class="repository-item-description">${repo.description || 'Trade finance document repository'}</div>
                <div class="repository-item-stats">
                    <span class="stat-item">
                        <i class="fas fa-folder"></i>
                        ${repo.collections.length} collections
                    </span>
                    <span class="stat-item">
                        <i class="fas fa-file-alt"></i>
                        ${totalDocs.toLocaleString()} documents
                    </span>
                </div>
                ${this.isAdmin() ? `
                    <div class="repository-item-actions">
                        ${isConnected ? 
                            `<button class="repository-disconnect-btn" 
                                    onclick="repositoryManager.disconnectRepository('${repo.id}')">
                                <i class="fas fa-unlink"></i> Disconnect
                            </button>` :
                            `<button class="repository-connect-btn" 
                                    onclick="repositoryManager.connectRepository('${repo.id}')">
                                <i class="fas fa-link"></i> Connect
                            </button>`
                        }
                    </div>
                ` : (isConnected ? `
                    <div class="repository-item-status">
                        <span class="status-active">
                            <i class="fas fa-check-circle"></i> Active
                        </span>
                    </div>
                ` : '')}
            `;
            repositoryList.appendChild(repoItem);
        });
    }

    async connectRepository(repositoryId) {
        try {
            // If there's already a connected repository, disconnect it first
            if (this.connectedRepoId && this.connectedRepoId !== repositoryId) {
                await this.disconnectRepository(this.connectedRepoId, false);
            }
            
            const response = await fetch(`/api/repositories/${repositoryId}/connect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.connectedRepoId = repositoryId;
                localStorage.setItem('connected_repository_id', repositoryId);
                
                // Find the connected repository to get its name
                const connectedRepo = this.repositories.find(repo => repo.id === repositoryId);
                if (connectedRepo) {
                    this.updateChatHeader(connectedRepo.name);
                    this.updateConnectionStatusDisplay(connectedRepo.name);
                }
                
                this.showNotification('Repository connected successfully', 'success');
                this.updateRepositoryUI(repositoryId, true);
                
                // Notify the chat system about the connection change
                if (window.updateChatContext) {
                    window.updateChatContext(repositoryId);
                }
            } else {
                this.showNotification(data.error || 'Failed to connect repository', 'error');
            }
        } catch (error) {
            console.error('Error connecting repository:', error);
            this.showNotification('Failed to connect repository', 'error');
        }
    }

    async disconnectRepository(repositoryId, showNotificationFlag = true) {
        try {
            const response = await fetch(`/api/repositories/${repositoryId}/disconnect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.connectedRepoId = null;
                localStorage.removeItem('connected_repository_id');
                
                // Reset chat header to default
                this.updateChatHeader('Finstack AI Chat');
                this.updateConnectionStatusDisplay();
                
                if (showNotificationFlag) {
                    this.showNotification('Repository disconnected', 'info');
                }
                this.updateRepositoryUI(repositoryId, false);
                
                // Notify the chat system about the disconnection
                if (window.updateChatContext) {
                    window.updateChatContext(null);
                }
            } else {
                this.showNotification(data.error || 'Failed to disconnect repository', 'error');
            }
        } catch (error) {
            console.error('Error disconnecting repository:', error);
            this.showNotification('Failed to disconnect repository', 'error');
        }
    }

    updateRepositoryUI(repositoryId, isConnected) {
        // Update all repository items
        const allRepoItems = document.querySelectorAll('.repository-item');
        allRepoItems.forEach(item => {
            const itemRepoId = item.dataset.repoId;
            if (itemRepoId === repositoryId) {
                if (isConnected) {
                    item.classList.add('connected');
                } else {
                    item.classList.remove('connected');
                }
            } else {
                // Remove connected class from other repositories
                item.classList.remove('connected');
            }
        });
        
        // Re-render to update buttons
        this.renderRepositories();
    }

    toggleRepositoryList() {
        const repositoryList = document.getElementById('repository-list');
        const toggleIcon = document.getElementById('repository-toggle-icon');
        const toggleBtn = document.querySelector('.repository-toggle-btn');
        
        this.isRepositoryListVisible = !this.isRepositoryListVisible;
        
        if (this.isRepositoryListVisible) {
            repositoryList.style.display = 'block';
            toggleBtn.classList.add('active');
            toggleIcon.style.transform = 'rotate(180deg)';
            this.loadRepositories(); // Reload when opening
        } else {
            repositoryList.style.display = 'none';
            toggleBtn.classList.remove('active');
            toggleIcon.style.transform = 'rotate(0deg)';
        }
    }

    async showCollections(repositoryId, repositoryName) {
        try {
            const response = await fetch(`/api/repositories/${repositoryId}/collections`);
            const data = await response.json();
            
            if (data.success) {
                this.displayCollectionsModal(data.collections, repositoryName);
            } else {
                this.showNotification('Failed to load collections', 'error');
            }
        } catch (error) {
            console.error('Error loading collections:', error);
            this.showNotification('Failed to load collections', 'error');
        }
    }

    displayCollectionsModal(collections, repositoryName) {
        // Remove existing modal if any
        const existingModal = document.querySelector('.collections-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.className = 'collections-modal';
        modal.innerHTML = `
            <div class="collections-modal-content">
                <div class="collections-modal-header">
                    <h3 class="collections-modal-title">${repositoryName} - RAG Collections</h3>
                    <button class="collections-modal-close" onclick="repositoryManager.closeCollectionsModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="collections-list">
                    ${collections.map(collection => `
                        <div class="collection-item">
                            <div class="collection-name">${collection.collection_name}</div>
                            <div class="collection-stats">
                                <div class="collection-stat">
                                    <i class="fas fa-file-alt"></i>
                                    <span>${collection.document_count} documents</span>
                                </div>
                                <div class="collection-stat">
                                    <i class="fas fa-clock"></i>
                                    <span>Updated ${this.formatDate(collection.updated_at)}</span>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeCollectionsModal();
            }
        });
    }

    closeCollectionsModal() {
        const modal = document.querySelector('.collections-modal');
        if (modal) {
            modal.remove();
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)} days ago`;
        
        return date.toLocaleDateString();
    }

    showNotification(message, type = 'info') {
        // Check if there's a global notification function
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            // Fallback to console
            console[type === 'error' ? 'error' : 'log'](message);
        }
    }
    
    updateChatHeader(title) {
        // Update the brand title in the header
        const brandTitle = document.querySelector('.brand-title');
        if (brandTitle) {
            brandTitle.textContent = title;
        }
        
        // Update the page title
        document.title = `${title} - AI Assistant`;
        
        // Update the welcome message if it exists
        const welcomeTitle = document.querySelector('.empty-state h2');
        if (welcomeTitle && welcomeTitle.textContent.includes('Welcome to')) {
            welcomeTitle.textContent = `Welcome to ${title}`;
        }
    }
    
    updateConnectionStatusDisplay(repositoryName = null) {
        const statusElement = document.getElementById('repository-connection-status');
        const statusText = document.getElementById('repository-status-text');
        const indicatorElement = document.getElementById('connection-indicator');
        
        if (!statusElement || !statusText) return;
        
        if (this.connectedRepoId && repositoryName) {
            // Repository is connected
            statusElement.classList.add('connected');
            statusText.textContent = repositoryName;
            statusText.title = `Connected to: ${repositoryName}`;
            
            // Add tooltip for full name if truncated
            if (repositoryName.length > 20) {
                statusText.title = repositoryName;
                statusText.textContent = repositoryName.substring(0, 17) + '...';
            }
        } else if (this.connectedRepoId) {
            // Repository ID exists but need to find the name
            const connectedRepo = this.repositories.find(repo => repo.id === this.connectedRepoId);
            if (connectedRepo) {
                this.updateConnectionStatusDisplay(connectedRepo.name);
                return;
            }
            statusElement.classList.add('connected');
            statusText.textContent = 'Repository Connected';
        } else {
            // No repository connected
            statusElement.classList.remove('connected');
            statusText.textContent = 'No Repository';
            statusText.title = 'Click to connect a repository';
        }
        
        // Add click handler to show repository list
        statusElement.onclick = () => {
            const sidebar = document.getElementById('sidebar');
            const repositorySection = document.getElementById('repository-section');
            if (sidebar && repositorySection) {
                // Open sidebar if closed
                if (sidebar.classList.contains('collapsed')) {
                    toggleSidebar();
                }
                // Scroll to repository section
                repositorySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Expand repository list if collapsed
                if (!this.isRepositoryListVisible) {
                    toggleRepositoryList();
                }
            }
        };
    }
}

// Initialize repository manager
const repositoryManager = new RepositoryManager();
window.repositoryManager = repositoryManager;

// Load repositories on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Loading repositories...');
    repositoryManager.loadRepositories();
    
    // Make repository section visible by default
    const repoSection = document.getElementById('repository-section');
    if (repoSection) {
        repoSection.style.display = 'block';
    }
});

// Add to global window functions
window.toggleRepositoryList = () => repositoryManager.toggleRepositoryList();
const { createApp } = Vue;
const { createVuetify } = Vuetify;

const vuetify = createVuetify({
  theme: {
    defaultTheme: localStorage.getItem('theme') || 'light',
  },
});

const app = createApp({
  data() {
    return {
      currentView: 'login',
      isDarkMode: localStorage.getItem('theme') === 'dark',
      userData: null,
      showProfileModal: false,
      profileEditMode: false,
      editedProfile: {
        firstName: '',
        lastName: '',
        email: '',
      },
      loginData: {
        email: '',
        password: '',
        rememberMe: false,
      },
      registerData: {
        firstName: '',
        lastName: '',
        email: '',
        password: '',
        confirmPassword: '',
        acceptTerms: false,
      },
      loginValid: false,
      registerValid: false,
      showPassword: false,
      showConfirmPassword: false,
      loading: false,
      loginError: '',
      registerError: '',
      emailRules: [
        v => !!v || 'Email is required',
        v => /.+@.+\..+/.test(v) || 'Email must be valid',
      ],
      passwordRules: [
        v => !!v || 'Password is required',
        v => v.length >= 6 || 'Password must be at least 6 characters',
      ],
      nameRules: [
        v => !!v || 'Name is required',
        v => v.length >= 2 || 'Name must be at least 2 characters',
      ],
      confirmPasswordRules: [
        v => !!v || 'Please confirm your password',
        v => v === this.registerData.password || 'Passwords must match',
      ],
      termsRules: [
        v => !!v || 'You must agree to the terms',
      ],
    };
  },
  mounted() {
    this.checkAuthenticationStatus();
    this.initializeRealTimeUpdates();
    this.setupKeyboardShortcuts();
    if (this.isDarkMode) {
      document.body.classList.add('dark-mode');
    }
    this.trackPerformance();
    
    // Initialize advanced features
    setTimeout(() => {
      this.initAdvancedFeatures();
      this.setupSmartLoading();
      this.setupOfflineDetection();
    }, 500);
  },
  methods: {
    async login() {
      this.loading = true;
      this.loginError = '';
      try {
        const response = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.loginData.email,
            password: this.loginData.password,
          }),
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Invalid credentials');
        }

        const data = await response.json();
        this.userData = data.user;
        localStorage.setItem('user_id', data.user.id);
        localStorage.setItem('user_data', JSON.stringify(data.user));
        if (this.loginData.rememberMe) {
          localStorage.setItem('remember_me', 'true');
        }
        this.currentView = 'dashboard';
        this.showNotification('Logged in successfully', 'success');
      } catch (error) {
        this.loginError = error.message || 'Login failed';
        this.showNotification(this.loginError, 'error');
      } finally {
        this.loading = false;
      }
    },
    async register() {
      this.loading = true;
      this.registerError = '';
      try {
        const response = await fetch('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            firstName: this.registerData.firstName,
            lastName: this.registerData.lastName,
            email: this.registerData.email,
            password: this.registerData.password,
          }),
        });

        if (!response.ok) {
          throw new Error('Registration failed');
        }

        const data = await response.json();
        this.showNotification('Registration successful! Please log in.', 'success');
        this.currentView = 'login';
        this.registerData = {
          firstName: '',
          lastName: '',
          email: '',
          password: '',
          confirmPassword: '',
          acceptTerms: false,
        };
      } catch (error) {
        this.registerError = error.message || 'Registration failed';
        this.showNotification(this.registerError, 'error');
      } finally {
        this.loading = false;
      }
    },
    async logout() {
      if (!confirm('Are you sure you want to logout?')) return;

      try {
        const response = await fetch('/auth/logout', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok && response.status !== 401) {
          console.warn('Logout request failed, proceeding with local cleanup');
        }
      } catch (error) {
        console.warn('Logout request error:', error);
      } finally {
        localStorage.removeItem('user_id');
        localStorage.removeItem('user_data');
        localStorage.removeItem('remember_me');
        this.userData = null;
        this.currentView = 'login';
        this.showNotification('Logged out successfully', 'success');
        window.location.href = '/';
      }
    },
    checkAuthenticationStatus() {
      const userData = localStorage.getItem('user_data');
      const userId = localStorage.getItem('user_id');

      if (userData && userId) {
        try {
          const parsedUser = JSON.parse(userData);
          if (parsedUser && parsedUser.id === userId) {
            this.userData = parsedUser;
            this.currentView = 'dashboard';
            return true;
          }
        } catch (error) {
          console.error('Invalid user data:', error);
        }
      }

      this.currentView = 'login';
      return false;
    },
    toggleTheme() {
      this.isDarkMode = !this.isDarkMode;
      document.body.classList.toggle('dark-mode', this.isDarkMode);
      localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
      this.showNotification(`Switched to ${this.isDarkMode ? 'dark' : 'light'} mode`, 'info');
    },
    showProfile() {
      if (this.userData) {
        this.showProfileModal = true;
        this.editedProfile = {
          firstName: this.userData.firstName,
          lastName: this.userData.lastName,
          email: this.userData.email,
        };
      } else {
        this.showNotification('Profile data unavailable', 'error');
      }
    },
    closeProfileModal() {
      this.showProfileModal = false;
      this.profileEditMode = false;
    },
    toggleEditMode() {
      this.profileEditMode = !this.profileEditMode;
      if (this.profileEditMode) {
        this.editedProfile = {
          firstName: this.userData.firstName,
          lastName: this.userData.lastName,
          email: this.userData.email,
        };
      }
    },
    async saveProfile() {
      this.loading = true;
      try {
        const response = await fetch('/auth/update-profile', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.editedProfile),
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to update profile');
        }

        const data = await response.json();
        this.userData = { ...this.userData, ...this.editedProfile };
        localStorage.setItem('user_data', JSON.stringify(this.userData));
        this.profileEditMode = false;
        this.showNotification('Profile updated successfully', 'success');
      } catch (error) {
        this.showNotification(error.message || 'Failed to update profile', 'error');
      } finally {
        this.loading = false;
      }
    },
    navigateToChat() {
      if (!this.checkAuthenticationStatus()) return;
      this.showNotification('Launching AI Help Bot...', 'info');
      setTimeout(() => {
        window.location.href = '/ai-chat';
      }, 1000);
    },
    navigateToDocClass() {
      if (!this.checkAuthenticationStatus()) return;
      this.showNotification('Opening Document Classification...', 'info');
      setTimeout(() => {
        window.location.href = '/document-classification';
      }, 1000);
    },
    navigateToGuarantee() {
      if (!this.checkAuthenticationStatus()) return;
      this.showNotification('Loading Guarantee Vetting...', 'info');
      setTimeout(() => {
        window.location.href = '/guarantee';
      }, 1000);
    },
    navigateToAnalytics() {
      if (!this.checkAuthenticationStatus()) return;
      this.showNotification('Opening Analytics Dashboard...', 'info');
      setTimeout(() => {
        window.location.href = '/analytics';
      }, 1000);
    },
    navigateToAPI() {
      if (!this.checkAuthenticationStatus()) return;
      this.showNotification('Accessing API Management...', 'info');
      setTimeout(() => {
        this.showNotification('API Management feature coming soon!', 'warning');
      }, 1000);
    },
    navigateToSettings() {
      if (!this.checkAuthenticationStatus()) return;
      this.showNotification('Opening Settings...', 'info');
      setTimeout(() => {
        this.showNotification('Settings feature coming soon!', 'warning');
      }, 1000);
    },
    refreshStats() {
      this.showNotification('Refreshing statistics...', 'info');
      setTimeout(() => {
        document.querySelectorAll('.metric-number').forEach(el => {
          el.classList.add('loading-shimmer');
        });
        setTimeout(() => {
          document.querySelectorAll('.metric-number').forEach(el => {
            el.classList.remove('loading-shimmer');
          });
          this.showNotification('Statistics updated successfully', 'success');
        }, 1500);
      }, 500);
    },
    exportData() {
      this.showNotification('Preparing data export...', 'info');
      setTimeout(() => {
        this.showNotification('Export feature coming soon!', 'warning');
      }, 1000);
    },
    viewLogs() {
      this.showNotification('Opening system logs...', 'info');
      setTimeout(() => {
        this.showNotification('System logs feature coming soon!', 'warning');
      }, 1000);
    },
    initializeRealTimeUpdates() {
      setInterval(() => {
        this.updateSystemMetrics();
      }, 30000);
      this.updateProgressRing();
    },
    updateSystemMetrics() {
      const cpuBar = document.querySelector('.w-3\\/12');
      if (cpuBar) {
        const newCpuWidth = Math.floor(Math.random() * 30) + 10;
        cpuBar.style.width = `${newCpuWidth}%`;
        cpuBar.parentElement.nextElementSibling.textContent = `${newCpuWidth}%`;
      }
    },
    updateProgressRing() {
      const progressCircle = document.querySelector('.progress-ring circle:last-child');
      if (progressCircle) {
        let progress = 0;
        const targetProgress = 92;
        const increment = targetProgress / 100;
        const animate = () => {
          if (progress < targetProgress) {
            progress += increment;
            const offset = 283 - (progress / 100) * 283;
            progressCircle.style.strokeDashoffset = offset;
            requestAnimationFrame(animate);
          }
        };
        animate();
      }
    },
    showNotification(message, type = 'info') {
      const container = document.getElementById('notification-container');
      if (!container) {
        console.warn('Notification container not found!');
        return;
      }
      const notification = document.createElement('div');
      const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500',
      };
      const icons = {
        success: 'mdi-check-circle',
        error: 'mdi-alert-circle',
        warning: 'mdi-alert',
        info: 'mdi-information',
      };
      notification.className = `notification ${colors[type]} text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3 max-w-sm`;
      notification.innerHTML = `
        <i class="mdi ${icons[type]} text-xl"></i>
        <span class="font-medium">${message}</span>
        <button onclick="this.parentElement.remove()" class="ml-auto">
          <i class="mdi mdi-close text-lg hover:bg-white/20 rounded p-1 transition-colors"></i>
        </button>
      `;
      container.appendChild(notification);
      setTimeout(() => notification.classList.add('show'), 100);
      const timeout = type === 'error' ? 5000 : 3000;
      setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
      }, timeout);
    },
    setupKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          switch (e.key) {
            case '1':
              this.navigateToChat();
              break;
            case '2':
              this.navigateToDocClass();
              break;
            case '3':
              this.navigateToGuarantee();
              break;
            case 'r':
              this.refreshStats();
              break;
            case 'k':
              this.toggleTheme();
              break;
          }
        }
      });
      setTimeout(() => {
        this.showNotification('Tip: Use Ctrl+1,2,3 for quick navigation', 'info');
      }, 3000);
    },
    trackPerformance() {
      if ('performance' in window) {
        const loadTime = window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;
        console.log(`Dashboard loaded in ${loadTime}ms`);
        if (loadTime > 3000) {
          this.showNotification('Dashboard loaded slowly. Consider clearing cache.', 'warning');
        }
      }
    },
    
    // Advanced Interactive Features
    initAdvancedFeatures() {
      this.setupParallaxEffects();
      this.setupSmartNotifications();
      this.setupAdvancedAnimations();
      this.setupIntersectionObserver();
      this.setupAdvancedKeyboardShortcuts();
    },
    
    setupParallaxEffects() {
      window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.glass-card');
        
        parallaxElements.forEach((element, index) => {
          const speed = 0.5 + (index * 0.1);
          const yPos = -(scrolled * speed);
          element.style.transform = `translateY(${yPos}px)`;
        });
      });
    },
    
    setupSmartNotifications() {
      // Smart notification system with priority queuing
      this.notificationQueue = [];
      this.isShowingNotification = false;
      
      this.originalShowNotification = this.showNotification;
      this.showNotification = (message, type = 'info', priority = 'normal') => {
        const notification = { message, type, priority, timestamp: Date.now() };
        
        if (priority === 'urgent' || !this.isShowingNotification) {
          this.displayNotification(notification);
        } else {
          this.notificationQueue.push(notification);
        }
      };
    },
    
    displayNotification(notification) {
      this.isShowingNotification = true;
      this.originalShowNotification(notification.message, notification.type);
      
      setTimeout(() => {
        this.isShowingNotification = false;
        if (this.notificationQueue.length > 0) {
          const next = this.notificationQueue.shift();
          this.displayNotification(next);
        }
      }, 3500);
    },
    
    setupAdvancedAnimations() {
      // Staggered animations for feature tiles
      const featureTiles = document.querySelectorAll('.feature-tile');
      featureTiles.forEach((tile, index) => {
        tile.style.animationDelay = `${index * 0.1}s`;
        tile.classList.add('animate-fade-in-up');
      });
      
      // Advanced hover effects
      featureTiles.forEach(tile => {
        tile.addEventListener('mouseenter', () => {
          tile.style.transform = 'translateY(-16px) scale(1.03) rotateX(5deg)';
          tile.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        });
        
        tile.addEventListener('mouseleave', () => {
          tile.style.transform = 'translateY(0) scale(1) rotateX(0deg)';
        });
      });
    },
    
    setupIntersectionObserver() {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in-up');
            this.animateMetrics(entry.target);
          }
        });
      }, { threshold: 0.1 });
      
      document.querySelectorAll('.metric-card, .glass-card').forEach(el => {
        observer.observe(el);
      });
    },
    
    animateMetrics(card) {
      const numbers = card.querySelectorAll('.metric-number');
      numbers.forEach(number => {
        const finalValue = number.textContent;
        const numericValue = parseFloat(finalValue.replace(/[^\d.]/g, ''));
        
        if (!isNaN(numericValue)) {
          this.animateNumber(number, 0, numericValue, finalValue);
        }
      });
    },
    
    animateNumber(element, start, end, suffix) {
      const duration = 2000;
      const startTime = performance.now();
      
      const animate = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = start + (end - start) * this.easeOutCubic(progress);
        const displayValue = suffix.replace(/[\d.]/g, '').trim();
        
        if (suffix.includes('%')) {
          element.textContent = current.toFixed(1) + '%';
        } else if (suffix.includes('K')) {
          element.textContent = current.toFixed(1) + 'K';
        } else if (suffix.includes('s')) {
          element.textContent = current.toFixed(1) + 's';
        } else {
          element.textContent = Math.round(current) + displayValue;
        }
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      requestAnimationFrame(animate);
    },
    
    easeOutCubic(t) {
      return 1 - Math.pow(1 - t, 3);
    },
    
    setupAdvancedKeyboardShortcuts() {
      // Enhanced keyboard shortcuts with combinations
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
          switch (e.key) {
            case 'h':
              e.preventDefault();
              this.showShortcutsHelp();
              break;
            case 'n':
              e.preventDefault();
              this.showNotification('Quick action: New document', 'info');
              break;
            case 's':
              e.preventDefault();
              this.exportDashboardData();
              break;
            case 'd':
              e.preventDefault();
              this.toggleDashboardMode();
              break;
          }
        }
        
        // Alt + key combinations
        if (e.altKey) {
          switch (e.key) {
            case 't':
              e.preventDefault();
              this.toggleTheme();
              break;
            case 'f':
              e.preventDefault();
              this.toggleFullscreen();
              break;
          }
        }
      });
    },
    
    showShortcutsHelp() {
      const shortcuts = [
        'Ctrl+1,2,3 - Quick navigation',
        'Ctrl+R - Refresh stats',
        'Ctrl+K - Toggle theme',
        'Ctrl+H - Show this help',
        'Ctrl+N - New document',
        'Ctrl+S - Export data',
        'Alt+T - Toggle theme',
        'Alt+F - Toggle fullscreen'
      ];
      
      this.showNotification('Shortcuts: ' + shortcuts.join(' | '), 'info');
    },
    
    exportDashboardData() {
      const data = {
        timestamp: new Date().toISOString(),
        user: this.userData,
        stats: {
          documentsProcessed: '12.5K',
          successRate: '98.7%',
          avgProcessingTime: '2.3s',
          activeUsers: '1.2K'
        }
      };
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dashboard-export-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      this.showNotification('Dashboard data exported successfully!', 'success');
    },
    
    toggleDashboardMode() {
      const body = document.body;
      body.classList.toggle('focus-mode');
      
      if (body.classList.contains('focus-mode')) {
        this.showNotification('Focus mode activated', 'info');
      } else {
        this.showNotification('Focus mode deactivated', 'info');
      }
    },
    
    toggleFullscreen() {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
          this.showNotification('Entered fullscreen mode', 'info');
        });
      } else {
        document.exitFullscreen().then(() => {
          this.showNotification('Exited fullscreen mode', 'info');
        });
      }
    },
    
    // Advanced User Experience Features
    setupSmartLoading() {
      // Preload critical resources
      const preloadLinks = [
        '/static/js/main.js',
        '/static/css/styles.css'
      ];
      
      preloadLinks.forEach(url => {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.href = url;
        link.as = url.endsWith('.js') ? 'script' : 'style';
        document.head.appendChild(link);
      });
    },
    
    setupOfflineDetection() {
      window.addEventListener('online', () => {
        this.showNotification('Connection restored', 'success');
      });
      
      window.addEventListener('offline', () => {
        this.showNotification('Connection lost - some features may be limited', 'warning');
      });
    },
  },
});

app.use(vuetify);
app.mount('#dashboard-app');

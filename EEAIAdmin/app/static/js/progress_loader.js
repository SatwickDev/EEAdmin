/**
 * Progress Loader Component with WebSocket Integration
 * Real-time progress updates for document processing, OCR, and AI analysis
 */

class ProgressLoader {
    constructor(options = {}) {
        this.containerId = options.containerId || 'progress-loader-container';
        this.wsClient = options.wsClient || window.aiWebSocket;
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});

        // State
        this.currentTaskId = null;
        this.isVisible = false;
        this.currentProgress = 0;
        this.currentStage = '';
        this.currentMessage = '';

        // Stage display names
        this.stageNames = {
            'initializing': 'Initializing',
            'uploading': 'Uploading Document',
            'quality_analysis': 'Analyzing Quality',
            'ocr_extraction': 'Extracting Text (OCR)',
            'document_classification': 'Analyzing Document',
            'field_extraction': 'Extracting Fields',
            'compliance_check': 'Checking Compliance',
            'finalizing': 'Finalizing',
            'completed': 'Complete',
            'error': 'Error'
        };

        // Stage icons (Material Design Icons)
        this.stageIcons = {
            'initializing': 'mdi-cog',
            'uploading': 'mdi-cloud-upload',
            'quality_analysis': 'mdi-magnify',
            'ocr_extraction': 'mdi-text-recognition',
            'document_classification': 'mdi-file-search',
            'field_extraction': 'mdi-table-search',
            'compliance_check': 'mdi-shield-check',
            'finalizing': 'mdi-check-circle',
            'completed': 'mdi-check-circle',
            'error': 'mdi-alert-circle'
        };

        this._createUI();
        this._registerWebSocketHandlers();
    }

    /**
     * Create loader UI
     * @private
     */
    _createUI() {
        // Create container if it doesn't exist
        let container = document.getElementById(this.containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            document.body.appendChild(container);
        }

        // Create loader HTML
        container.innerHTML = `
            <div class="progress-loader-overlay" id="progress-loader-overlay" style="display: none;">
                <div class="progress-loader-modal">
                    <!-- Header -->
                    <div class="progress-loader-header">
                        <div class="progress-loader-icon">
                            <i class="mdi mdi-cog mdi-spin"></i>
                        </div>
                        <h3 class="progress-loader-title">Processing Document</h3>
                    </div>

                    <!-- Progress Bar -->
                    <div class="progress-loader-body">
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill" id="progress-bar-fill" style="width: 0%">
                                <span class="progress-bar-text" id="progress-bar-text">0%</span>
                            </div>
                        </div>

                        <!-- Stage Info -->
                        <div class="progress-stage-info">
                            <div class="progress-stage-icon">
                                <i class="mdi mdi-cog" id="progress-stage-icon"></i>
                            </div>
                            <div class="progress-stage-text">
                                <div class="progress-stage-name" id="progress-stage-name">Initializing</div>
                                <div class="progress-stage-message" id="progress-stage-message">Preparing to process document...</div>
                            </div>
                        </div>

                        <!-- Stage Progress Indicators -->
                        <div class="progress-stages">
                            <div class="progress-stage-item" data-stage="uploading">
                                <div class="progress-stage-dot"></div>
                                <span>Upload</span>
                            </div>
                            <div class="progress-stage-item" data-stage="quality_analysis">
                                <div class="progress-stage-dot"></div>
                                <span>Quality</span>
                            </div>
                            <div class="progress-stage-item" data-stage="ocr_extraction">
                                <div class="progress-stage-dot"></div>
                                <span>OCR</span>
                            </div>
                            <div class="progress-stage-item" data-stage="document_classification">
                                <div class="progress-stage-dot"></div>
                                <span>Classify</span>
                            </div>
                            <div class="progress-stage-item" data-stage="field_extraction">
                                <div class="progress-stage-dot"></div>
                                <span>Extract</span>
                            </div>
                            <div class="progress-stage-item" data-stage="compliance_check">
                                <div class="progress-stage-dot"></div>
                                <span>Comply</span>
                            </div>
                            <div class="progress-stage-item" data-stage="finalizing">
                                <div class="progress-stage-dot"></div>
                                <span>Finalize</span>
                            </div>
                            <div class="progress-stage-item" data-stage="completed">
                                <div class="progress-stage-dot"></div>
                                <span>Done</span>
                            </div>
                        </div>

                        <!-- Time Elapsed -->
                        <div class="progress-time-info">
                            <i class="mdi mdi-clock-outline"></i>
                            <span id="progress-time-elapsed">0s</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this._addStyles();
    }

    /**
     * Add CSS styles
     * @private
     */
    _addStyles() {
        if (document.getElementById('progress-loader-styles')) return;

        const style = document.createElement('style');
        style.id = 'progress-loader-styles';
        style.textContent = `
            .progress-loader-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(5px);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s ease;
            }

            .progress-loader-modal {
                background: white;
                border-radius: 24px;
                padding: 40px;
                max-width: 600px;
                width: 90%;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
                animation: slideUp 0.3s ease;
            }

            .progress-loader-header {
                text-align: center;
                margin-bottom: 32px;
            }

            .progress-loader-icon {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 16px;
            }

            .progress-loader-icon i {
                font-size: 40px;
                color: white;
            }

            .progress-loader-title {
                font-size: 24px;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
            }

            .progress-bar-container {
                background: #f1f5f9;
                border-radius: 12px;
                height: 48px;
                overflow: hidden;
                margin-bottom: 24px;
                position: relative;
            }

            .progress-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
            }

            .progress-bar-fill::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
                animation: shimmer 2s infinite;
            }

            @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }

            .progress-bar-text {
                color: white;
                font-weight: 700;
                font-size: 18px;
                z-index: 1;
            }

            .progress-stage-info {
                display: flex;
                align-items: flex-start;
                gap: 16px;
                margin-bottom: 24px;
                padding: 20px;
                background: #f8fafc;
                border-radius: 16px;
            }

            .progress-stage-icon {
                width: 48px;
                height: 48px;
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }

            .progress-stage-icon i {
                font-size: 24px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .progress-stage-text {
                flex: 1;
            }

            .progress-stage-name {
                font-size: 16px;
                font-weight: 700;
                color: #1e293b;
                margin-bottom: 4px;
            }

            .progress-stage-message {
                font-size: 14px;
                color: #64748b;
            }

            .progress-stages {
                display: flex;
                justify-content: space-between;
                margin-bottom: 24px;
                padding: 0 8px;
            }

            .progress-stage-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                flex: 1;
                position: relative;
            }

            .progress-stage-item::after {
                content: '';
                position: absolute;
                top: 12px;
                left: 50%;
                width: 100%;
                height: 2px;
                background: #e2e8f0;
                z-index: -1;
            }

            .progress-stage-item:last-child::after {
                display: none;
            }

            .progress-stage-dot {
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: #e2e8f0;
                border: 3px solid white;
                transition: all 0.3s ease;
            }

            .progress-stage-item.active .progress-stage-dot {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                transform: scale(1.2);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }

            .progress-stage-item.completed .progress-stage-dot {
                background: #10b981;
                transform: scale(1.1);
                box-shadow: 0 3px 8px rgba(16, 185, 129, 0.4);
                position: relative;
            }

            .progress-stage-item.completed .progress-stage-dot::after {
                content: "✓";
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 12px;
                font-weight: bold;
            }

            .progress-stage-item.completed span {
                color: #10b981;
                font-weight: 600;
            }

            .progress-stage-item span {
                font-size: 11px;
                color: #64748b;
                font-weight: 500;
                text-align: center;
            }

            .progress-stage-item.active span {
                color: #667eea;
                font-weight: 700;
            }

            .progress-time-info {
                text-align: center;
                color: #64748b;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .mdi-spin {
                animation: spin 2s linear infinite;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Register WebSocket event handlers
     * @private
     */
    _registerWebSocketHandlers() {
        if (!this.wsClient) {
            console.warn('WebSocket client not available for ProgressLoader');
            return;
        }

        this.wsClient.on('progress_update', (data) => {
            if (this.currentTaskId && data.task_id === this.currentTaskId) {
                this._updateProgress(data);
            }
        });
    }

    /**
     * Show loader
     */
    show(taskId = null) {
        this.currentTaskId = taskId || this._generateTaskId();
        this.isVisible = true;
        this.startTime = Date.now();

        const overlay = document.getElementById('progress-loader-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }

        // Start time counter
        this._startTimeCounter();

        console.log('🔄 Progress loader shown for task:', this.currentTaskId);
    }

    /**
     * Hide loader
     */
    hide() {
        this.isVisible = false;
        this.currentTaskId = null;

        const overlay = document.getElementById('progress-loader-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }

        // Stop time counter
        this._stopTimeCounter();

        // Reset progress
        this._resetProgress();

        console.log('✅ Progress loader hidden');
    }

    /**
     * Update progress
     * @private
     */
    _updateProgress(data) {
        const { stage, message, progress, metadata } = data;
        
        console.log(`📊 Progress update received:`, {
            stage,
            message,
            progress,
            metadata
        });

        // Update progress bar
        this._setProgress(progress);

        // Update stage
        this._setStage(stage, message);

        // Mark stage indicators
        this._updateStageIndicators(stage);

        // Handle completion or error
        if (stage === 'completed') {
            setTimeout(() => {
                this.hide();
                this.onComplete(metadata);
            }, 1500);
        } else if (stage === 'error') {
            setTimeout(() => {
                this.hide();
                this.onError(data);
            }, 2000);
        }
    }

    /**
     * Set progress percentage
     * @private
     */
    _setProgress(progress) {
        this.currentProgress = progress;

        const fill = document.getElementById('progress-bar-fill');
        const text = document.getElementById('progress-bar-text');

        if (fill) {
            fill.style.width = `${progress}%`;
        }

        if (text) {
            text.textContent = `${progress}%`;
        }
    }

    /**
     * Set current stage
     * @private
     */
    _setStage(stage, message) {
        this.currentStage = stage;
        this.currentMessage = message;

        const stageName = document.getElementById('progress-stage-name');
        const stageMessage = document.getElementById('progress-stage-message');
        const stageIcon = document.getElementById('progress-stage-icon');

        if (stageName) {
            stageName.textContent = this.stageNames[stage] || stage;
        }

        if (stageMessage) {
            stageMessage.textContent = message;
        }

        if (stageIcon) {
            stageIcon.className = `mdi ${this.stageIcons[stage] || 'mdi-cog'}`;
            if (stage !== 'completed' && stage !== 'error') {
                stageIcon.classList.add('mdi-spin');
            }
        }
    }

    /**
     * Update stage indicators
     * @private
     */
    _updateStageIndicators(currentStage) {
        console.log(`🔄 _updateStageIndicators called with stage: '${currentStage}'`);
        
        const stages = ['uploading', 'quality_analysis', 'ocr_extraction', 'document_classification', 'field_extraction', 'compliance_check', 'finalizing', 'completed'];
        const currentIndex = stages.indexOf(currentStage);
        
        console.log(`   Stage index: ${currentIndex} (${currentIndex >= 0 ? 'FOUND' : 'NOT FOUND'})`);

        stages.forEach((stage, index) => {
            const item = document.querySelector(`.progress-stage-item[data-stage="${stage}"]`);
            if (item) {
                item.classList.remove('active', 'completed');

                if (index < currentIndex) {
                    item.classList.add('completed');
                    console.log(`   ✅ Marked '${stage}' as COMPLETED (green)`);
                } else if (index === currentIndex) {
                    item.classList.add('active');
                    console.log(`   🔵 Marked '${stage}' as ACTIVE (blue)`);
                } else {
                    console.log(`   ⚪ Marked '${stage}' as PENDING (default)`);
                }
            } else {
                console.log(`   ❌ HTML element not found for stage: '${stage}'`);
            }
        });
    }

    /**
     * Start time counter
     * @private
     */
    _startTimeCounter() {
        this._stopTimeCounter();

        this.timeInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const timeElement = document.getElementById('progress-time-elapsed');
            if (timeElement) {
                timeElement.textContent = `${elapsed}s`;
            }
        }, 1000);
    }

    /**
     * Stop time counter
     * @private
     */
    _stopTimeCounter() {
        if (this.timeInterval) {
            clearInterval(this.timeInterval);
            this.timeInterval = null;
        }
    }

    /**
     * Reset progress
     * @private
     */
    _resetProgress() {
        this._setProgress(0);
        this._setStage('initializing', 'Preparing to process document...');

        // Reset stage indicators
        document.querySelectorAll('.progress-stage-item').forEach(item => {
            item.classList.remove('active', 'completed');
        });
    }

    /**
     * Generate task ID
     * @private
     */
    _generateTaskId() {
        return `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get current task ID
     */
    getTaskId() {
        return this.currentTaskId;
    }
}

// Create global progress loader instance
// Export ProgressLoader class globally
window.ProgressLoader = ProgressLoader;

// Global instance
window.progressLoader = new ProgressLoader({
    wsClient: window.aiWebSocket,
    onComplete: (metadata) => {
        console.log('✅ Processing complete:', metadata);
    },
    onError: (error) => {
        console.error('❌ Processing error:', error);
    }
});

console.log('✅ Progress Loader initialized');

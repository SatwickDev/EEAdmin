/**
 * WebSocket Client for Real-time AI Communication
 * Handles WebSocket connections for streaming AI responses
 */

class AIWebSocketClient {
    constructor(options = {}) {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
        this.reconnectDelay = options.reconnectDelay || 1000;
        this.pingInterval = options.pingInterval || 30000;
        this.pingTimer = null;
        this.eventHandlers = {};
        this.requestCallbacks = new Map();

        // Connection state
        this.clientId = null;
        this.connectionEstablishedAt = null;

        // Auto-connect if specified
        if (options.autoConnect !== false) {
            this.connect();
        }
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        try {
            console.log('🔌 Connecting to WebSocket server...');

            // Initialize Socket.IO connection
            this.socket = io({
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay,
                timeout: 10000
            });

            // Register event handlers
            this._registerEventHandlers();

            return this;
        } catch (error) {
            console.error('❌ Failed to connect to WebSocket:', error);
            this._triggerEvent('error', { error: error.message });
            return null;
        }
    }

    /**
     * Register WebSocket event handlers
     * @private
     */
    _registerEventHandlers() {
        // Connection established
        this.socket.on('connect', () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            console.log('✅ WebSocket connected');
            this._startPing();
            this._triggerEvent('connect', {});
        });

        // Connection established confirmation from server
        this.socket.on('connection_established', (data) => {
            this.clientId = data.client_id;
            this.connectionEstablishedAt = new Date(data.timestamp);
            console.log('✅ Connection established:', data);
            this._triggerEvent('connection_established', data);
        });

        // Disconnection
        this.socket.on('disconnect', (reason) => {
            this.connected = false;
            console.log('🔌 WebSocket disconnected:', reason);
            this._stopPing();
            this._triggerEvent('disconnect', { reason });

            // Auto-reconnect logic
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
                console.log(`⏳ Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                setTimeout(() => this.connect(), delay);
            }
        });

        // Error handling
        this.socket.on('error', (error) => {
            console.error('❌ WebSocket error:', error);
            this._triggerEvent('error', { error: error.message || error });
        });

        // Pong response
        this.socket.on('pong', (data) => {
            console.log('🏓 Pong received:', data);
        });

        // Request acknowledged
        this.socket.on('request_acknowledged', (data) => {
            console.log('📨 Request acknowledged:', data);
            this._triggerEvent('request_acknowledged', data);
        });

        // Stream start
        this.socket.on('stream_start', (data) => {
            console.log('▶️  Stream started:', data.request_id);
            this._triggerEvent('stream_start', data);
        });

        // Stream chunk
        this.socket.on('stream_chunk', (data) => {
            console.log('📦 Received chunk:', data.chunk_number);
            this._triggerEvent('stream_chunk', data);

            // Call request-specific callback if exists
            const callback = this.requestCallbacks.get(data.request_id);
            if (callback && callback.onChunk) {
                callback.onChunk(data);
            }
        });

        // Stream end
        this.socket.on('stream_end', (data) => {
            console.log('⏹️  Stream ended:', data.request_id);
            this._triggerEvent('stream_end', data);

            // Call request-specific callback if exists
            const callback = this.requestCallbacks.get(data.request_id);
            if (callback && callback.onComplete) {
                callback.onComplete(data);
            }

            // Clean up callback
            this.requestCallbacks.delete(data.request_id);
        });

        // Progress updates for document processing
        this.socket.on('progress_update', (data) => {
            console.log('📊 Progress update:', data);
            this._triggerEvent('progress_update', data);
        });

        // Progress update handler
        this.socket.on('progress_update', (data) => {
            console.log('📊 Progress update:', data);
            this._triggerEvent('progress_update', data);
        });

        // Progress updates for document processing
        this.socket.on('progress_update', (data) => {
            console.log('📊 Progress update:', data);
            this._triggerEvent('progress_update', data);
        });
    }

    /**
     * Send AI request
     */
    sendAIRequest(type, payload, callbacks = {}) {
        if (!this.connected) {
            console.error('❌ Cannot send request: WebSocket not connected');
            if (callbacks.onError) {
                callbacks.onError({ error: 'Not connected' });
            }
            return null;
        }

        const requestId = this._generateRequestId();

        // Store callbacks for this request
        this.requestCallbacks.set(requestId, callbacks);

        // Send request
        this.socket.emit('ai_request', {
            type,
            payload,
            request_id: requestId,
            timestamp: new Date().toISOString()
        });

        console.log('📤 Sent AI request:', requestId);
        return requestId;
    }

    /**
     * Send chat message
     */
    sendChatMessage(message, context = {}, callbacks = {}) {
        return this.sendAIRequest('chat', {
            message,
            context,
            stream: true
        }, callbacks);
    }

    /**
     * Request document analysis
     */
    requestDocumentAnalysis(documentId, options = {}, callbacks = {}) {
        return this.sendAIRequest('document_analysis', {
            document_id: documentId,
            ...options
        }, callbacks);
    }

    /**
     * Request compliance check
     */
    requestComplianceCheck(content, rules = [], callbacks = {}) {
        return this.sendAIRequest('compliance_check', {
            content,
            rules
        }, callbacks);
    }

    /**
     * Register event handler
     */
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
        return this;
    }

    /**
     * Remove event handler
     */
    off(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        }
        return this;
    }

    /**
     * Trigger event
     * @private
     */
    _triggerEvent(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`❌ Error in ${event} handler:`, error);
                }
            });
        }
    }

    /**
     * Start ping/pong keep-alive
     * @private
     */
    _startPing() {
        this._stopPing();
        this.pingTimer = setInterval(() => {
            if (this.connected) {
                this.socket.emit('ping', { timestamp: new Date().toISOString() });
            }
        }, this.pingInterval);
    }

    /**
     * Stop ping/pong keep-alive
     * @private
     */
    _stopPing() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }

    /**
     * Generate unique request ID
     * @private
     */
    _generateRequestId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.socket) {
            this._stopPing();
            this.socket.disconnect();
            this.connected = false;
            this.socket = null;
            console.log('🔌 Disconnected from WebSocket server');
        }
    }

    /**
     * Get connection status
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Get client ID
     */
    getClientId() {
        return this.clientId;
    }
}

// Create global WebSocket client instance
window.aiWebSocket = new AIWebSocketClient({
    autoConnect: true,
    maxReconnectAttempts: 5,
    reconnectDelay: 1000,
    pingInterval: 30000
});

// Log connection events
window.aiWebSocket
    .on('connect', () => console.log('🎉 Connected to AI WebSocket'))
    .on('disconnect', () => console.log('👋 Disconnected from AI WebSocket'))
    .on('error', (data) => console.error('❌ WebSocket error:', data));

console.log('✅ AI WebSocket client initialized');

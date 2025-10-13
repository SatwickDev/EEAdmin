"""
WebSocket Handler for Real-time AI Streaming
Provides WebSocket support for streaming OpenAI responses to frontend
"""

import logging
import json
import asyncio
from typing import Dict, Optional, Callable, Any
from flask_socketio import emit, join_room, leave_room
from datetime import datetime

logger = logging.getLogger(__name__)

# Global WebSocket handler instance
ws_handler: Optional['WebSocketHandler'] = None


class WebSocketHandler:
    """Handles WebSocket connections for AI streaming"""

    def __init__(self, socketio):
        """
        Initialize WebSocket handler

        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio
        self.active_connections: Dict[str, dict] = {}
        self._register_events()

    def _register_events(self):
        """Register WebSocket event handlers"""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            client_id = self._get_client_id()
            self.active_connections[client_id] = {
                'connected_at': datetime.now().isoformat(),
                'room': client_id
            }
            join_room(client_id)
            logger.info(f"✅ WebSocket client connected: {client_id}")

            emit('connection_established', {
                'client_id': client_id,
                'status': 'connected',
                'timestamp': datetime.now().isoformat()
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = self._get_client_id()
            if client_id in self.active_connections:
                leave_room(client_id)
                del self.active_connections[client_id]
                logger.info(f"🔌 WebSocket client disconnected: {client_id}")

        @self.socketio.on('ping')
        def handle_ping(data=None):
            """Handle ping for keep-alive"""
            emit('pong', {'timestamp': datetime.now().isoformat()})

        @self.socketio.on('ai_request')
        def handle_ai_request(data):
            """Handle AI request from client"""
            client_id = self._get_client_id()
            logger.info(f"📨 AI request received from {client_id}")

            try:
                # Validate request data
                if not isinstance(data, dict):
                    self.emit_error(client_id, "Invalid request format")
                    return

                # Extract request parameters
                request_type = data.get('type', 'chat')
                payload = data.get('payload', {})
                request_id = data.get('request_id', self._generate_request_id())

                # Acknowledge request
                self.emit_message(client_id, 'request_acknowledged', {
                    'request_id': request_id,
                    'type': request_type,
                    'status': 'processing'
                })

                # Process request based on type
                if request_type == 'chat':
                    self._handle_chat_request(client_id, request_id, payload)
                elif request_type == 'document_analysis':
                    self._handle_document_analysis(client_id, request_id, payload)
                elif request_type == 'compliance_check':
                    self._handle_compliance_check(client_id, request_id, payload)
                else:
                    self.emit_error(client_id, f"Unknown request type: {request_type}")

            except Exception as e:
                logger.error(f"❌ Error handling AI request: {e}")
                self.emit_error(client_id, str(e))

    def _get_client_id(self) -> str:
        """Get current client session ID"""
        from flask import request
        return request.sid

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())

    def emit_message(self, client_id: str, event: str, data: dict):
        """
        Emit message to specific client

        Args:
            client_id: Client session ID
            event: Event name
            data: Data to send
        """
        try:
            self.socketio.emit(event, data, room=client_id)
        except Exception as e:
            logger.error(f"❌ Error emitting message to {client_id}: {e}")

    def emit_error(self, client_id: str, error_message: str):
        """
        Emit error message to client

        Args:
            client_id: Client session ID
            error_message: Error description
        """
        self.emit_message(client_id, 'error', {
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })

    def stream_ai_response(
        self,
        client_id: str,
        request_id: str,
        response_generator: Callable,
        chunk_size: int = 100
    ):
        """
        Stream AI response in chunks to client

        Args:
            client_id: Client session ID
            request_id: Request ID
            response_generator: Generator that yields response chunks
            chunk_size: Size of each chunk
        """
        try:
            # Emit stream start
            self.emit_message(client_id, 'stream_start', {
                'request_id': request_id,
                'timestamp': datetime.now().isoformat()
            })

            # Stream chunks
            chunk_count = 0
            for chunk in response_generator():
                chunk_count += 1
                self.emit_message(client_id, 'stream_chunk', {
                    'request_id': request_id,
                    'chunk': chunk,
                    'chunk_number': chunk_count,
                    'timestamp': datetime.now().isoformat()
                })

                # Small delay to prevent overwhelming the client
                import time
                time.sleep(0.01)

            # Emit stream end
            self.emit_message(client_id, 'stream_end', {
                'request_id': request_id,
                'total_chunks': chunk_count,
                'timestamp': datetime.now().isoformat()
            })

            logger.info(f"✅ Streamed {chunk_count} chunks to {client_id}")

        except Exception as e:
            logger.error(f"❌ Error streaming response: {e}")
            self.emit_error(client_id, f"Stream error: {str(e)}")

    def emit_progress(self, client_id: str, task_id: str, stage: str, message: str, progress: int, metadata: Optional[dict] = None):
        """
        Emit progress update to client

        Args:
            client_id: Client session ID
            task_id: Task identifier
            stage: Current processing stage
            message: Progress message
            progress: Progress percentage (0-100)
            metadata: Optional metadata
        """
        progress_data = {
            'task_id': task_id,
            'stage': stage,
            'message': message,
            'progress': progress,
            'timestamp': datetime.now().isoformat()
        }

        if metadata:
            progress_data['metadata'] = metadata

        self.emit_message(client_id, 'progress_update', progress_data)

    def _handle_chat_request(self, client_id: str, request_id: str, payload: dict):
        """Handle chat request (placeholder - implement with actual AI logic)"""
        # This will be implemented with actual OpenAI integration
        pass

    def _handle_document_analysis(self, client_id: str, request_id: str, payload: dict):
        """Handle document analysis request (placeholder)"""
        # This will be implemented with actual document processing
        pass

    def _handle_compliance_check(self, client_id: str, request_id: str, payload: dict):
        """Handle compliance check request (placeholder)"""
        # This will be implemented with actual compliance checking
        pass

    def broadcast_message(self, event: str, data: dict):
        """
        Broadcast message to all connected clients

        Args:
            event: Event name
            data: Data to broadcast
        """
        try:
            self.socketio.emit(event, data, broadcast=True)
            logger.info(f"📢 Broadcasted {event} to all clients")
        except Exception as e:
            logger.error(f"❌ Error broadcasting message: {e}")

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def is_connected(self, client_id: str) -> bool:
        """Check if client is connected"""
        return client_id in self.active_connections


# Global WebSocket handler instance (will be initialized in app factory)
ws_handler: Optional[WebSocketHandler] = None


def init_websocket_handler(socketio):
    """
    Initialize global WebSocket handler

    Args:
        socketio: Flask-SocketIO instance

    Returns:
        WebSocketHandler instance
    """
    global ws_handler
    logger.info("🔌 Initializing WebSocket handler...")
    try:
        ws_handler = WebSocketHandler(socketio)
        logger.info("✅ WebSocket handler initialized successfully")
        return ws_handler
    except Exception as e:
        logger.error(f"❌ Failed to initialize WebSocket handler: {e}")
        raise


def get_websocket_handler() -> Optional[WebSocketHandler]:
    """Get global WebSocket handler instance"""
    return ws_handler

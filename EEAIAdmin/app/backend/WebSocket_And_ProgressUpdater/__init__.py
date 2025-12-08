"""
WebSocket And Progress Updater Module
=====================================

This module provides WebSocket handling and progress tracking functionality
for real-time communication and job status updates in the application.

Key Components:
- WebSocketHandler: Handles WebSocket connections, events, and AI streaming
- ProgressTracker: Base class for tracking task progress
- DocumentProcessingTracker: Specialized tracker for document processing stages
- ProcessingStage: Enum defining processing stages
- StatusRoutes: Routes for checking job/task status

Usage:
    from app.backend.WebSocket_And_ProgressUpdater import (
        WebSocketHandler,
        init_websocket_handler,
        get_websocket_handler,
        ProgressTracker,
        DocumentProcessingTracker,
        ProcessingStage,
        create_progress_tracker,
        register_status_routes,
        get_llm_compliance_tracker,
        get_compliance_status_tracker,
        set_llm_compliance_status,
        set_compliance_status
    )
"""

import logging

logger = logging.getLogger(__name__)

# Import WebSocket components
from .websocket_handler import (
    WebSocketHandler,
    init_websocket_handler,
    get_websocket_handler
)

# Import Progress Tracking components
from .progress_tracker import (
    ProcessingStage,
    ProgressTracker,
    DocumentProcessingTracker,
    create_progress_tracker
)

# Import Status Routes and Tracker functions
from .status_routes import (
    register_status_routes,
    get_llm_compliance_tracker,
    get_compliance_status_tracker,
    set_llm_compliance_status,
    set_compliance_status,
    llm_compliance_tracker,
    compliance_status_tracker
)

# Export all components
__all__ = [
    # WebSocket
    'WebSocketHandler',
    'init_websocket_handler',
    'get_websocket_handler',
    # Progress Tracking
    'ProcessingStage',
    'ProgressTracker',
    'DocumentProcessingTracker',
    'create_progress_tracker',
    # Status Routes
    'register_status_routes',
    'get_llm_compliance_tracker',
    'get_compliance_status_tracker',
    'set_llm_compliance_status',
    'set_compliance_status',
    'llm_compliance_tracker',
    'compliance_status_tracker'
]

logger.info("✅ WebSocket_And_ProgressUpdater module initialized")

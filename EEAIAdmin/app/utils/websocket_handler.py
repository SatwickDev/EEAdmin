"""
WebSocket Handler for Real-time AI Streaming
============================================

DEPRECATED: This module has been moved to:
    app.backend.WebSocket_And_ProgressUpdater.websocket_handler

This file is kept for backward compatibility only.
Please update your imports to use the new location.
"""

import warnings
import logging

logger = logging.getLogger(__name__)

# Emit deprecation warning
warnings.warn(
    "app.utils.websocket_handler is deprecated. "
    "Use app.backend.WebSocket_And_ProgressUpdater instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from app.backend.WebSocket_And_ProgressUpdater.websocket_handler import (
    WebSocketHandler,
    init_websocket_handler,
    get_websocket_handler,
    ws_handler
)

__all__ = [
    'WebSocketHandler',
    'init_websocket_handler', 
    'get_websocket_handler',
    'ws_handler'
]

logger.info("Warning: websocket_handler imported from old location. Please update to use app.backend.WebSocket_And_ProgressUpdater")

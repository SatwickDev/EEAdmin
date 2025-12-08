"""
Progress Tracker for Document Processing with WebSocket Integration
===================================================================

DEPRECATED: This module has been moved to:
    app.backend.WebSocket_And_ProgressUpdater.progress_tracker

This file is kept for backward compatibility only.
Please update your imports to use the new location.
"""

import warnings
import logging

logger = logging.getLogger(__name__)

# Emit deprecation warning
warnings.warn(
    "app.utils.progress_tracker is deprecated. "
    "Use app.backend.WebSocket_And_ProgressUpdater instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from app.backend.WebSocket_And_ProgressUpdater.progress_tracker import (
    ProcessingStage,
    ProgressTracker,
    DocumentProcessingTracker,
    create_progress_tracker
)

__all__ = [
    'ProcessingStage',
    'ProgressTracker',
    'DocumentProcessingTracker',
    'create_progress_tracker'
]

logger.info("Warning: progress_tracker imported from old location. Please update to use app.backend.WebSocket_And_ProgressUpdater")

"""
Progress Tracker for Document Processing with WebSocket Integration
Provides real-time progress updates for OCR, AI analysis, and document processing
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Enumeration of processing stages"""
    INITIALIZING = "initializing"
    UPLOADING = "uploading"
    QUALITY_ANALYSIS = "quality_analysis"
    OCR_EXTRACTION = "ocr_extraction"
    DOCUMENT_CLASSIFICATION = "document_classification"
    FIELD_EXTRACTION = "field_extraction"
    COMPLIANCE_CHECK = "compliance_check"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


class ProgressTracker:
    """Tracks and emits progress updates via WebSocket"""

    def __init__(self, websocket_handler=None, client_id: Optional[str] = None, task_id: Optional[str] = None):
        """
        Initialize progress tracker

        Args:
            websocket_handler: WebSocket handler instance
            client_id: Client session ID
            task_id: Unique task identifier
        """
        self.ws_handler = websocket_handler
        self.client_id = client_id
        self.task_id = task_id or self._generate_task_id()
        self.current_stage = None
        self.progress = 0
        self.total_steps = 0
        self.completed_steps = 0
        self.start_time = datetime.now()
        self.stage_times = {}
        self.errors = []

    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        import uuid
        return str(uuid.uuid4())

    def start(self, total_steps: int = 100, task_name: str = "Processing"):
        """
        Start tracking progress

        Args:
            total_steps: Total number of steps
            task_name: Name of the task
        """
        self.total_steps = total_steps
        self.completed_steps = 0
        self.progress = 0
        self.start_time = datetime.now()

        self._emit_update(
            stage=ProcessingStage.INITIALIZING,
            message=f"Starting {task_name}...",
            progress=0
        )

    def update_stage(self, stage: ProcessingStage, message: str, progress: Optional[int] = None):
        """
        Update current processing stage

        Args:
            stage: Processing stage
            message: Status message
            progress: Optional progress percentage (0-100)
        """
        # Record stage timing
        if self.current_stage:
            stage_duration = (datetime.now() - self.stage_times.get(self.current_stage, datetime.now())).total_seconds()
            logger.info(f"Stage '{self.current_stage.value}' completed in {stage_duration:.2f}s")

        self.current_stage = stage
        self.stage_times[stage] = datetime.now()

        if progress is not None:
            self.progress = progress

        self._emit_update(
            stage=stage,
            message=message,
            progress=self.progress
        )

    def update_progress(self, steps: int = 1, message: Optional[str] = None):
        """
        Update progress by number of steps

        Args:
            steps: Number of steps completed
            message: Optional status message
        """
        self.completed_steps += steps
        self.progress = int((self.completed_steps / self.total_steps) * 100) if self.total_steps > 0 else 0

        self._emit_update(
            stage=self.current_stage or ProcessingStage.INITIALIZING,
            message=message or f"Processing... {self.progress}%",
            progress=self.progress
        )

    def set_progress(self, progress: int, message: Optional[str] = None):
        """
        Set progress to specific percentage

        Args:
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        self.progress = min(100, max(0, progress))

        self._emit_update(
            stage=self.current_stage or ProcessingStage.INITIALIZING,
            message=message or f"Processing... {self.progress}%",
            progress=self.progress
        )

    def complete(self, message: str = "Processing completed successfully"):
        """
        Mark task as completed

        Args:
            message: Completion message
        """
        duration = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"Task '{self.task_id}' completed in {duration:.2f}s")

        self._emit_update(
            stage=ProcessingStage.COMPLETED,
            message=message,
            progress=100,
            metadata={'duration': duration}
        )

    def error(self, error_message: str, error_details: Optional[Dict] = None):
        """
        Mark task as failed

        Args:
            error_message: Error message
            error_details: Optional error details
        """
        self.errors.append({
            'message': error_message,
            'details': error_details,
            'timestamp': datetime.now().isoformat()
        })

        logger.error(f"Task '{self.task_id}' failed: {error_message}")

        self._emit_update(
            stage=ProcessingStage.ERROR,
            message=error_message,
            progress=self.progress,
            metadata={'error_details': error_details}
        )

    def _emit_update(self, stage: ProcessingStage, message: str, progress: int, metadata: Optional[Dict] = None):
        """
        Emit progress update via WebSocket

        Args:
            stage: Current processing stage
            message: Status message
            progress: Progress percentage
            metadata: Optional metadata
        """
        update_data = {
            'task_id': self.task_id,
            'stage': stage.value,
            'message': message,
            'progress': progress,
            'timestamp': datetime.now().isoformat(),
            'completed_steps': self.completed_steps,
            'total_steps': self.total_steps
        }

        if metadata:
            update_data['metadata'] = metadata

        # Emit via WebSocket if available
        if self.ws_handler and self.client_id:
            try:
                self.ws_handler.emit_message(
                    self.client_id,
                    'progress_update',
                    update_data
                )
            except Exception as e:
                logger.error(f"Failed to emit progress update: {e}")

        # Always log the update
        logger.info(f"Progress [{self.task_id}]: {stage.value} - {message} ({progress}%)")


class DocumentProcessingTracker(ProgressTracker):
    """Specialized tracker for document processing with predefined stages"""

    def __init__(self, websocket_handler=None, client_id: Optional[str] = None, task_id: Optional[str] = None):
        super().__init__(websocket_handler, client_id, task_id)
        # Define stage weights for progress calculation
        self.stage_weights = {
            ProcessingStage.UPLOADING: 10,
            ProcessingStage.QUALITY_ANALYSIS: 10,
            ProcessingStage.OCR_EXTRACTION: 25,
            ProcessingStage.DOCUMENT_CLASSIFICATION: 20,
            ProcessingStage.FIELD_EXTRACTION: 20,
            ProcessingStage.COMPLIANCE_CHECK: 10,
            ProcessingStage.FINALIZING: 5
        }

    def start_upload(self, filename: str):
        """Start file upload stage"""
        self.update_stage(
            ProcessingStage.UPLOADING,
            f"Uploading {filename}...",
            progress=5
        )

    def upload_complete(self):
        """Mark upload as complete and move to quality analysis"""
        self.update_stage(
            ProcessingStage.QUALITY_ANALYSIS,
            "Upload complete - Starting quality analysis...",
            progress=10
        )

    def start_quality_analysis(self):
        """Start quality analysis stage"""
        self.update_stage(
            ProcessingStage.QUALITY_ANALYSIS,
            "Analyzing document quality...",
            progress=10
        )

    def update_quality_progress(self, current_page: int, total_pages: int):
        """Update quality analysis progress for specific page"""
        page_progress = int((current_page / total_pages) * 100)
        overall_progress = 10 + int((page_progress / 100) * 10)  # Quality is 10-20%

        self.set_progress(
            overall_progress,
            f"Analyzing quality of page {current_page}/{total_pages}..."
        )

    def quality_complete(self, verdict: str, quality_score: float):
        """Mark quality analysis as complete and move to OCR"""
        self.update_stage(
            ProcessingStage.OCR_EXTRACTION,
            f"Quality analysis complete - {verdict} (score: {quality_score:.3f})",
            progress=20
        )

    def start_ocr(self, page_count: Optional[int] = None):
        """Start OCR extraction stage"""
        message = f"Extracting text from {page_count} pages..." if page_count else "Extracting text from document..."
        self.update_stage(
            ProcessingStage.OCR_EXTRACTION,
            message,
            progress=20
        )

    def update_ocr_progress(self, current_page: int, total_pages: int):
        """Update OCR progress for specific page"""
        page_progress = int((current_page / total_pages) * 100)
        overall_progress = 20 + int((page_progress / 100) * 25)  # OCR is 20-45%

        self.set_progress(
            overall_progress,
            f"Processing page {current_page}/{total_pages}..."
        )

    def ocr_complete(self, extracted_entries: int):
        """Mark OCR as complete and move to classification"""
        self.update_stage(
            ProcessingStage.DOCUMENT_CLASSIFICATION,
            f"OCR complete - Extracted {extracted_entries} text entries",
            progress=45
        )

    def start_classification(self):
        """Start document classification stage"""
        self.update_stage(
            ProcessingStage.DOCUMENT_CLASSIFICATION,
            "Analyzing document type with AI...",
            progress=50
        )

    def classification_complete(self, doc_type: str, confidence: int):
        """Mark classification as complete and move to field extraction"""
        self.update_stage(
            ProcessingStage.FIELD_EXTRACTION,
            f"Classified as {doc_type} (confidence: {confidence}%)",
            progress=65
        )

    def start_field_extraction(self, field_count: Optional[int] = None):
        """Start field extraction stage"""
        message = f"Extracting {field_count} fields..." if field_count else "Extracting document fields..."
        self.update_stage(
            ProcessingStage.FIELD_EXTRACTION,
            message,
            progress=65
        )

    def update_field_extraction(self, current_field: int, total_fields: int):
        """Update field extraction progress"""
        field_progress = int((current_field / total_fields) * 100)
        overall_progress = 65 + int((field_progress / 100) * 20)  # Field extraction is 65-85%

        self.set_progress(
            overall_progress,
            f"Extracting field {current_field}/{total_fields}..."
        )

    def field_extraction_complete(self, extracted_count: int):
        """Mark field extraction as complete and move to compliance check"""
        self.update_stage(
            ProcessingStage.COMPLIANCE_CHECK,
            f"Extracted {extracted_count} fields",
            progress=85
        )

    def start_compliance_check(self):
        """Start compliance checking stage"""
        self.update_stage(
            ProcessingStage.COMPLIANCE_CHECK,
            "Running compliance checks...",
            progress=87
        )

    def compliance_complete(self, issues_found: int):
        """Mark compliance check as complete and move to finalizing"""
        message = f"Compliance check complete - {issues_found} issues found" if issues_found > 0 else "Compliance check complete - No issues found"
        self.update_stage(
            ProcessingStage.FINALIZING,
            message,
            progress=95
        )

    def finalize(self):
        """Finalize processing"""
        self.update_stage(
            ProcessingStage.FINALIZING,
            "Finalizing results...",
            progress=98
        )

    def complete_with_summary(self, doc_type: str, fields_extracted: int, compliance_status: str):
        """Complete with summary"""
        summary = f"Document processed: {doc_type} | Fields: {fields_extracted} | Compliance: {compliance_status}"
        self.complete(summary)


# Helper function to create tracker instance
def create_progress_tracker(websocket_handler=None, client_id: Optional[str] = None, task_type: str = "document") -> ProgressTracker:
    """
    Create appropriate progress tracker instance

    Args:
        websocket_handler: WebSocket handler instance
        client_id: Client session ID
        task_type: Type of task ('document', 'generic')

    Returns:
        ProgressTracker instance
    """
    if task_type == "document":
        return DocumentProcessingTracker(websocket_handler, client_id)
    else:
        return ProgressTracker(websocket_handler, client_id)

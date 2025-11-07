"""
Simple Daily Log Manager
Creates daily log files in format: Filtered_Logs_DD-MM-YYYY.log
All application logs go to a single daily file.
"""

import logging
from datetime import datetime
from pathlib import Path


class DailyLogManager:
    """Manages daily log files with automatic date-based file creation"""
    
    def __init__(self, log_dir="Logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_date = None
        self.logger = None
        self.handler = None
        self._setup_daily_logger()
    
    def _get_daily_filename(self):
        """Generate daily log filename: Filtered_Logs_DD-MM-YYYY.log"""
        today = datetime.now()
        return f"Filtered_Logs_{today.strftime('%d-%m-%Y')}.log"
    
    def _setup_daily_logger(self):
        """Setup or refresh the daily logger"""
        today = datetime.now().date()
        
        # Check if we need to rotate to a new day
        if self.current_date != today:
            self._rotate_log_file()
            self.current_date = today
    
    def _rotate_log_file(self):
        """Rotate to new daily log file"""
        # Remove old handler if exists
        if self.handler and self.logger:
            self.logger.removeHandler(self.handler)
            self.handler.close()
        
        # Create new daily log file
        log_filename = self._get_daily_filename()
        log_path = self.log_dir / log_filename
        
        # Setup file handler
        self.handler = logging.FileHandler(log_path, mode='a',
                                           encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.handler.setFormatter(formatter)
        
        # Setup logger
        if not self.logger:
            self.logger = logging.getLogger('FilteredLogs')
            self.logger.setLevel(logging.DEBUG)
            # Remove default console handlers
            self.logger.handlers.clear()
        
        self.logger.addHandler(self.handler)
        
        # Log rotation message
        self.logger.info(f"=== Daily Log File Created: {log_filename} ===")
    
    def get_logger(self):
        """Get the daily logger instance"""
        self._setup_daily_logger()  # Check for date change
        return self.logger
    
    def log(self, level, message, **kwargs):
        """Log a message with optional metadata"""
        logger = self.get_logger()
        
        # Format message with metadata
        if kwargs:
            metadata = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {metadata}"
        
        # Log at appropriate level
        if level.upper() == 'ERROR':
            logger.error(message)
        elif level.upper() == 'WARNING':
            logger.warning(message)
        elif level.upper() == 'DEBUG':
            logger.debug(message)
        else:
            logger.info(message)


# Global instance
daily_logger = DailyLogManager()


def setup_application_logging():
    """Setup application-wide logging to daily files"""
    # Get the daily logger
    app_logger = daily_logger.get_logger()
    
    # Redirect root logger to our daily file
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Remove console handlers
    root_logger.addHandler(daily_logger.handler)
    root_logger.setLevel(logging.INFO)
    
    app_logger.info("=== Application Logging Initialized ===")
    return app_logger


def log_info(message, **kwargs):
    """Log info message"""
    daily_logger.log('INFO', message, **kwargs)


def log_error(message, **kwargs):
    """Log error message"""
    daily_logger.log('ERROR', message, **kwargs)


def log_warning(message, **kwargs):
    """Log warning message"""
    daily_logger.log('WARNING', message, **kwargs)


def log_debug(message, **kwargs):
    """Log debug message"""
    daily_logger.log('DEBUG', message, **kwargs)


# Convenience functions for different operation types
def log_api(method, endpoint, status_code, **kwargs):
    """Log API operations"""
    log_info(f"API {method} {endpoint} - Status: {status_code}", **kwargs)


def log_database(operation, table=None, **kwargs):
    """Log database operations"""
    msg = f"DATABASE {operation}"
    if table:
        msg += f" on {table}"
    log_info(msg, **kwargs)


def log_authentication(action, user_id=None, **kwargs):
    """Log authentication events"""
    msg = f"AUTH {action}"
    if user_id:
        msg += f" - User: {user_id}"
    log_info(msg, **kwargs)


def log_compliance(document_type, status, **kwargs):
    """Log compliance analysis"""
    log_info(f"COMPLIANCE {document_type} - Status: {status}", **kwargs)


def log_chroma(operation, collection=None, **kwargs):
    """Log Chroma vector database operations"""
    msg = f"CHROMA {operation}"
    if collection:
        msg += f" on {collection}"
    log_info(msg, **kwargs)


def log_system(event, message=None, **kwargs):
    """Log system events"""
    if message:
        log_info(f"SYSTEM {event} - {message}", **kwargs)
    else:
        log_info(f"SYSTEM {event}", **kwargs)


def log_performance(metric, value, unit="ms", **kwargs):
    """Log performance metrics"""
    log_info(f"PERFORMANCE {metric}: {value}{unit}", **kwargs)


def log_document_processing(operation, document_name=None, **kwargs):
    """Log document processing events"""
    msg = f"DOCUMENT {operation}"
    if document_name:
        msg += f" - {document_name}"
    log_info(msg, **kwargs)


def log_qr_processing(operation, **kwargs):
    """Log QR code processing"""
    log_info(f"QR {operation}", **kwargs)


def log_smart_capture(operation, **kwargs):
    """Log Smart Capture operations"""
    log_info(f"SMART_CAPTURE {operation}", **kwargs)
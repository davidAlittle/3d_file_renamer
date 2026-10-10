# src/utils/logging_config.py
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

class LogConfig:
    """Manages application logging configuration"""
    
    # Default configuration values
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DEFAULT_LEVEL = logging.INFO
    MAX_BYTES = 5 * 1024 * 1024  # 5MB
    BACKUP_COUNT = 5
    
    # Singleton instance
    _instance: Optional['LogConfig'] = None
    _initialized = False

    def __new__(cls) -> 'LogConfig':
        if cls._instance is None:
            cls._instance = super(LogConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.log_dir: Path = Path(__file__).parent.parent / "logs"
        self.loggers: Dict[str, logging.Logger] = {}
        self._initialized = True

    @classmethod
    def setup_logging(cls, 
                     log_level: int = None, 
                     log_format: str = None) -> logging.Logger:
        """
        Set up the main application logger.
        
        Args:
            log_level: Optional logging level (defaults to INFO)
            log_format: Optional log format string
            
        Returns:
            logging.Logger: Configured root logger
        """
        instance = cls()
        return instance._setup_main_logger(log_level, log_format)

    def _setup_main_logger(self, 
                          log_level: Optional[int] = None, 
                          log_format: Optional[str] = None) -> logging.Logger:
        """Set up the main application logger with file and console output"""
        try:
            # Ensure log directory exists
            self.log_dir.mkdir(exist_ok=True)
            
            # Generate log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"file_renamer_{timestamp}.log"
            
            # Configure root logger
            logger = logging.getLogger('FileRenamer')
            logger.setLevel(log_level or self.DEFAULT_LEVEL)
            
            # Create formatter
            formatter = logging.Formatter(
                log_format or self.DEFAULT_FORMAT
            )
            
            # File handler with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.MAX_BYTES,
                backupCount=self.BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # Store logger reference
            self.loggers['main'] = logger
            
            return logger
            
        except Exception as e:
            # If logging setup fails, ensure we at least have console output
            console_logger = logging.getLogger('FileRenamer')
            console_logger.setLevel(logging.ERROR)
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(logging.Formatter(self.DEFAULT_FORMAT))
            console_logger.addHandler(console_handler)
            
            console_logger.error(f"Failed to setup logging: {e}", exc_info=True)
            return console_logger

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a named logger with the application's configuration.
        
        Args:
            name: Logger name (will be prefixed with 'FileRenamer.')
            
        Returns:
            logging.Logger: Configured logger instance
        """
        try:
            full_name = f'FileRenamer.{name}'
            
            if full_name not in self.loggers:
                logger = logging.getLogger(full_name)
                
                # Inherit handlers from main logger if they exist
                main_logger = self.loggers.get('main')
                if main_logger:
                    for handler in main_logger.handlers:
                        logger.addHandler(handler.copy())
                
                self.loggers[full_name] = logger
                
            return self.loggers[full_name]
            
        except Exception as e:
            # Fall back to basic logger in case of error
            fallback = logging.getLogger(name)
            fallback.error(f"Error creating logger: {e}", exc_info=True)
            return fallback

    def set_level(self, level: int, logger_name: str = None):
        """
        Set logging level for specified or all loggers.
        
        Args:
            level: Logging level to set
            logger_name: Optional specific logger name
        """
        try:
            if logger_name:
                if logger_name in self.loggers:
                    self.loggers[logger_name].setLevel(level)
            else:
                for logger in self.loggers.values():
                    logger.setLevel(level)
                    
        except Exception as e:
            logging.error(f"Error setting log level: {e}", exc_info=True)

    def cleanup_old_logs(self, days: int = 30):
        """
        Clean up log files older than specified days.
        
        Args:
            days: Number of days to keep logs for
        """
        try:
            if not self.log_dir.exists():
                return
                
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    
        except Exception as e:
            logging.error(f"Error cleaning up old logs: {e}", exc_info=True)
# src/utils/logging_config.py
import logging
from pathlib import Path
from datetime import datetime

class LogConfig:
    @staticmethod
    def setup_logging(log_level=logging.INFO):
        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        log_file = log_dir / f"file_renamer_{datetime.now():%Y%m%d_%H%M%S}.log"
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        # Create logger for this application
        logger = logging.getLogger('FileRenamer')
        
        return logger

    @staticmethod
    def get_logger(name: str):
        """Get a logger with the given name"""
        return logging.getLogger(f'FileRenamer.{name}')
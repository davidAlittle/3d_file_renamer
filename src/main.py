# src/main.py
from datetime import datetime
import logging
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils.logging_config import LogConfig

# main.py
def setup_logging():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"file_renamer_{datetime.now():%Y%m%d}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def main():
    logger = LogConfig.setup_logging()
    logger.info("Starting File Renamer application")
    
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
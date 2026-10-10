# src/main.py
import sys

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.utils.logging_config import LogConfig


def main():
    logger = LogConfig.setup_logging()
    logger.info("Starting File Renamer application")

    try:
        logger.debug("Initializing QApplication")
        app = QApplication(sys.argv)

        logger.debug("Creating MainWindow")
        window = MainWindow()

        logger.debug("Showing MainWindow")
        window.show()

        logger.debug("Entering Qt event loop")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

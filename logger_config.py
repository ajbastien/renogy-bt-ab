# logger_config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_shared_logger():
    logger = logging.getLogger('shared_app_logger')
    logger.setLevel(logging.DEBUG) # Set desired logging level

    # Prevent adding multiple handlers if the function is called multiple times
    if not logger.handlers:
        # Create a RotatingFileHandler
        # filename: path to the log file
        # maxBytes: maximum size of the log file before rotation (e.g., 1MB)
        # backupCount: number of backup log files to keep
        file_handler = RotatingFileHandler(
            'renogy.log', 
            maxBytes=3 * 1024 * 1024, # 3MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO) # Set handler-specific level

        # Define log formatter
        formatter = logging.Formatter('%(asctime)s-%(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(file_handler)

    return logger

# Initialize the logger when the module is imported
logger = setup_shared_logger()

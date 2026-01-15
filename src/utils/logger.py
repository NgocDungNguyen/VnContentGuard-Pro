import logging
import os
import platform
import sys
from datetime import datetime


class SystemLogger:
    """
    Centralized logging system for VnContentGuard.
    Logs errors to 'logs/error.log' and scan history to 'logs/history.log'.
    """

    # Class-level logger instances
    _error_logger = None
    _history_logger = None
    _initialized = False

    @classmethod
    def initialize(cls, log_dir="logs"):
        """
        Initialize the logging system with two separate loggers.

        Args:
            log_dir (str): Directory to store log files (default: 'logs')
        """
        if cls._initialized:
            return

        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Configure error logger
        cls._error_logger = logging.getLogger("error_logger")
        cls._error_logger.setLevel(logging.ERROR)

        error_handler = logging.FileHandler(
            os.path.join(log_dir, "error.log"), encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        error_handler.setFormatter(error_formatter)

        # Avoid duplicate handlers
        if not cls._error_logger.handlers:
            cls._error_logger.addHandler(error_handler)

        # Configure history logger
        cls._history_logger = logging.getLogger("history_logger")
        cls._history_logger.setLevel(logging.INFO)

        history_handler = logging.FileHandler(
            os.path.join(log_dir, "history.log"), encoding="utf-8"
        )
        history_handler.setLevel(logging.INFO)
        history_formatter = logging.Formatter(
            "%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        history_handler.setFormatter(history_formatter)

        # Avoid duplicate handlers
        if not cls._history_logger.handlers:
            cls._history_logger.addHandler(history_handler)

        cls._initialized = True
        print(f"✅ Logger initialized. Log directory: {os.path.abspath(log_dir)}")

    @classmethod
    def log_error(cls, error_message, exception=None):
        """
        Log an error to error.log.

        Args:
            error_message (str): Description of the error
            exception (Exception, optional): The exception object
        """
        if not cls._initialized:
            cls.initialize()

        full_message = error_message
        if exception:
            full_message = (
                f"{error_message} | {type(exception).__name__}: {str(exception)}"
            )

        cls._error_logger.error(full_message)
        print(f"❌ {full_message}")

    @classmethod
    def log_scan(cls, scan_data):
        """
        Log a scan summary to history.log.

        Args:
            scan_data (dict): Dictionary containing scan information
                Expected keys: url, title, toxicity_status, fake_news_verdict, sentiment
        """
        if not cls._initialized:
            cls.initialize()

        # Format scan data for logging
        url = scan_data.get("url", "Unknown")
        title = scan_data.get("title", "No Title")[:100]  # Truncate long titles
        toxicity_status = scan_data.get("toxicity_status", "Unknown")
        fake_news_verdict = scan_data.get("fake_news_verdict", "Unknown")
        sentiment = scan_data.get("sentiment", "Unknown")

        log_message = (
            f"URL: {url} | Title: {title} | "
            f"Toxicity: {toxicity_status} | Fake News: {fake_news_verdict} | "
            f"Sentiment: {sentiment}"
        )

        cls._history_logger.info(log_message)

    @classmethod
    def log_comment_analysis(cls, comment_data):
        """
        Log a comment analysis result to history.log.

        Args:
            comment_data (dict): Dictionary containing comment info
                Expected keys: text, is_toxic, category, confidence, source
        """
        if not cls._initialized:
            cls.initialize()

        text = comment_data.get("text", "Unknown")[:80]  # Truncate
        is_toxic = comment_data.get("is_toxic", False)
        category = comment_data.get("category", "Unknown")
        confidence = comment_data.get("confidence", 0)
        source = comment_data.get("source", "Unknown")

        log_message = (
            f"COMMENT | Source: {source} | Text: {text} | "
            f"Toxic: {is_toxic} | Category: {category} | Confidence: {confidence:.2f}"
        )

        cls._history_logger.info(log_message)

    @classmethod
    def log_info(cls, message):
        """
        Log an informational message to history.log.

        Args:
            message (str): The message to log
        """
        if not cls._initialized:
            cls.initialize()

        cls._history_logger.info(message)

    @classmethod
    def log_warning(cls, message):
        """
        Log a warning message to both error.log and history.log.

        Args:
            message (str): The warning message
        """
        if not cls._initialized:
            cls.initialize()

        cls._error_logger.warning(message)
        cls._history_logger.warning(message)
        print(f"⚠️  {message}")

    @classmethod
    def get_log_files(cls, log_dir="logs"):
        """
        Get paths to the log files.

        Args:
            log_dir (str): Directory containing logs

        Returns:
            dict: Paths to error and history logs
        """
        return {
            "error_log": os.path.join(log_dir, "error.log"),
            "history_log": os.path.join(log_dir, "history.log"),
        }


# Initialize on import
SystemLogger.initialize()

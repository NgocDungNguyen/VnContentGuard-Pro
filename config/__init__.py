"""
Configuration Module for VnContentGuard
Loads settings from config/settings.yaml and provides convenient access.
"""

import os
from typing import Any, Dict, Optional

import yaml


class ConfigLoader:
    """
    Central configuration loader for VnContentGuard.
    Reads from config/settings.yaml and provides easy access to settings.
    """

    _instance = None
    _config = None

    def __new__(cls):
        """Singleton pattern to ensure only one config loader instance."""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the config loader."""
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        config_path = os.path.join(os.path.dirname(__file__), "settings.yaml")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Configuration file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            print(f"✅ Configuration loaded from {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"❌ Invalid YAML in settings.yaml: {str(e)}")
        except Exception as e:
            raise Exception(f"❌ Error loading configuration: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key (str): Configuration key (e.g., "api.gemini_api_key_env_var")
            default (Any): Default value if key not found

        Returns:
            Any: Configuration value

        Example:
            >>> config = ConfigLoader()
            >>> api_key_env = config.get("api.gemini_api_key_env_var")
            >>> timeout = config.get("api.timeout_api_call", 30)
        """
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    return default

            return value
        except (KeyError, TypeError):
            return default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.

        Args:
            section (str): Section name (e.g., "api", "toxicity")

        Returns:
            Dict: Configuration section as dictionary

        Example:
            >>> config = ConfigLoader()
            >>> api_config = config.get_section("api")
        """
        return self._config.get(section, {})

    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration.

        Returns:
            Dict: All configuration settings
        """
        return self._config.copy()

    def reload(self):
        """Reload configuration from file."""
        self._config = None
        self._load_config()


# ============================================================================
# Convenience Functions for Direct Access
# ============================================================================


def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value.

    Args:
        key (str): Configuration key in dot notation
        default (Any): Default value if not found

    Returns:
        Any: Configuration value

    Example:
        >>> from config import get_config
        >>> api_key = get_config("api.gemini_api_key_env_var", "GEMINI_API_KEY")
    """
    loader = ConfigLoader()
    return loader.get(key, default)


def get_api_config() -> Dict[str, Any]:
    """Get API configuration section."""
    loader = ConfigLoader()
    return loader.get_section("api")


def get_toxicity_config() -> Dict[str, Any]:
    """Get toxicity configuration section."""
    loader = ConfigLoader()
    return loader.get_section("toxicity")


def get_crawler_config() -> Dict[str, Any]:
    """Get crawler configuration section."""
    loader = ConfigLoader()
    return loader.get_section("crawlers")


def get_text_cleaning_config() -> Dict[str, Any]:
    """Get text cleaning configuration section."""
    loader = ConfigLoader()
    return loader.get_section("text_cleaning")


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration section."""
    loader = ConfigLoader()
    return loader.get_section("logging")


def get_sentiment_config() -> Dict[str, Any]:
    """Get sentiment analysis configuration section."""
    loader = ConfigLoader()
    return loader.get_section("sentiment")


def get_fake_news_config() -> Dict[str, Any]:
    """Get fake news detection configuration section."""
    loader = ConfigLoader()
    return loader.get_section("fake_news")


def get_ui_config() -> Dict[str, Any]:
    """Get UI configuration section."""
    loader = ConfigLoader()
    return loader.get_section("ui")


# ============================================================================
# Example Usage / Testing
# ============================================================================

if __name__ == "__main__":
    # Initialize config
    config = ConfigLoader()

    print("=" * 60)
    print("VnContentGuard Configuration Loader")
    print("=" * 60)

    # Test getting individual values
    print("\n✅ API Configuration:")
    print(f"  - API Key Env Var: {get_config('api.gemini_api_key_env_var')}")
    print(f"  - Primary Model: {get_config('api.gemini_model')}")
    print(f"  - API Timeout: {get_config('api.timeout_api_call')} seconds")

    print("\n✅ Toxicity Settings:")
    print(f"  - Confidence Threshold: {get_config('toxicity.confidence_threshold')}")
    print(f"  - Min Comment Length: {get_config('toxicity.min_comment_length')}")

    print("\n✅ Logging Configuration:")
    print(f"  - Log Directory: {get_config('logging.log_directory')}")
    print(f"  - Error Log: {get_config('logging.error_log.filename')}")

    print("\n✅ Sentiment Model:")
    print(f"  - Model: {get_config('sentiment.model_name')}")
    print(f"  - Max Text Length: {get_config('sentiment.max_text_length')}")

    print("\n" + "=" * 60)
    print("All configurations loaded successfully!")
    print("=" * 60)

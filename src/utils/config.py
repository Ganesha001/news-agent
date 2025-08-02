"""
Configuration management for the News Agent system.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger


class ConfigManager:
    """Manages configuration loading and access for the News Agent system."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file and environment variables."""
        # Load environment variables
        load_dotenv()
        
        # Load YAML configuration
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
        else:
            logger.warning(f"Configuration file not found: {self.config_path}")
            self._config = {}
        
        # Override with environment variables
        self._override_with_env()
        
        logger.info("Configuration loaded successfully")
    
    def _override_with_env(self):
        """Override configuration values with environment variables."""
        # API Keys
        if os.getenv("OPENAI_API_KEY"):
            self._config.setdefault("apis", {})["openai"] = {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "1000")),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
            }
        
        if os.getenv("TWILIO_ACCOUNT_SID"):
            self._config.setdefault("apis", {})["twilio"] = {
                "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
                "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
                "whatsapp_number": os.getenv("TWILIO_WHATSAPP_NUMBER")
            }
        
        if os.getenv("NEWSGUARD_API_KEY"):
            self._config.setdefault("apis", {})["newsguard"] = {
                "api_key": os.getenv("NEWSGUARD_API_KEY"),
                "enabled": True
            }
        
        # System configuration
        if os.getenv("DATABASE_URL"):
            self._config.setdefault("system", {})["database"] = {
                "url": os.getenv("DATABASE_URL")
            }
        
        if os.getenv("REDIS_HOST"):
            self._config.setdefault("system", {})["redis"] = {
                "host": os.getenv("REDIS_HOST"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "db": int(os.getenv("REDIS_DB", "0")),
                "password": os.getenv("REDIS_PASSWORD")
            }
        
        # User preferences
        if os.getenv("USER_TOPICS_OF_INTEREST"):
            topics = os.getenv("USER_TOPICS_OF_INTEREST").split(",")
            self._config.setdefault("notifications", {})["user_preferences"] = {
                "topics_of_interest": topics,
                "frequency": os.getenv("NOTIFICATION_FREQUENCY", "instant"),
                "language": os.getenv("LANGUAGE", "en")
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "apis.openai.model")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_news_sources(self) -> list:
        """Get the list of configured news sources.
        
        Returns:
            List of news source configurations
        """
        return self.get("news_sources.sources", [])
    
    def get_api_config(self, api_name: str) -> Dict[str, Any]:
        """Get configuration for a specific API.
        
        Args:
            api_name: Name of the API (e.g., "openai", "twilio")
            
        Returns:
            API configuration dictionary
        """
        return self.get(f"apis.{api_name}", {})
    
    def get_trend_detection_config(self) -> Dict[str, Any]:
        """Get trend detection configuration.
        
        Returns:
            Trend detection configuration dictionary
        """
        return self.get("trend_detection", {})
    
    def get_summarization_config(self) -> Dict[str, Any]:
        """Get summarization configuration.
        
        Returns:
            Summarization configuration dictionary
        """
        return self.get("summarization", {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration.
        
        Returns:
            Validation configuration dictionary
        """
        return self.get("validation", {})
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration.
        
        Returns:
            Notification configuration dictionary
        """
        return self.get("notifications", {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration.
        
        Returns:
            System configuration dictionary
        """
        return self.get("system", {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration.
        
        Returns:
            Security configuration dictionary
        """
        return self.get("security", {})
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences configuration.
        
        Returns:
            User preferences configuration dictionary
        """
        return self.get("notifications.user_preferences", {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature: Feature name (e.g., "whatsapp", "fact_check")
            
        Returns:
            True if feature is enabled, False otherwise
        """
        if feature == "whatsapp":
            return self.get("notifications.whatsapp.enabled", False)
        elif feature == "fact_check":
            return self.get("validation.fact_check_enabled", False)
        elif feature == "cross_reference":
            return self.get("validation.cross_reference_threshold", 0) > 0
        else:
            return self.get(f"features.{feature}.enabled", False)
    
    def reload(self):
        """Reload configuration from files."""
        self._load_config()
        logger.info("Configuration reloaded")
    
    def validate(self) -> bool:
        """Validate the configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_keys = [
            "news_sources.sources",
            "apis.openai",
            "apis.twilio"
        ]
        
        for key in required_keys:
            if not self.get(key):
                logger.error(f"Missing required configuration: {key}")
                return False
        
        return True


# Global configuration instance
config = ConfigManager() 
"""
Configuration Loader
Loads and provides access to PR-Reviewer configuration from config.yml
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Singleton class for loading and accessing configuration"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """Load configuration from config.yml"""
        config_path = Path(__file__).parent.parent / "config.yml"

        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}. Using defaults.")
            self._config = self._get_default_config()
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}. Using defaults.")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "code_analysis": {
                "tools": ["pylint", "flake8", "mypy"],
                "severity_threshold": "medium"
            },
            "architecture": {
                "max_cyclomatic_complexity": 10,
                "max_cognitive_complexity": 15
            }
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Dot-separated path (e.g., "code_analysis.tools")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_code_analysis_tools(self) -> list:
        """Get list of code analysis tools from config"""
        return self.get("code_analysis.tools", [])

    def get_architecture_config(self) -> Dict[str, Any]:
        """Get architecture analysis configuration"""
        return self.get("architecture", {})

    def get_max_cyclomatic_complexity(self) -> int:
        """Get maximum cyclomatic complexity threshold"""
        return self.get("architecture.max_cyclomatic_complexity", 10)

    def get_max_cognitive_complexity(self) -> int:
        """Get maximum cognitive complexity threshold"""
        return self.get("architecture.max_cognitive_complexity", 15)

    def reload(self):
        """Reload configuration from file"""
        self._config = None
        self._load_config()


# Global instance
config = ConfigLoader()

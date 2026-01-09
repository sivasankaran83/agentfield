"""
Tool Checker Utility
Checks if required analysis tools are installed on the system
Reads configuration from config.yml and supports auto-installation
"""

import subprocess
import logging
from typing import Dict, List, Optional
import shutil

logger = logging.getLogger(__name__)


class ToolChecker:
    """Utility to check if analysis tools are installed"""

    # Cache for tool availability
    _cache: Dict[str, bool] = {}

    # Cache for config data to avoid repeated file reads
    _config_cache: Optional[Dict] = None

    # Mapping of file extensions to language names
    EXT_TO_LANG = {
        '.py': 'python',
        '.go': 'go',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.rb': 'ruby',
        '.php': 'php',
        '.cs': 'csharp',
        '.cpp': 'cpp',
        '.c': 'c',
    }

    @classmethod
    def _load_config(cls) -> Dict:
        """
        Load complexity tools configuration from config.yml

        Returns:
            Dictionary containing complexity_tools configuration
        """
        if cls._config_cache is not None:
            return cls._config_cache

        try:
            from utils.config_loader import config
            cls._config_cache = config.get("complexity_tools", {})
            logger.debug("Loaded complexity tools configuration from config.yml")
        except Exception as e:
            logger.error(f"Failed to load complexity tools config: {e}")
            cls._config_cache = {}

        return cls._config_cache

    @classmethod
    def _get_tools_for_extension(cls, file_extension: str) -> List[str]:
        """
        Get list of configured tools for a file extension

        Args:
            file_extension: File extension (e.g., '.py', '.go')

        Returns:
            List of tool names configured for this extension
        """
        language = cls.EXT_TO_LANG.get(file_extension)
        if not language:
            return []

        config_data = cls._load_config()
        lang_config = config_data.get(language, {})
        return lang_config.get("tools", [])

    @classmethod
    def is_tool_installed(cls, tool_name: str) -> bool:
        """
        Check if a tool is installed and accessible

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is installed, False otherwise
        """
        # Check cache first
        if tool_name in cls._cache:
            return cls._cache[tool_name]

        # Check using shutil.which (cross-platform)
        tool_path = shutil.which(tool_name)
        is_installed = tool_path is not None

        if not is_installed:
            # Try running the tool with --version
            try:
                result = subprocess.run(
                    [tool_name, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                is_installed = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                is_installed = False

        # Cache result
        cls._cache[tool_name] = is_installed

        if not is_installed:
            logger.warning(f"Tool '{tool_name}' is not installed or not in PATH")

        return is_installed

    @classmethod
    def install_tool(cls, tool_name: str, language: str) -> bool:
        """
        Auto-install a tool if auto_install is enabled in config

        Args:
            tool_name: Name of the tool to install
            language: Language name (python, go, javascript, etc.)

        Returns:
            True if installation succeeded, False otherwise
        """
        config_data = cls._load_config()

        # Check if auto-install is enabled
        if not config_data.get("auto_install", False):
            logger.info(f"Auto-install is disabled. Tool '{tool_name}' not installed.")
            return False

        # Get install command for this tool
        lang_config = config_data.get(language, {})
        install_commands = lang_config.get("install_commands", {})
        install_cmd = install_commands.get(tool_name)

        if not install_cmd:
            logger.warning(f"No install command found for '{tool_name}' in language '{language}'")
            return False

        # Execute installation command
        logger.info(f"Auto-installing tool '{tool_name}' using: {install_cmd}")
        try:
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for installation
            )

            if result.returncode == 0:
                logger.info(f"Successfully installed '{tool_name}'")
                # Update cache to reflect successful installation
                cls._cache[tool_name] = True
                return True
            else:
                logger.error(f"Failed to install '{tool_name}': {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Installation of '{tool_name}' timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Error installing '{tool_name}': {e}")
            return False

    @classmethod
    def get_available_tools_for_extension(cls, file_extension: str, auto_install: bool = False) -> List[str]:
        """
        Get list of available complexity analysis tools for a file extension

        Args:
            file_extension: File extension (e.g., '.py', '.go')
            auto_install: If True, attempt to auto-install missing tools

        Returns:
            List of available tool names
        """
        potential_tools = cls._get_tools_for_extension(file_extension)
        if not potential_tools:
            return []

        available_tools = []
        language = cls.EXT_TO_LANG.get(file_extension)

        for tool in potential_tools:
            if cls.is_tool_installed(tool):
                available_tools.append(tool)
            elif auto_install and language:
                # Try to auto-install if enabled
                if cls.install_tool(tool, language):
                    available_tools.append(tool)

        return available_tools

    @classmethod
    def get_first_available_tool(cls, file_extension: str, auto_install: bool = False) -> Optional[str]:
        """
        Get the first available tool for a file extension

        Args:
            file_extension: File extension (e.g., '.py', '.go')
            auto_install: If True, attempt to auto-install missing tools

        Returns:
            Name of first available tool or None
        """
        potential_tools = cls._get_tools_for_extension(file_extension)
        if not potential_tools:
            return None

        language = cls.EXT_TO_LANG.get(file_extension)

        # Check each tool in order
        for tool in potential_tools:
            if cls.is_tool_installed(tool):
                return tool
            elif auto_install and language:
                # Try to auto-install if enabled
                if cls.install_tool(tool, language):
                    return tool

        return None

    @classmethod
    def clear_cache(cls):
        """Clear the tool availability cache and config cache"""
        cls._cache.clear()
        cls._config_cache = None

    @classmethod
    def check_all_tools(cls) -> Dict[str, bool]:
        """
        Check availability of all known tools from config

        Returns:
            Dictionary mapping tool names to availability status
        """
        all_tools = set()
        config_data = cls._load_config()

        # Collect all tools from all languages
        for language, lang_config in config_data.items():
            if language == "auto_install":
                continue
            if isinstance(lang_config, dict) and "tools" in lang_config:
                all_tools.update(lang_config["tools"])

        return {tool: cls.is_tool_installed(tool) for tool in all_tools}

    @classmethod
    def get_tool_install_command(cls, tool_name: str, language: Optional[str] = None) -> str:
        """
        Get installation command suggestion for a tool from config

        Args:
            tool_name: Name of the tool
            language: Optional language name to search within

        Returns:
            Suggested installation command
        """
        config_data = cls._load_config()

        # If language is provided, search within that language's config
        if language:
            lang_config = config_data.get(language, {})
            install_commands = lang_config.get("install_commands", {})
            if tool_name in install_commands:
                return install_commands[tool_name]

        # Otherwise, search all languages for this tool
        for lang, lang_config in config_data.items():
            if lang == "auto_install":
                continue
            if isinstance(lang_config, dict):
                install_commands = lang_config.get("install_commands", {})
                if tool_name in install_commands:
                    return install_commands[tool_name]

        return f"Install {tool_name} manually (no install command found in config)"

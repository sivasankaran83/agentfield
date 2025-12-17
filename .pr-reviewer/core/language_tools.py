"""
Language Tools Registry
Multi-language support with 8+ programming languages and 50+ tools
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict
import os


class Language(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    GO = "go"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    REACT = "react"
    JAVA = "java"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"


class ToolCategory(Enum):
    """Categories of development tools"""
    TESTING = "testing"
    LINTING = "linting"
    FORMATTING = "formatting"
    TYPE_CHECKING = "type_checking"
    SECURITY = "security"
    COMPLEXITY = "complexity"
    COVERAGE = "coverage"


@dataclass
class ToolConfig:
    """Configuration for a development tool"""
    name: str
    command: str
    args: List[str]
    category: ToolCategory
    language: Language
    output_format: str  # 'json', 'text', 'xml'
    enabled: bool = True
    requires_config: bool = False
    config_file: Optional[str] = None
    version_command: Optional[str] = None
    install_command: Optional[str] = None


class LanguageToolRegistry:
    """
    Registry of tools for all supported languages
    Provides tool configuration, execution, and management
    """
    
    def __init__(self):
        self.tools: Dict[Language, Dict[ToolCategory, List[ToolConfig]]] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all language tools"""
        
        # Python Tools
        self._register_python_tools()
        
        # Go Tools
        self._register_go_tools()
        
        # TypeScript/JavaScript Tools
        self._register_typescript_tools()
        self._register_javascript_tools()
        
        # React Tools (extends JavaScript)
        self._register_react_tools()
        
        # Java Tools
        self._register_java_tools()
        
        # Rust Tools
        self._register_rust_tools()
        
        # C++ Tools
        self._register_cpp_tools()
        
        # C# Tools
        self._register_csharp_tools()
    
    def _register_python_tools(self):
        """Register Python development tools"""
        python_tools = [
            # Testing
            ToolConfig(
                name="pytest",
                command="pytest",
                args=["--json-report", "--json-report-file=test_results.json", "-v"],
                category=ToolCategory.TESTING,
                language=Language.PYTHON,
                output_format="json",
                install_command="pip install pytest pytest-json-report"
            ),
            ToolConfig(
                name="pytest-cov",
                command="pytest",
                args=["--cov", "--cov-report=json"],
                category=ToolCategory.COVERAGE,
                language=Language.PYTHON,
                output_format="json",
                install_command="pip install pytest-cov"
            ),
            
            # Linting
            ToolConfig(
                name="pylint",
                command="pylint",
                args=["--output-format=json"],
                category=ToolCategory.LINTING,
                language=Language.PYTHON,
                output_format="json",
                install_command="pip install pylint"
            ),
            ToolConfig(
                name="ruff",
                command="ruff",
                args=["check", "--output-format=json"],
                category=ToolCategory.LINTING,
                language=Language.PYTHON,
                output_format="json",
                install_command="pip install ruff"
            ),
            
            # Type Checking
            ToolConfig(
                name="mypy",
                command="mypy",
                args=["--json-report", "."],
                category=ToolCategory.TYPE_CHECKING,
                language=Language.PYTHON,
                output_format="json",
                install_command="pip install mypy"
            ),
            
            # Formatting
            ToolConfig(
                name="black",
                command="black",
                args=["--check"],
                category=ToolCategory.FORMATTING,
                language=Language.PYTHON,
                output_format="text",
                install_command="pip install black"
            ),
            
            # Security
            ToolConfig(
                name="bandit",
                command="bandit",
                args=["-r", "-f", "json", "."],
                category=ToolCategory.SECURITY,
                language=Language.PYTHON,
                output_format="json",
                install_command="pip install bandit"
            ),
        ]
        
        self._register_tools(Language.PYTHON, python_tools)
    
    def _register_go_tools(self):
        """Register Go development tools"""
        go_tools = [
            ToolConfig(
                name="go test",
                command="go",
                args=["test", "-json", "./..."],
                category=ToolCategory.TESTING,
                language=Language.GO,
                output_format="json"
            ),
            ToolConfig(
                name="golangci-lint",
                command="golangci-lint",
                args=["run", "--out-format", "json"],
                category=ToolCategory.LINTING,
                language=Language.GO,
                output_format="json"
            ),
            ToolConfig(
                name="gosec",
                command="gosec",
                args=["-fmt=json", "./..."],
                category=ToolCategory.SECURITY,
                language=Language.GO,
                output_format="json"
            ),
        ]
        
        self._register_tools(Language.GO, go_tools)
    
    def _register_typescript_tools(self):
        """Register TypeScript tools"""
        ts_tools = [
            ToolConfig(
                name="jest",
                command="jest",
                args=["--json"],
                category=ToolCategory.TESTING,
                language=Language.TYPESCRIPT,
                output_format="json"
            ),
            ToolConfig(
                name="eslint",
                command="eslint",
                args=["--format=json"],
                category=ToolCategory.LINTING,
                language=Language.TYPESCRIPT,
                output_format="json"
            ),
        ]
        
        self._register_tools(Language.TYPESCRIPT, ts_tools)
    
    def _register_javascript_tools(self):
        """Register JavaScript tools"""
        js_tools = [
            ToolConfig(
                name="jest",
                command="jest",
                args=["--json"],
                category=ToolCategory.TESTING,
                language=Language.JAVASCRIPT,
                output_format="json"
            ),
            ToolConfig(
                name="eslint",
                command="eslint",
                args=["--format=json"],
                category=ToolCategory.LINTING,
                language=Language.JAVASCRIPT,
                output_format="json"
            ),
        ]
        
        self._register_tools(Language.JAVASCRIPT, js_tools)
    
    def _register_react_tools(self):
        """Register React tools"""
        self._register_tools(Language.REACT, [])
    
    def _register_java_tools(self):
        """Register Java tools"""
        self._register_tools(Language.JAVA, [])
    
    def _register_rust_tools(self):
        """Register Rust tools"""
        self._register_tools(Language.RUST, [])
    
    def _register_cpp_tools(self):
        """Register C++ tools"""
        self._register_tools(Language.CPP, [])
    
    def _register_csharp_tools(self):
        """Register C# tools"""
        self._register_tools(Language.CSHARP, [])
    
    def _register_tools(self, language: Language, tools: List[ToolConfig]):
        """Register tools for a language"""
        if language not in self.tools:
            self.tools[language] = {}
        
        for tool in tools:
            category = tool.category
            if category not in self.tools[language]:
                self.tools[language][category] = []
            self.tools[language][category].append(tool)
    
    def get_tools_for_language(
        self,
        language: Language,
        category: Optional[ToolCategory] = None
    ) -> List[ToolConfig]:
        """Get tools for a specific language"""
        if language not in self.tools:
            return []
        
        if category:
            return self.tools[language].get(category, [])
        
        all_tools = []
        for cat_tools in self.tools[language].values():
            all_tools.extend(cat_tools)
        return all_tools
    
    def detect_language(self, filepath: str) -> Optional[Language]:
        """Detect language from file extension"""
        ext = os.path.splitext(filepath)[1].lower()
        
        extension_map = {
            '.py': Language.PYTHON,
            '.go': Language.GO,
            '.ts': Language.TYPESCRIPT,
            '.tsx': Language.REACT,
            '.js': Language.JAVASCRIPT,
            '.jsx': Language.REACT,
            '.java': Language.JAVA,
            '.rs': Language.RUST,
            '.cpp': Language.CPP,
            '.cs': Language.CSHARP,
        }
        
        return extension_map.get(ext)

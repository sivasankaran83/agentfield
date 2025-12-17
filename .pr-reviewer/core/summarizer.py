"""
Enhanced Multi-Language Summarizer
Combines language-specific tool execution with LLM-powered insights
"""

import subprocess
import json
from typing import Dict, List, Optional
from pathlib import Path

from core.language_tools import LanguageToolRegistry, Language, ToolCategory
from core.llm_summary import LLMSummaryGenerator


class EnhancedMultiLanguageSummarizer:
    """
    Enhanced PR summarizer that combines:
    - Multi-language tool execution (tests, linting, security)
    - LLM-powered analysis and insights
    - Comprehensive reporting
    """
    
    def __init__(self):
        """Initialize with tool registry and LLM generator"""
        self.tool_registry = LanguageToolRegistry()
        self.llm_generator = LLMSummaryGenerator()
    
    def get_changed_files(self, base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
        """
        Get list of changed files between branches
        
        Args:
            base_branch: Base branch
            head_branch: Head branch
            
        Returns:
            List of changed file paths
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_branch}...{head_branch}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            return files
        
        except Exception as e:
            print(f"Error getting changed files: {e}")
            return []
    
    def detect_languages(self, files: List[str]) -> Dict[str, List[str]]:
        """
        Detect languages used in changed files
        
        Args:
            files: List of file paths
            
        Returns:
            Dictionary mapping language name to list of files
        """
        language_files = {}
        
        for file in files:
            language = self.tool_registry.detect_language(file)
            if language:
                lang_name = language.value
                if lang_name not in language_files:
                    language_files[lang_name] = []
                language_files[lang_name].append(file)
        
        return language_files
    
    def run_tests(self, language: Language, files: List[str]) -> Dict:
        """
        Run tests for a specific language
        
        Args:
            language: Programming language
            files: Files to test
            
        Returns:
            Test results
        """
        tools = self.tool_registry.get_tools_for_language(language, ToolCategory.TESTING)
        
        if not tools:
            return {"status": "no_test_tools", "language": language.value}
        
        # Use first available test tool
        tool = tools[0]
        
        try:
            # Build command
            cmd = [tool.command] + tool.args
            
            # Run command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd="."
            )
            
            # Parse output
            if tool.output_format == "json" and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return {
                        "status": "success",
                        "tool": tool.name,
                        "data": data,
                        "summary": self._parse_test_results(data, language)
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "status": "completed",
                "tool": tool.name,
                "return_code": result.returncode,
                "stdout": result.stdout[:1000],  # Limit output
                "stderr": result.stderr[:1000]
            }
        
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "tool": tool.name}
        except Exception as e:
            return {"status": "error", "tool": tool.name, "error": str(e)}
    
    def run_linting(self, language: Language, files: List[str]) -> Dict:
        """
        Run linting for a specific language
        
        Args:
            language: Programming language
            files: Files to lint
            
        Returns:
            Linting results
        """
        tools = self.tool_registry.get_tools_for_language(language, ToolCategory.LINTING)
        
        if not tools:
            return {"status": "no_lint_tools", "language": language.value}
        
        tool = tools[0]
        
        try:
            cmd = [tool.command] + tool.args + files
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd="."
            )
            
            if tool.output_format == "json" and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return {
                        "status": "success",
                        "tool": tool.name,
                        "data": data,
                        "summary": self._parse_lint_results(data, language)
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "status": "completed",
                "tool": tool.name,
                "return_code": result.returncode,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:1000]
            }
        
        except Exception as e:
            return {"status": "error", "tool": tool.name, "error": str(e)}
    
    def run_security_scan(self, language: Language, files: List[str]) -> Dict:
        """
        Run security scan for a specific language
        
        Args:
            language: Programming language
            files: Files to scan
            
        Returns:
            Security scan results
        """
        tools = self.tool_registry.get_tools_for_language(language, ToolCategory.SECURITY)
        
        if not tools:
            return {"status": "no_security_tools", "language": language.value}
        
        tool = tools[0]
        
        try:
            cmd = [tool.command] + tool.args
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd="."
            )
            
            if tool.output_format == "json" and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return {
                        "status": "success",
                        "tool": tool.name,
                        "data": data,
                        "summary": self._parse_security_results(data, language)
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "status": "completed",
                "tool": tool.name,
                "return_code": result.returncode,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:1000]
            }
        
        except Exception as e:
            return {"status": "error", "tool": tool.name, "error": str(e)}
    
    def _parse_test_results(self, data: Dict, language: Language) -> Dict:
        """Parse test results into standardized format"""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failures": []
        }
        
        # Python pytest format
        if language == Language.PYTHON and "summary" in data:
            summary.update({
                "total_tests": data["summary"].get("total", 0),
                "passed": data["summary"].get("passed", 0),
                "failed": data["summary"].get("failed", 0)
            })
        
        return summary
    
    def _parse_lint_results(self, data: Dict, language: Language) -> Dict:
        """Parse linting results into standardized format"""
        summary = {
            "total_issues": 0,
            "by_severity": {
                "error": 0,
                "warning": 0,
                "info": 0
            },
            "issues": []
        }
        
        if isinstance(data, list):
            summary["total_issues"] = len(data)
            for item in data[:10]:  # Limit to first 10
                summary["issues"].append({
                    "file": item.get("path", "unknown"),
                    "line": item.get("line", 0),
                    "message": item.get("message", ""),
                    "severity": item.get("type", "warning")
                })
        
        return summary
    
    def _parse_security_results(self, data: Dict, language: Language) -> Dict:
        """Parse security results into standardized format"""
        summary = {
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "issues": []
        }
        
        # Python bandit format
        if language == Language.PYTHON and "results" in data:
            issues = data["results"]
            summary["total_issues"] = len(issues)
            
            for issue in issues[:10]:
                severity = issue.get("issue_severity", "MEDIUM")
                if severity == "CRITICAL":
                    summary["critical_issues"] += 1
                elif severity == "HIGH":
                    summary["high_issues"] += 1
                
                summary["issues"].append({
                    "file": issue.get("filename", ""),
                    "line": issue.get("line_number", 0),
                    "message": issue.get("issue_text", ""),
                    "severity": severity
                })
        
        return summary
    
    def generate_comprehensive_summary(
        self,
        base_branch: str = "main",
        head_branch: str = "HEAD"
    ) -> Dict:
        """
        Generate comprehensive PR summary
        
        Combines:
        - Changed files detection
        - Language detection
        - Tool execution (tests, linting, security)
        - LLM analysis
        
        Args:
            base_branch: Base branch
            head_branch: Head branch
            
        Returns:
            Complete summary dictionary
        """
        
        # Get changed files
        changed_files = self.get_changed_files(base_branch, head_branch)
        
        if not changed_files:
            return {
                "status": "no_changes",
                "message": "No files changed"
            }
        
        # Detect languages
        language_files = self.detect_languages(changed_files)
        
        # Run analysis for each language
        language_analysis = {}
        
        for lang_str, files in language_files.items():
            try:
                language = Language(lang_str)
                
                print(f"Analyzing {lang_str} files...")
                
                language_analysis[lang_str] = {
                    "files": files,
                    "test_results": self.run_tests(language, files),
                    "linting_results": self.run_linting(language, files),
                    "security_results": self.run_security_scan(language, files)
                }
            
            except Exception as e:
                print(f"Error analyzing {lang_str}: {e}")
                language_analysis[lang_str] = {
                    "error": str(e)
                }
        
        # Generate LLM summary
        print("Generating LLM summary...")
        llm_summary = self.llm_generator.generate_comprehensive_summary(
            base_branch,
            head_branch
        )
        
        # Compile complete summary
        complete_summary = {
            "status": "success",
            "metadata": {
                "base_branch": base_branch,
                "head_branch": head_branch,
                "total_files_changed": len(changed_files),
                "languages_detected": list(language_files.keys()),
                "changed_files": changed_files
            },
            "language_analysis": language_analysis,
            "llm_summary": llm_summary
        }
        
        return complete_summary

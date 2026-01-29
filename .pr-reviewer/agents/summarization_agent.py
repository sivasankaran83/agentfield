"""
Summarization Agent - Enhanced with Architectural Analysis
Analyzes PR changes using multi-language tools, LLM, and architectural design principles
"""

# Apply nest_asyncio to handle nested event loops in CI environments
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

from agentfield import AIConfig, Agent
from typing import Dict, List, Optional
import os
import json
import subprocess
import sys
from pathlib import Path

from utils.git_utils import GitUtils

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import (
    AnalysisPlan,
    ArchitecturalAnalysis,
    ComprehensiveInsights
)
from utils.llm_sanitizer import sanitize_llm_output

# Initialize Summarization Agent with AgentField
app = Agent(
    node_id="pr-reviewer-summarizer",
    agentfield_url=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
    ai_config=AIConfig(
        model=os.getenv("AI_MODEL", "openrouter/anthropic/claude-sonnet-4.5"),
        api_key=os.getenv("OPENROUTER_API_KEY"),  # or set OPENAI_API_KEY env var
    )
)


@app.skill()
async def get_changed_files(base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
    """
    Get list of changed files between branches

    Args:
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)

    Returns:
        List of changed file paths
    """
    git_utils = GitUtils()
    return await git_utils.get_changed_files_async(base_branch, head_branch)


@app.skill()
def detect_languages(changed_files: List[str]) -> Dict[str, List[str]]:
    """
    Detect programming languages in changed files
    
    Args:
        changed_files: List of file paths
        
    Returns:
        Dictionary mapping language to list of files
    """
    from core.language_tools import LanguageToolRegistry
    
    registry = LanguageToolRegistry()
    language_files = {}
    
    for file_path in changed_files:
        language = registry.detect_language(file_path)
        if language:
            lang_name = language.value
            if lang_name not in language_files:
                language_files[lang_name] = []
            language_files[lang_name].append(file_path)
    
    return language_files


@app.skill()
def analyze_file_structure(files: List[str]) -> Dict:
    """
    Analyze file and directory structure for architectural patterns
    
    Args:
        files: List of file paths
        
    Returns:
        Structure analysis including patterns detected
    """
    structure = {
        "total_files": len(files),
        "by_type": {},
        "directories": set(),
        "depth_analysis": {},
        "patterns_detected": []
    }
    
    for file in files:
        # Extract directory
        parts = file.split('/')
        if len(parts) > 1:
            structure["directories"].add('/'.join(parts[:-1]))
        
        # Count depth
        depth = len(parts) - 1
        structure["depth_analysis"][depth] = structure["depth_analysis"].get(depth, 0) + 1
        
        # Categorize by type
        if '.' in file:
            ext = file.split('.')[-1]
            structure["by_type"][ext] = structure["by_type"].get(ext, 0) + 1
        
        # Detect common patterns
        if 'test' in file.lower() or 'spec' in file.lower():
            structure["patterns_detected"].append("test_files")
        if 'controller' in file.lower():
            structure["patterns_detected"].append("mvc_pattern")
        if 'service' in file.lower():
            structure["patterns_detected"].append("service_layer")
        if 'repository' in file.lower() or 'dao' in file.lower():
            structure["patterns_detected"].append("repository_pattern")
        if 'factory' in file.lower():
            structure["patterns_detected"].append("factory_pattern")
        if 'interface' in file.lower() or file.endswith('Interface.py'):
            structure["patterns_detected"].append("interface_segregation")
    
    structure["directories"] = list(structure["directories"])
    structure["patterns_detected"] = list(set(structure["patterns_detected"]))
    
    return structure


@app.skill()
def analyze_code_complexity(file_path: str) -> Dict:
    """
    Analyze code complexity metrics for a file using configured tools

    Args:
        file_path: Path to file

    Returns:
        Complexity metrics
    """
    import logging
    from utils.tool_checker import ToolChecker
    from utils.config_loader import config

    logger = logging.getLogger(__name__)

    # Get file extension
    file_extension = Path(file_path).suffix

    if not file_extension:
        return {"status": "no_extension", "message": "File has no extension"}

    # Get configured complexity threshold
    max_complexity = config.get_max_cyclomatic_complexity()

    try:
        # Get available tool for this file type with auto-install
        # The auto_install flag in config.yml controls whether tools will be automatically installed
        available_tool = ToolChecker.get_first_available_tool(file_extension, auto_install=True)

        if not available_tool:
            # Get language name and potential tools
            language = ToolChecker.EXT_TO_LANG.get(file_extension)
            potential_tools = ToolChecker._get_tools_for_extension(file_extension)

            logger.error(
                f"No complexity analysis tool installed for {file_extension} files. "
                f"Supported tools: {potential_tools}"
            )

            # Get installation suggestions
            install_commands = [
                ToolChecker.get_tool_install_command(tool, language)
                for tool in potential_tools
            ]

            return {
                "status": "tool_not_installed",
                "file_type": file_extension,
                "message": f"No complexity analysis tool found for {file_extension} files",
                "suggested_tools": potential_tools,
                "install_commands": install_commands
            }

        # Run analysis with the available tool
        result = None

        if available_tool == 'radon' and file_extension == '.py':
            # Python with radon
            result = subprocess.run(
                ['radon', 'cc', '-j', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                complexity_data = json.loads(result.stdout)
                return {
                    "status": "success",
                    "tool": "radon",
                    "file": file_path,
                    "complexity_data": complexity_data,
                    "threshold": max_complexity,
                    "violations": _check_complexity_violations(complexity_data, max_complexity)
                }

        elif available_tool == 'gocyclo' and file_extension == '.go':
            # Go with gocyclo
            result = subprocess.run(
                ['gocyclo', '-avg', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return {
                    "status": "success",
                    "tool": "gocyclo",
                    "file": file_path,
                    "average_complexity": result.stdout.strip(),
                    "threshold": max_complexity
                }

        elif available_tool == 'eslint' and file_extension in ['.js', '.ts']:
            # JavaScript/TypeScript with eslint
            result = subprocess.run(
                ['eslint', '--format', 'json', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.stdout:
                eslint_data = json.loads(result.stdout)
                return {
                    "status": "success",
                    "tool": "eslint",
                    "file": file_path,
                    "complexity_data": eslint_data,
                    "threshold": max_complexity
                }

        elif available_tool == 'lizard' and file_extension in ['.cpp', '.c']:
            # C/C++ with lizard
            result = subprocess.run(
                ['lizard', '-l', 'cpp', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return {
                    "status": "success",
                    "tool": "lizard",
                    "file": file_path,
                    "complexity_output": result.stdout,
                    "threshold": max_complexity
                }

        # If we got here, tool ran but produced unexpected output
        if result:
            logger.warning(
                f"Tool '{available_tool}' completed but output format was unexpected. "
                f"Return code: {result.returncode}, stderr: {result.stderr[:200]}"
            )
            return {
                "status": "tool_error",
                "tool": available_tool,
                "file": file_path,
                "error": f"Tool completed with return code {result.returncode}",
                "stderr": result.stderr[:500] if result.stderr else None
            }

        return {
            "status": "unsupported_language",
            "file_type": file_extension,
            "available_tool": available_tool
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Complexity analysis timed out for {file_path}")
        return {
            "status": "timeout",
            "file": file_path,
            "message": "Analysis took too long (>30s)"
        }

    except Exception as e:
        logger.error(f"Error analyzing complexity for {file_path}: {e}")
        return {
            "status": "error",
            "file": file_path,
            "error": str(e)
        }


def _check_complexity_violations(complexity_data: Dict, threshold: int) -> List[Dict]:
    """
    Check for complexity violations in radon output

    Args:
        complexity_data: Radon complexity data
        threshold: Maximum allowed complexity

    Returns:
        List of violations
    """
    violations = []

    # Radon format: {file_path: [{"complexity": N, "name": "func", ...}]}
    for file_path, functions in complexity_data.items():
        if not isinstance(functions, list):
            continue

        for func in functions:
            complexity = func.get('complexity', 0)
            if complexity > threshold:
                violations.append({
                    "file": file_path,
                    "function": func.get('name', 'unknown'),
                    "complexity": complexity,
                    "threshold": threshold,
                    "line": func.get('lineno', 0)
                })

    return violations


@app.skill()
def run_language_analysis(language: str, files: List[str]) -> Dict:
    """
    Run complete analysis for a specific language
    
    Args:
        language: Programming language name
        files: List of files to analyze
        
    Returns:
        Analysis results dictionary
    """
    from core.language_tools import LanguageToolRegistry, Language, ToolCategory
    import subprocess
    
    registry = LanguageToolRegistry()
    
    try:
        lang_enum = Language(language)
    except ValueError:
        return {"error": f"Unsupported language: {language}"}
    
    results = {
        "language": language,
        "test_results": {},
        "linting_results": {},
        "security_results": {},
        "complexity_results": {}
    }
    
    # Run tests
    test_tools = registry.get_tools_for_language(lang_enum, ToolCategory.TESTING)
    for tool in test_tools:
        try:
            cmd = [tool.command] + tool.args + files
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if tool.output_format == 'json' and process.stdout:
                parsed = json.loads(process.stdout)
                results['test_results'] = parsed
        except Exception as e:
            results['test_results']['error'] = str(e)
    
    # Run linting
    linting_tools = registry.get_tools_for_language(lang_enum, ToolCategory.LINTING)
    for tool in linting_tools:
        try:
            cmd = [tool.command] + tool.args + files
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if tool.output_format == 'json' and process.stdout:
                parsed = json.loads(process.stdout)
                results['linting_results'] = parsed
        except Exception as e:
            results['linting_results']['error'] = str(e)
    
    # Run security scan
    security_tools = registry.get_tools_for_language(lang_enum, ToolCategory.SECURITY)
    for tool in security_tools:
        try:
            cmd = [tool.command] + tool.args + files
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if tool.output_format == 'json' and process.stdout:
                parsed = json.loads(process.stdout)
                results['security_results'] = parsed
        except Exception as e:
            results['security_results']['error'] = str(e)
    
    # Analyze complexity for each file
    complexity_analyses = []
    for file in files[:10]:  # Limit to first 10 files
        complexity = analyze_code_complexity(file)
        if complexity:
            complexity_analyses.append({
                "file": file,
                "complexity": complexity
            })
    results['complexity_results'] = complexity_analyses
    
    return results


@app.skill()
async def get_git_diff(base_branch: str = "main", head_branch: str = "HEAD") -> str:
    """
    Get git diff between branches

    Args:
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)

    Returns:
        Git diff output
    """
    git_utils = GitUtils()
    return await git_utils.get_git_diff_async(base_branch, head_branch)


@app.skill()
async def get_commit_messages(base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
    """
    Get commit messages in the PR

    Args:
        base_branch: Base branch
        head_branch: Head branch

    Returns:
        List of commit messages
    """
    git_utils = GitUtils()
    return await git_utils.get_commit_messages_async(base_branch, head_branch)


@app.skill()
def get_changed_file_stats(base_branch: str = "main", head_branch: str = "HEAD") -> str:
    """
    Get statistics about changed files

    Args:
        base_branch: Base branch
        head_branch: Head branch

    Returns:
        File statistics
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", f"{base_branch}...{head_branch}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"Error getting file stats: {e}"


@app.reasoner()
async def generate_comprehensive_summary(
    base_branch: str = "main",
    head_branch: str = "HEAD",
    max_diff_length: int = 10000
) -> Dict:
    """
    Generate comprehensive PR summary using AI

    Args:
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)
        max_diff_length: Maximum length of diff to analyze

    Returns:
        Comprehensive summary dictionary
    """

    # Get git information
    git_diff = await get_git_diff(base_branch, head_branch)
    commit_messages = await get_commit_messages(base_branch, head_branch)
    file_stats = get_changed_file_stats(base_branch, head_branch)

    # Truncate diff if too long
    if len(git_diff) > max_diff_length:
        git_diff = git_diff[:max_diff_length] + "\n\n... (truncated)"

    # Create prompt for AI
    prompt = f"""
Analyze this Pull Request and provide a comprehensive summary.

COMMIT MESSAGES:
{json.dumps(commit_messages, indent=2)}

FILE STATISTICS:
{file_stats}

GIT DIFF (changes made):
{git_diff}

Provide a comprehensive analysis in JSON format:

{{
    "executive_summary": "2-3 sentence high-level summary of what this PR does",

    "pr_type": "feature|bugfix|refactor|documentation|test|chore|hotfix",

    "risk_assessment": "low|medium|high|critical",

    "key_changes": [
        "Most important change 1",
        "Most important change 2",
        "Most important change 3"
    ],

    "files_affected": {{
        "added": ["list of new files"],
        "modified": ["list of modified files"],
        "deleted": ["list of deleted files"]
    }},

    "impact_analysis": {{
        "scope": "small|medium|large - how much of the codebase is affected",
        "complexity": "low|medium|high - how complex are the changes",
        "dependencies": "Are there external dependency changes?",
        "backwards_compatibility": "Does this maintain backwards compatibility?"
    }},

    "testing_requirements": [
        "What tests should be run",
        "What test coverage is needed",
        "Edge cases to test"
    ],

    "breaking_changes": [
        "List any breaking changes or empty array"
    ],

    "security_considerations": [
        "Any security implications",
        "Authentication/authorization changes",
        "Data handling changes"
    ],

    "recommendations": [
        "Suggestion 1 for reviewers",
        "Suggestion 2 for reviewers",
        "Areas requiring special attention"
    ],

    "estimated_review_time": "5m|15m|30m|1h|2h+ - estimated time to review",

    "confidence": "low|medium|high - confidence in this analysis"
}}

Focus on:
- What problem does this solve?
- How does it solve it?
- What are the risks?
- What should reviewers focus on?

Return ONLY valid JSON, no other text.
"""

    try:
        # Call app.ai for structured response
        response_raw = await app.ai(user=prompt)

        # Handle response - it might have a .text attribute or be a string
        if hasattr(response_raw, 'text'):
            content = response_raw.text
        else:
            content = str(response_raw)

        # Parse JSON
        try:
            summary = json.loads(content)
            return sanitize_llm_output(summary)
        except json.JSONDecodeError:
            # Try to extract JSON if wrapped in markdown
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
                summary = json.loads(content)
                return sanitize_llm_output(summary)
            else:
                raise

    except Exception as e:
        # Return error summary
        return {
            "executive_summary": f"Error generating LLM summary: {e}",
            "pr_type": "unknown",
            "risk_assessment": "unknown",
            "key_changes": [],
            "impact_analysis": {},
            "testing_requirements": [],
            "breaking_changes": [],
            "security_considerations": [],
            "recommendations": [],
            "estimated_review_time": "unknown",
            "confidence": "low",
            "error": str(e)
        }


@app.reasoner()
async def generate_quick_summary(commit_messages: List[str]) -> str:
    """
    Generate a quick one-line summary from commit messages

    Args:
        commit_messages: List of commit messages

    Returns:
        Quick summary string
    """
    try:
        prompt = f"""
Summarize these commit messages in ONE sentence:

{json.dumps(commit_messages, indent=2)}

Return ONLY the summary sentence, nothing else.
"""

        response_raw = await app.ai(user=prompt)

        # Handle response - it might have a .text attribute or be a string
        if hasattr(response_raw, 'text'):
            summary = response_raw.text.strip()
        else:
            summary = str(response_raw).strip()

        return sanitize_llm_output(summary)

    except Exception as e:
        return f"Multiple commits: {len(commit_messages)} changes"


@app.reasoner()
async def analyze_code_quality(code_snippet: str, language: str) -> Dict:
    """
    Analyze code quality of a specific snippet

    Args:
        code_snippet: Code to analyze
        language: Programming language

    Returns:
        Quality analysis
    """
    try:
        prompt = f"""
Analyze this {language} code for quality:

```{language}
{code_snippet}
```

Provide analysis in JSON:
{{
    "readability": "excellent|good|fair|poor",
    "maintainability": "excellent|good|fair|poor",
    "issues": ["list specific issues"],
    "suggestions": ["list improvements"],
    "complexity": "low|medium|high"
}}

Return ONLY valid JSON.
"""

        response_raw = await app.ai(user=prompt)

        # Handle response - it might have a .text attribute or be a string
        if hasattr(response_raw, 'text'):
            content = response_raw.text
        else:
            content = str(response_raw)

        analysis = json.loads(content)
        return sanitize_llm_output(analysis)

    except Exception as e:
        return {
            "readability": "unknown",
            "maintainability": "unknown",
            "issues": [str(e)],
            "suggestions": [],
            "complexity": "unknown"
        }


@app.skill()
def generate_llm_summary(base_branch: str = "main", head_branch: str = "HEAD") -> Dict:
    """
    Generate LLM-powered summary (synchronous wrapper)

    This is a synchronous wrapper that calls the async generate_comprehensive_summary.
    Used for backward compatibility with existing code.

    Args:
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)

    Returns:
        LLM-generated summary
    """
    import asyncio

    # Get the event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the async function
    return loop.run_until_complete(generate_comprehensive_summary(base_branch, head_branch))


@app.skill()
def get_code_for_analysis(files: List[str], max_files: int = 20) -> Dict[str, str]:
    """
    Extract code content from files for architectural analysis
    
    Args:
        files: List of file paths
        max_files: Maximum number of files to read
        
    Returns:
        Dictionary mapping file paths to their content
    """
    code_contents = {}
    
    for file in files[:max_files]:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Limit content size to avoid token limits
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (truncated)"
                code_contents[file] = content
        except Exception as e:
            code_contents[file] = f"Error reading file: {e}"
    
    return code_contents


@app.reasoner()
async def analyze_architectural_design(
    changed_files: List[str],
    language_files: Dict[str, List[str]],
    code_contents: Dict[str, str]
) -> Dict:
    """
    Comprehensive architectural design analysis
    
    Analyzes:
    - SOLID principles adherence
    - Design patterns (good and anti-patterns)
    - Code organization and structure
    - Coupling and cohesion
    - Dependency management
    - Testability
    - Maintainability concerns
    
    Args:
        changed_files: List of changed files
        language_files: Files grouped by language
        code_contents: File contents for analysis
        
    Returns:
        Comprehensive architectural analysis
    """
    
    # Analyze file structure first
    structure_analysis = analyze_file_structure(changed_files)
    
    # Use AI for deep architectural analysis
    architectural_prompt = f"""
    Perform a comprehensive architectural design analysis of this PR.
    
    Files Changed: {len(changed_files)}
    Languages: {list(language_files.keys())}
    
    File Structure:
    {json.dumps(structure_analysis, indent=2)}
    
    Sample Code (top 5 files):
    {json.dumps({k: code_contents[k] for k in list(code_contents.keys())[:5]}, indent=2)}
    
    Analyze the following architectural aspects:
    
    1. **SOLID PRINCIPLES ADHERENCE**:
       - Single Responsibility Principle (SRP): Are classes/functions doing one thing?
       - Open/Closed Principle (OCP): Is code open for extension, closed for modification?
       - Liskov Substitution Principle (LSP): Are abstractions properly used?
       - Interface Segregation Principle (ISP): Are interfaces focused and minimal?
       - Dependency Inversion Principle (DIP): Does code depend on abstractions?
       
       For each principle, rate: excellent|good|fair|poor
       Provide specific violations with file:line references.
    
    2. **DESIGN PATTERNS**:
       - Good patterns detected: Factory, Strategy, Repository, etc.
       - Pattern misuse: Where patterns are incorrectly applied
       - Missing patterns: Where patterns would help
    
    3. **ANTI-PATTERNS DETECTION**:
       - God Object/God Class: Classes doing too much
       - Spaghetti Code: Tangled control flow
       - Circular Dependencies: Files/modules depending on each other
       - Tight Coupling: Excessive dependencies between components
       - Magic Numbers/Strings: Hard-coded values without constants
       - Copy-Paste Programming: Duplicated code blocks
       - Premature Optimization: Complexity without proven need
       - Shotgun Surgery: Changes requiring modifications across many files
       - Feature Envy: Methods using other classes' data more than their own
       - Data Clumps: Same groups of data appearing together
    
    4. **CODE ORGANIZATION**:
       - Separation of Concerns: Are different aspects properly separated?
       - Layering: Is there clear architectural layering (presentation, business, data)?
       - Module Cohesion: Do related things group together?
       - File/Folder Structure: Is organization logical and scalable?
    
    5. **COUPLING & COHESION**:
       - Coupling Level: high|medium|low
       - Cohesion Level: high|medium|low
       - Specific coupling issues with examples
    
    6. **DEPENDENCY MANAGEMENT**:
       - Are dependencies properly injected or hard-coded?
       - Is there excessive use of singletons or global state?
       - Are there circular dependencies?
    
    7. **TESTABILITY**:
       - Test Coverage Indicators: Are new files covered by tests?
       - Testability Issues: Hard-to-test code patterns
       - Mock-ability: Can dependencies be easily mocked?
    
    8. **MAINTAINABILITY CONCERNS**:
       - Complexity Hotspots: Overly complex functions/classes
       - Documentation: Are complex parts documented?
       - Naming: Are names clear and consistent?
       - Code Duplication: Is code being repeated?
    
    Return as JSON:
    {{
        "solid_principles": {{
            "srp": {{"rating": "good", "violations": ["file:line - description"]}},
            "ocp": {{"rating": "fair", "violations": [...]}},
            "lsp": {{"rating": "good", "violations": []}},
            "isp": {{"rating": "excellent", "violations": []}},
            "dip": {{"rating": "poor", "violations": [...]}}
        }},
        "design_patterns": {{
            "good_patterns": ["Repository pattern in data layer", "Factory for object creation"],
            "pattern_misuse": ["Singleton overused in config.py"],
            "missing_patterns": ["Strategy pattern would help with payment methods"]
        }},
        "anti_patterns": {{
            "detected": [
                {{
                    "type": "God Object",
                    "severity": "high",
                    "location": "src/user_service.py:UserService",
                    "description": "UserService handles authentication, authorization, profile, and notifications",
                    "recommendation": "Split into AuthService, ProfileService, NotificationService"
                }}
            ],
            "count_by_severity": {{"critical": 0, "high": 2, "medium": 5, "low": 3}}
        }},
        "code_organization": {{
            "separation_of_concerns": "good",
            "layering": "fair - business logic mixed with presentation",
            "module_cohesion": "good",
            "structure_quality": "good"
        }},
        "coupling_cohesion": {{
            "coupling": "medium",
            "cohesion": "high",
            "issues": ["auth.py tightly coupled to user.py", "payment module depends on too many others"]
        }},
        "dependency_management": {{
            "injection_quality": "good",
            "singleton_overuse": true,
            "circular_dependencies": ["auth <-> user", "order <-> payment"],
            "global_state": ["config.py uses module-level globals"]
        }},
        "testability": {{
            "test_coverage_estimate": "~65%",
            "issues": ["UserService too complex to test", "Hard-coded database connections"],
            "mockability": "fair"
        }},
        "maintainability": {{
            "complexity_hotspots": ["process_payment() in payment.py - 45 lines, 8 branches"],
            "documentation_gaps": ["No docstrings in auth.py", "Complex algorithms undocumented"],
            "naming_issues": ["Variable 'x' in loop", "Function 'do_stuff' is vague"],
            "duplication": ["Error handling pattern repeated 15 times"]
        }},
        "overall_assessment": {{
            "architectural_quality": "good|fair|poor",
            "technical_debt_level": "low|medium|high",
            "refactoring_priority": "immediate|soon|eventual|none",
            "major_concerns": ["list of top 3-5 concerns"],
            "strengths": ["list of architectural strengths"]
        }},
        "recommendations": {{
            "immediate": ["Critical fixes needed now"],
            "short_term": ["Improvements for next sprint"],
            "long_term": ["Strategic refactoring suggestions"]
        }}
    }}
    
    Be specific with file names and line numbers where possible.
    Focus on actionable feedback.
    """

    # Use Pydantic schema for structured response
    architectural_analysis_raw = await app.ai(
        user=architectural_prompt,
        schema=ArchitecturalAnalysis
    )
    architectural_analysis = sanitize_llm_output(architectural_analysis_raw)

    return architectural_analysis


@app.reasoner()
async def analyze_pr(
    pr_number: Optional[int] = None,
    base_branch: str = "main",
    head_branch: str = "HEAD"
) -> Dict:
    """
    Main reasoning function: Analyzes PR with multi-language tools, LLM, and architectural analysis
    
    This reasoner:
    1. Gets changed files
    2. Detects languages
    3. Uses AI to create analysis plan
    4. Runs language-specific analysis (tests, linting, security)
    5. Analyzes code complexity
    6. Generates LLM summary
    7. **NEW: Performs comprehensive architectural design analysis**
    8. Combines all results with AI insights
    
    Args:
        pr_number: PR number (optional)
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)
        
    Returns:
        Comprehensive summary with LLM, language analysis, and architectural insights
    """
    
    print(f"Analyzing PR #{pr_number}: {base_branch}...{head_branch}")

    # Step 1: Get changed files
    changed_files = await get_changed_files(base_branch, head_branch)

    if not changed_files:
        return {
            "status": "error",
            "message": "No changed files found"
        }

    print(f"Found {len(changed_files)} changed files")

    # Step 2: Detect languages
    language_files = detect_languages(changed_files)
    
    print(f"Detected languages: {list(language_files.keys())}")
    
    # Step 3: Get code contents for architectural analysis
    code_contents = get_code_for_analysis(changed_files, max_files=20)
    
    # Step 4: Use AI to create analysis plan
    plan_prompt = f"""
    I need to analyze a Pull Request with the following changes:
    
    Changed files: {len(changed_files)}
    Languages detected: {list(language_files.keys())}
    
    For each language, we can run:
    - Tests
    - Linting
    - Security scans
    - Complexity analysis
    - Architectural design analysis (NEW)
    
    Create a prioritized analysis plan focusing on the most important checks first.
    Consider that we have limited time and should focus on high-impact analysis.

    Return a JSON object with:
    {{
        "priority_languages": ["list of languages to analyze first"],
        "analysis_types": ["tests", "linting", "security", "complexity", "architecture"],
        "skip_analysis": ["any analysis types to skip and why"],
        "focus_areas": ["specific areas to focus on"],
        "rationale": "why this order"
    }}
    """

    # Use Pydantic schema for structured response
    analysis_plan_raw = await app.ai(
        user=plan_prompt,
        schema=AnalysisPlan
    )
    analysis_plan = sanitize_llm_output(analysis_plan_raw)

    print(f"Analysis plan created: {analysis_plan.get('rationale', '')}")
    
    # Step 5: Run language-specific analysis
    language_results = {}
    
    for language, files in language_files.items():
        print(f"Analyzing {language} files...")
        language_results[language] = run_language_analysis(language, files)
    
    # Step 6: Generate LLM summary
    print("Generating LLM summary...")
    llm_summary = generate_llm_summary(base_branch, head_branch)
    
    # Step 7: NEW - Perform architectural design analysis
    print("Performing architectural design analysis...")
    architectural_analysis = await analyze_architectural_design(
        changed_files,
        language_files,
        code_contents
    )
    
    # Step 8: Use AI to analyze combined results and generate insights
    print("Generating comprehensive insights...")
    combined_analysis_prompt = f"""
    Analyze these comprehensive PR review results and provide actionable insights:
    
    LLM Summary:
    {json.dumps(llm_summary, indent=2)}
    
    Language Analysis Results:
    {json.dumps({k: {
        "tests": v.get('test_results', {}).get('summary', 'N/A'),
        "linting": v.get('linting_results', {}).get('summary', 'N/A'),
        "security": v.get('security_results', {}).get('summary', 'N/A')
    } for k, v in language_results.items()}, indent=2)}
    
    Architectural Analysis:
    {json.dumps(architectural_analysis, indent=2)}
    
    Provide:
    1. Overall assessment considering ALL aspects (functionality, quality, architecture)
    2. Top 5 priorities to address (including architectural issues)
    3. Risk level (low, medium, high, critical)
    4. Estimated effort to fix all issues
    5. Whether architectural concerns block merge
    
    Return as JSON:
    {{
        "assessment": "ready_to_merge|needs_work|critical_issues|architectural_refactoring_needed",
        "priorities": [
            {{"priority": 1, "category": "architecture|testing|security|quality", "issue": "...", "impact": "high|medium|low"}},
            ...
        ],
        "risk_level": "low|medium|high|critical",
        "estimated_effort_hours": "number",
        "blocking_issues": [
            {{"type": "architecture|security|functionality", "description": "...", "severity": "critical|high|medium|low"}}
        ],
        "architectural_concerns_block_merge": true|false,
        "recommendations": [
            "Immediate action 1",
            "Immediate action 2",
            "Long-term improvement 1"
        ],
        "strengths": ["What's good about this PR"],
        "summary": "2-3 sentence overall summary"
    }}
    """

    # Use Pydantic schema for structured response
    ai_insights_raw = await app.ai(
        user=combined_analysis_prompt,
        schema=ComprehensiveInsights
    )
    ai_insights = sanitize_llm_output(ai_insights_raw)

    # Step 9: Compile comprehensive summary
    comprehensive_summary = {
        "pr_number": pr_number,
        "metadata": {
            "base_branch": base_branch,
            "head_branch": head_branch,
            "total_files_changed": len(changed_files),
            "languages_detected": list(language_files.keys()),
            "analysis_timestamp": "2024-01-01T00:00:00Z"  # Add proper timestamp
        },
        "llm_summary": llm_summary,
        "language_analysis": language_results,
        "architectural_analysis": architectural_analysis,  # NEW
        "ai_insights": ai_insights,
        "analysis_plan": analysis_plan,
        "status": "success"
    }
    
    print("Analysis complete!")
    
    return comprehensive_summary


if __name__ == "__main__":
    # Run the agent - it will register with the control plane
    # and expose the analyze_pr reasoner as an endpoint
    print("Starting PR Reviewer Summarization Agent (Enhanced with Architectural Analysis)")
    print(f"Connecting to AgentField at {os.getenv('AGENTFIELD_SERVER', 'http://localhost:8080')}")
    app.run()

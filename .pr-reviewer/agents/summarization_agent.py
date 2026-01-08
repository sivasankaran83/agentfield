"""
Summarization Agent - Enhanced with Architectural Analysis
Analyzes PR changes using multi-language tools, LLM, and architectural design principles
"""

from agentfield import AIConfig, Agent
from typing import Dict, List, Optional
import os
import json
import subprocess
import sys
from pathlib import Path

from core.summarizer import EnhancedMultiLanguageSummarizer
from core.llm_summary import LLMSummaryGenerator
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
def get_changed_files(base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
    """
    Get list of changed files between branches
    
    Args:
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)
        
    Returns:
        List of changed file paths
    """
    git_utils = GitUtils()
    return git_utils.get_changed_files(base_branch, head_branch)


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
    Analyze code complexity metrics for a file
    
    Args:
        file_path: Path to file
        
    Returns:
        Complexity metrics
    """
    try:
        # Use different tools based on language
        if file_path.endswith('.py'):
            # Use radon for Python
            result = subprocess.run(
                ['radon', 'cc', '-j', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        
        elif file_path.endswith('.go'):
            # Use gocyclo for Go
            result = subprocess.run(
                ['gocyclo', '-avg', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return {"average_complexity": result.stdout.strip()}
        
        return {"status": "unsupported_language"}
    
    except Exception as e:
        return {"error": str(e)}


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
def generate_llm_summary(base_branch: str = "main", head_branch: str = "HEAD") -> Dict:
    """
    Generate LLM-powered summary using Claude API
    
    Args:
        base_branch: Base branch for comparison
        head_branch: Head branch (PR branch)
        
    Returns:
        LLM-generated summary
    """
    generator = LLMSummaryGenerator()
    return generator.generate_comprehensive_summary(base_branch, head_branch)


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
    changed_files = get_changed_files(base_branch, head_branch)
    
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

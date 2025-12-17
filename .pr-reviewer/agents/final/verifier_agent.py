"""
Verifier Agent - Final Production Version
Verifies that fixes are correct and complete with comprehensive checking
"""

from agentfield import Agent
from typing import Dict, List, Optional
import os
import subprocess
import json

# Initialize Verifier Agent
app = Agent(
    node_id="pr-reviewer-verifier",
    agentfield_url=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080")
)


@app.skill()
def run_tests(language: str, test_path: Optional[str] = None) -> Dict:
    """
    Run tests for a specific language
    
    Args:
        language: Programming language
        test_path: Specific path to test
        
    Returns:
        Test results
    """
    test_commands = {
        "python": "pytest --json-report --json-report-file=test_results.json -v",
        "go": "go test -json ./...",
        "typescript": "jest --json --outputFile=test_results.json",
        "javascript": "jest --json --outputFile=test_results.json",
        "rust": "cargo test --message-format=json"
    }
    
    command = test_commands.get(language.lower())
    if not command:
        return {"error": f"No test command for {language}"}
    
    if test_path:
        command += f" {test_path}"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        # Try to parse JSON output
        output_file = "test_results.json"
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                test_data = json.load(f)
            
            return {
                "success": result.returncode == 0,
                "data": test_data,
                "summary": _parse_test_summary(test_data, language)
            }
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except Exception as e:
        return {"error": str(e)}


def _parse_test_summary(data: Dict, language: str) -> Dict:
    """Parse test results into standardized format"""
    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    if language == "python" and "summary" in data:
        summary.update(data["summary"])
    elif language in ["typescript", "javascript"] and "numTotalTests" in data:
        summary["total"] = data.get("numTotalTests", 0)
        summary["passed"] = data.get("numPassedTests", 0)
        summary["failed"] = data.get("numFailedTests", 0)
    
    return summary


@app.skill()
def run_linting(language: str, files: Optional[List[str]] = None) -> Dict:
    """
    Run linting for a specific language
    
    Args:
        language: Programming language
        files: Specific files to lint
        
    Returns:
        Linting results
    """
    lint_commands = {
        "python": "pylint --output-format=json --disable=C0114,C0115,C0116",
        "go": "golangci-lint run --out-format json",
        "typescript": "eslint --format json",
        "javascript": "eslint --format json"
    }
    
    command = lint_commands.get(language.lower())
    if not command:
        return {"error": f"No lint command for {language}"}
    
    if files:
        command += " " + " ".join(files)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            try:
                lint_data = json.loads(result.stdout)
                return {
                    "success": result.returncode == 0,
                    "data": lint_data,
                    "summary": _parse_lint_summary(lint_data, language)
                }
            except json.JSONDecodeError:
                pass
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except Exception as e:
        return {"error": str(e)}


def _parse_lint_summary(data, language: str) -> Dict:
    """Parse linting results into standardized format"""
    summary = {
        "total_issues": 0,
        "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}
    }
    
    if isinstance(data, list):
        summary["total_issues"] = len(data)
        for issue in data:
            severity = issue.get("type", "warning").lower()
            if severity in summary["by_severity"]:
                summary["by_severity"][severity] += 1
    
    return summary


@app.skill()
def run_security_scan(language: str, paths: Optional[List[str]] = None) -> Dict:
    """
    Run security scan for a specific language
    
    Args:
        language: Programming language
        paths: Specific paths to scan
        
    Returns:
        Security scan results
    """
    security_commands = {
        "python": "bandit -r -f json .",
        "go": "gosec -fmt=json ./...",
        "typescript": "npm audit --json",
        "javascript": "npm audit --json"
    }
    
    command = security_commands.get(language.lower())
    if not command:
        return {"error": f"No security command for {language}"}
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            try:
                security_data = json.loads(result.stdout)
                return {
                    "success": True,
                    "data": security_data,
                    "summary": _parse_security_summary(security_data, language)
                }
            except json.JSONDecodeError:
                pass
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except Exception as e:
        return {"error": str(e)}


def _parse_security_summary(data: Dict, language: str) -> Dict:
    """Parse security results into standardized format"""
    summary = {
        "total_issues": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0
    }
    
    if language == "python" and "results" in data:
        issues = data["results"]
        summary["total_issues"] = len(issues)
        for issue in issues:
            severity = issue.get("issue_severity", "MEDIUM").lower()
            if severity in summary:
                summary[severity] += 1
    
    return summary


@app.reasoner()
async def verify_changes(
    execution_results: Dict,
    original_summary: Dict
) -> Dict:
    """
    Main reasoning function: Complete verification of changes
    
    This agent:
    1. Re-runs all analysis (tests, linting, security)
    2. Compares before/after results
    3. Identifies remaining issues
    4. Uses AI to assess quality improvement
    5. Recommends next action (merge, fix more, rollback)
    
    Args:
        execution_results: Results from executor agent
        original_summary: Original analysis from summarization agent
        
    Returns:
        Comprehensive verification results with recommendation
    """
    
    # Extract languages from original summary
    languages = original_summary.get('metadata', {}).get('languages_detected', [])
    
    verification_results = {
        "languages": {},
        "overall": {
            "all_tests_pass": True,
            "critical_issues_resolved": True,
            "new_issues_introduced": False,
            "quality_improved": False
        },
        "comparison": {}
    }
    
    # Re-run analysis for each language
    for language in languages:
        print(f"Verifying {language}...")
        
        lang_results = {
            "tests": run_tests(language),
            "linting": run_linting(language),
            "security": run_security_scan(language)
        }
        
        verification_results['languages'][language] = lang_results
        
        # Check if tests pass
        test_data = lang_results['tests']
        if not test_data.get('success', False):
            verification_results['overall']['all_tests_pass'] = False
        
        # Check for critical security issues
        security_summary = test_data.get('summary', {})
        if security_summary.get('critical', 0) > 0 or security_summary.get('high', 0) > 0:
            verification_results['overall']['critical_issues_resolved'] = False
    
    # Compare with original results
    for language in languages:
        original_lang = original_summary.get('language_analysis', {}).get(language, {})
        current_lang = verification_results['languages'].get(language, {})
        
        comparison = {
            "tests": _compare_test_results(
                original_lang.get('test_results', {}),
                current_lang.get('tests', {})
            ),
            "linting": _compare_lint_results(
                original_lang.get('linting_results', {}),
                current_lang.get('linting', {})
            ),
            "security": _compare_security_results(
                original_lang.get('security_results', {}),
                current_lang.get('security', {})
            )
        }
        
        verification_results['comparison'][language] = comparison
    
    # Use AI to analyze verification results
    analysis_prompt = f"""
    Analyze these verification results after applying fixes:
    
    Original Summary (key points):
    - Risk: {original_summary.get('llm_summary', {}).get('risk_assessment', 'unknown')}
    - Issues found: {sum(len(r.get('test_results', {}).get('failures', [])) for r in original_summary.get('language_analysis', {}).values())}
    
    Execution Results:
    - Successful fixes: {execution_results.get('successful_fixes', 0)}
    - Failed fixes: {execution_results.get('failed_fixes', 0)}
    
    Current Verification:
    - All tests pass: {verification_results['overall']['all_tests_pass']}
    - Critical issues resolved: {verification_results['overall']['critical_issues_resolved']}
    
    Comparisons:
    {json.dumps(verification_results['comparison'], indent=2)}
    
    Determine:
    1. Are all critical issues resolved?
    2. Were any new issues introduced?
    3. What's the overall quality improvement?
    4. Should we proceed to merge or need more fixes?
    
    Return as JSON:
    {{
        "ready_to_merge": true/false,
        "quality_improvement": "significant|moderate|minimal|negative|none",
        "remaining_issues": {{
            "critical": ["list"],
            "high": ["list"],
            "medium": ["list"]
        }},
        "new_issues": ["list of new issues introduced"],
        "recommendation": "merge|fix_and_rerun|rollback|manual_review",
        "rationale": "clear explanation of recommendation",
        "confidence": "low|medium|high"
    }}
    """
    
    ai_analysis = await app.ai(analysis_prompt)
    
    verification_results['ai_analysis'] = ai_analysis
    verification_results['ready_to_merge'] = ai_analysis.get('ready_to_merge', False)
    verification_results['recommendation'] = ai_analysis.get('recommendation', 'manual_review')
    
    # Generate summary
    verification_results['summary'] = {
        "all_tests_pass": verification_results['overall']['all_tests_pass'],
        "critical_issues_resolved": verification_results['overall']['critical_issues_resolved'],
        "quality_improvement": ai_analysis.get('quality_improvement', 'unknown'),
        "new_issues_introduced": len(ai_analysis.get('new_issues', [])) > 0
    }
    
    return verification_results


def _compare_test_results(before: Dict, after: Dict) -> Dict:
    """Compare test results before and after"""
    before_summary = before.get('summary', {})
    after_summary = after.get('summary', {})
    
    return {
        "improved": after_summary.get('failed', 99) < before_summary.get('failed', 0),
        "before_failed": before_summary.get('failed', 0),
        "after_failed": after_summary.get('failed', 0),
        "delta": before_summary.get('failed', 0) - after_summary.get('failed', 0)
    }


def _compare_lint_results(before: Dict, after: Dict) -> Dict:
    """Compare linting results before and after"""
    before_count = before.get('total_issues', 0)
    after_summary = after.get('summary', {})
    after_count = after_summary.get('total_issues', 0)
    
    return {
        "improved": after_count < before_count,
        "before_issues": before_count,
        "after_issues": after_count,
        "delta": before_count - after_count
    }


def _compare_security_results(before: Dict, after: Dict) -> Dict:
    """Compare security results before and after"""
    before_count = before.get('total_issues', 0)
    after_summary = after.get('summary', {})
    after_count = after_summary.get('total_issues', 0)
    
    return {
        "improved": after_count < before_count,
        "before_issues": before_count,
        "after_issues": after_count,
        "before_critical": before.get('critical_issues', 0),
        "after_critical": after_summary.get('critical', 0),
        "delta": before_count - after_count
    }


@app.reasoner()
async def identify_remaining_issues(verification_results: Dict) -> Dict:
    """
    Identify issues that still need to be addressed
    
    Args:
        verification_results: Results from verification
        
    Returns:
        Categorized remaining issues with priorities
    """
    
    remaining_issues = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }
    
    # Extract issues from verification results
    for language, results in verification_results.get('languages', {}).items():
        # Test failures
        test_data = results.get('tests', {}).get('data', {})
        if 'tests' in test_data:
            for test in test_data['tests']:
                if test.get('outcome') == 'failed':
                    remaining_issues['high'].append({
                        'type': 'test_failure',
                        'language': language,
                        'test': test.get('nodeid', 'unknown'),
                        'error': test.get('call', {}).get('longrepr', '')
                    })
        
        # Linting issues
        lint_data = results.get('linting', {}).get('data', {})
        if isinstance(lint_data, list):
            for issue in lint_data:
                severity = issue.get('type', 'warning').lower()
                priority = 'high' if severity == 'error' else 'medium'
                
                remaining_issues[priority].append({
                    'type': 'linting',
                    'language': language,
                    'file': issue.get('path', ''),
                    'message': issue.get('message', '')
                })
        
        # Security issues
        security_data = results.get('security', {}).get('data', {})
        if 'results' in security_data:
            for issue in security_data['results']:
                severity = issue.get('issue_severity', 'MEDIUM').lower()
                priority = 'critical' if severity == 'critical' else 'high' if severity == 'high' else 'medium'
                
                remaining_issues[priority].append({
                    'type': 'security',
                    'language': language,
                    'file': issue.get('filename', ''),
                    'message': issue.get('issue_text', ''),
                    'severity': severity
                })
    
    # Use AI to prioritize
    prioritization_prompt = f"""
    Prioritize these remaining issues:
    
    Critical: {len(remaining_issues['critical'])}
    High: {len(remaining_issues['high'])}
    Medium: {len(remaining_issues['medium'])}
    
    Details:
    {json.dumps(remaining_issues, indent=2)}
    
    Provide:
    1. Which issues are blocking merge (must fix now)
    2. Which can be addressed in follow-up PR
    3. Recommended next steps in priority order
    4. Estimated time to resolve blocking issues
    
    Return as JSON:
    {{
        "blocking_issues": [
            {{
                "issue": "description",
                "reason": "why it blocks merge",
                "estimated_time": "minutes"
            }}
        ],
        "can_defer": ["list of issues that can wait"],
        "next_steps": ["ordered list of actions"],
        "estimated_time_to_unblock": "total minutes"
    }}
    """
    
    prioritization = await app.ai(prioritization_prompt)
    
    return {
        "remaining_issues": remaining_issues,
        "prioritization": prioritization,
        "total_remaining": sum(len(issues) for issues in remaining_issues.values())
    }


@app.reasoner()
async def generate_improvement_suggestions(
    verification_results: Dict,
    execution_results: Dict
) -> Dict:
    """
    Generate suggestions for improving the fixes
    
    Args:
        verification_results: Verification results
        execution_results: Execution results
        
    Returns:
        Actionable improvement suggestions
    """
    
    suggestion_prompt = f"""
    Based on these results, provide specific improvement suggestions:
    
    Verification Summary:
    - Ready to merge: {verification_results.get('ready_to_merge', False)}
    - Quality improvement: {verification_results.get('ai_analysis', {}).get('quality_improvement', 'unknown')}
    
    Execution Summary:
    - Successful: {execution_results.get('successful_fixes', 0)}
    - Failed: {execution_results.get('failed_fixes', 0)}
    
    Provide actionable suggestions in these areas:
    1. Code improvements
    2. Testing improvements
    3. Security hardening
    4. Architecture recommendations
    
    Return as JSON:
    {{
        "code_improvements": [
            {{
                "area": "specific area",
                "suggestion": "what to do",
                "impact": "expected benefit"
            }}
        ],
        "testing_improvements": [...],
        "security_improvements": [...],
        "architectural_improvements": [...],
        "priority_order": ["ordered list of what to do first"]
    }}
    """
    
    suggestions = await app.ai(suggestion_prompt)
    
    return suggestions


if __name__ == "__main__":
    # Run the agent - it will register with the control plane
    app.run()

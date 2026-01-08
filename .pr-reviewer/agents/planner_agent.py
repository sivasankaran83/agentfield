"""
Planner Agent - Final Production Version
Creates remediation plans based on analysis results with human oversight
"""

from agentfield import Agent
from typing import Dict, List, Optional, Any
import os
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import (
    OverallIssueStrategy,
    ExecutionPlan,
    PlanValidationResult
)
from utils.llm_sanitizer import sanitize_llm_output

# Initialize Planner Agent
app = Agent(
    node_id="pr-reviewer-planner",
    agentfield_url=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080")
)


@app.skill()
def categorize_issues(summary: Dict) -> Dict[str, List[Dict]]:
    """
    Categorize issues from summary into actionable groups
    
    Args:
        summary: Comprehensive summary from summarization agent
        
    Returns:
        Categorized issues by type
    """
    categories = {
        "test_failures": [],
        "linting_issues": [],
        "security_issues": [],
        "type_errors": [],
        "breaking_changes": []
    }
    
    # Extract issues from language analysis
    for language, results in summary.get('language_analysis', {}).items():
        # Test failures
        test_results = results.get('test_results', {})
        if isinstance(test_results, dict):
            failures = test_results.get('failures', [])
            for failure in failures:
                categories['test_failures'].append({
                    'language': language,
                    'test': failure.get('test', ''),
                    'error': failure.get('error', ''),
                    'file': failure.get('file', '')
                })
        
        # Linting issues
        linting_results = results.get('linting_results', {})
        if isinstance(linting_results, dict):
            issues = linting_results.get('issues', [])
            for issue in issues:
                severity = issue.get('severity', 'low')
                if severity in ['high', 'critical']:
                    categories['linting_issues'].append({
                        'language': language,
                        'file': issue.get('file', ''),
                        'line': issue.get('line', 0),
                        'message': issue.get('message', ''),
                        'severity': severity
                    })
        
        # Security issues
        security_results = results.get('security_results', {})
        if isinstance(security_results, dict):
            sec_issues = security_results.get('issues', [])
            for issue in sec_issues:
                categories['security_issues'].append({
                    'language': language,
                    'file': issue.get('file', ''),
                    'line': issue.get('line', 0),
                    'message': issue.get('message', ''),
                    'severity': issue.get('severity', 'medium')
                })
    
    # Extract breaking changes from LLM
    llm_summary = summary.get('llm_summary', {})
    breaking_changes = llm_summary.get('breaking_changes', [])
    if isinstance(breaking_changes, list):
        categories['breaking_changes'] = breaking_changes
    
    return categories


@app.skill()
def calculate_priority(issue: Dict) -> str:
    """
    Calculate priority for an issue based on type and severity
    
    Args:
        issue: Issue details
        
    Returns:
        Priority level (critical, high, medium, low)
    """
    issue_type = issue.get('type', '')
    severity = str(issue.get('severity', '')).lower()
    
    # Security issues are always high priority
    if 'security' in issue_type.lower():
        if severity in ['critical', 'high']:
            return 'critical'
        return 'high'
    
    # Breaking changes are critical
    if 'breaking' in issue_type.lower():
        return 'critical'
    
    # Test failures are high priority
    if 'test' in issue_type.lower():
        return 'high'
    
    # Map severity directly
    severity_map = {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
    }
    
    return severity_map.get(severity, 'medium')


@app.skill()
def estimate_effort(issue: Dict) -> Dict[str, Any]:
    """
    Estimate effort and complexity to fix an issue
    
    Args:
        issue: Issue details
        
    Returns:
        Effort estimation with time and complexity
    """
    issue_str = str(issue).lower()
    category = issue.get('category', '')
    
    # Base estimates in minutes
    estimates = {
        'test_fix': {'time': 30, 'complexity': 'medium'},
        'linting': {'time': 10, 'complexity': 'low'},
        'security': {'time': 60, 'complexity': 'high'},
        'type_error': {'time': 20, 'complexity': 'medium'},
        'breaking_change': {'time': 120, 'complexity': 'high'}
    }
    
    # Adjust based on issue details
    if 'test' in issue_str or category == 'test_fix':
        return estimates['test_fix']
    elif 'lint' in issue_str or 'format' in issue_str:
        return estimates['linting']
    elif 'security' in issue_str or 'vulnerability' in issue_str:
        return estimates['security']
    elif 'type' in issue_str:
        return estimates['type_error']
    elif 'breaking' in issue_str:
        return estimates['breaking_change']
    
    return {'time': 30, 'complexity': 'medium'}


@app.reasoner()
async def create_remediation_plan(
    summary: Dict,
    context_enrichment: Optional[str] = None
) -> Dict:
    """
    Main reasoning function: Creates comprehensive remediation plan
    
    This agent:
    1. Analyzes the summary from summarization agent
    2. Categorizes issues by type
    3. Uses AI to create fix strategies
    4. Prioritizes fixes based on impact
    5. Estimates effort and dependencies
    6. Generates execution phases
    
    Args:
        summary: Output from summarization agent
        context_enrichment: Additional human context (optional)
        
    Returns:
        Comprehensive remediation plan with prioritized fixes
    """
    
    # Step 1: Categorize issues
    categorized = categorize_issues(summary)
    
    # Count total issues
    total_issues = sum(len(issues) for issues in categorized.values())
    
    if total_issues == 0:
        return {
            "status": "success",
            "message": "No issues found - PR looks good!",
            "total_fixes": 0,
            "recommendation": "ready_to_merge"
        }
    
    # Step 2: Use AI to analyze issues and create strategies
    issue_analysis_prompt = f"""
    Analyze these categorized issues from a PR review:
    
    Test Failures: {len(categorized['test_failures'])}
    Linting Issues: {len(categorized['linting_issues'])}
    Security Issues: {len(categorized['security_issues'])}
    Breaking Changes: {len(categorized['breaking_changes'])}
    
    Issues Details:
    {json.dumps(categorized, indent=2)}
    
    Human Context: {context_enrichment or "No additional context provided"}
    
    For each category, provide:
    1. Root cause analysis - why these issues exist
    2. Fix strategy - how to resolve them
    3. Whether fixes can be automated
    4. Dependencies between fixes
    5. Risk of fixes causing new issues
    
    Return as JSON:
    {{
        "test_failures": {{
            "root_cause": "explanation",
            "strategy": "fix approach",
            "automatable": true/false,
            "risk": "low|medium|high",
            "dependencies": ["list of dependencies"]
        }},
        "linting_issues": {{...}},
        "security_issues": {{...}},
        "overall_strategy": "high-level approach",
        "focus_areas": ["priority 1", "priority 2", "priority 3"]
    }}
    """
    # Use Pydantic schema for structured response
    issue_strategies_raw = await app.ai(
        user=issue_analysis_prompt,
        schema=OverallIssueStrategy
    )
    issue_strategies = sanitize_llm_output(issue_strategies_raw)

    # Step 3: Create fix items for each issue
    fix_items = []
    
    # Security issues (highest priority)
    for issue in categorized['security_issues']:
        priority = calculate_priority({'type': 'security', 'severity': issue['severity']})
        effort = estimate_effort({'category': 'security'})
        
        fix_items.append({
            'id': f"sec_{len(fix_items)}",
            'category': 'security',
            'priority': priority,
            'effort_minutes': effort['time'],
            'complexity': effort['complexity'],
            'description': f"Fix {issue['severity']} security issue in {issue['file']}",
            'details': issue,
            'language': issue['language'],
            'automatable': issue_strategies.get('security_issues', {}).get('automatable', False)
        })
    
    # Test failures
    for failure in categorized['test_failures']:
        priority = calculate_priority({'type': 'test_fix'})
        effort = estimate_effort({'category': 'test_fix'})
        
        fix_items.append({
            'id': f"test_{len(fix_items)}",
            'category': 'test_fix',
            'priority': priority,
            'effort_minutes': effort['time'],
            'complexity': effort['complexity'],
            'description': f"Fix failing test: {failure['test']}",
            'details': failure,
            'language': failure['language'],
            'automatable': issue_strategies.get('test_failures', {}).get('automatable', False)
        })
    
    # Linting issues (only high/critical)
    for issue in categorized['linting_issues']:
        priority = calculate_priority(issue)
        effort = estimate_effort({'category': 'linting'})
        
        fix_items.append({
            'id': f"lint_{len(fix_items)}",
            'category': 'code_quality',
            'priority': priority,
            'effort_minutes': effort['time'],
            'complexity': effort['complexity'],
            'description': f"Fix {issue['severity']} linting issue in {issue['file']}",
            'details': issue,
            'language': issue['language'],
            'automatable': True  # Linting is usually automatable
        })
    
    # Sort by priority (critical > high > medium > low)
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    fix_items.sort(key=lambda x: (priority_order.get(x['priority'], 3), -x['effort_minutes']))
    
    # Step 4: Use AI to create execution plan with phases
    execution_plan_prompt = f"""
    Create a detailed execution plan for these fixes:
    
    Total fixes: {len(fix_items)}
    Strategies:
    {json.dumps(issue_strategies, indent=2)}
    
    Top 10 fixes to address:
    {json.dumps(fix_items[:10], indent=2)}
    
    Consider:
    1. Order of execution (dependencies)
    2. What can be done in parallel
    3. Which fixes might affect others
    4. Testing strategy after each phase
    5. Rollback points
    
    Return as JSON:
    {{
        "phases": [
            {{
                "phase": 1,
                "name": "Critical Security Fixes",
                "fix_ids": ["sec_0", "sec_1"],
                "parallel": false,
                "description": "Address critical security vulnerabilities first",
                "estimated_minutes": 60,
                "validation": "Run security scan after completion"
            }}
        ],
        "testing_strategy": "how to test after fixes",
        "rollback_strategy": "how to rollback if needed",
        "risks": ["potential risks"],
        "human_review_points": ["where human should check"]
    }}
    """
    
    # Use Pydantic schema for structured response
    execution_plan_raw = await app.ai(
        user=execution_plan_prompt,
        schema=ExecutionPlan
    )
    execution_plan = sanitize_llm_output(execution_plan_raw)

    # Step 5: Generate human-readable summary
    summary_prompt = f"""
    Create a concise summary of this remediation plan for human review:
    
    Total fixes: {len(fix_items)}
    Critical: {len([f for f in fix_items if f['priority'] == 'critical'])}
    High: {len([f for f in fix_items if f['priority'] == 'high'])}
    Security issues: {len(categorized['security_issues'])}
    Test failures: {len(categorized['test_failures'])}
    
    Write 2-3 sentences that:
    - Explain what will be fixed
    - Why it's important
    - Estimated time
    - Main risks
    
    Be direct, actionable, and specific.
    """
    
    # Get text response for summary
    human_summary_response = await app.ai(user=summary_prompt, schema=ExecutionPlan)
    human_summary = sanitize_llm_output(human_summary_response)    

    # Step 6: Calculate statistics
    total_time = sum(fix['effort_minutes'] for fix in fix_items)
    automatable_count = len([f for f in fix_items if f.get('automatable', False)])
    
    # Step 7: Compile final plan
    remediation_plan = {
        "status": "success",
        "summary": human_summary,
        "total_fixes": len(fix_items),
        "by_priority": {
            "critical": len([f for f in fix_items if f['priority'] == 'critical']),
            "high": len([f for f in fix_items if f['priority'] == 'high']),
            "medium": len([f for f in fix_items if f['priority'] == 'medium']),
            "low": len([f for f in fix_items if f['priority'] == 'low'])
        },
        "by_category": {
            "security": len([f for f in fix_items if f['category'] == 'security']),
            "test_fixes": len([f for f in fix_items if f['category'] == 'test_fix']),
            "code_quality": len([f for f in fix_items if f['category'] == 'code_quality'])
        },
        "estimated_total_time": total_time,
        "automatable_fixes": automatable_count,
        "manual_fixes": len(fix_items) - automatable_count,
        "fix_items": fix_items,
        "strategies": issue_strategies,
        "execution_plan": execution_plan,
        "requires_human_review": any(f['priority'] == 'critical' for f in fix_items),
        "context_used": context_enrichment or None
    }
    
    return remediation_plan


@app.reasoner()
async def modify_plan(
    original_plan: Dict,
    modifications: str
) -> Dict:
    """
    Modify an existing plan based on human feedback
    
    Args:
        original_plan: Original remediation plan
        modifications: Human feedback/instructions
        
    Returns:
        Modified plan incorporating feedback
    """
    
    modification_prompt = f"""
    Modify this remediation plan based on human feedback:

    Original Plan Summary:
    - Total fixes: {original_plan.get('total_fixes', 0)}
    - Critical: {original_plan.get('by_priority', {}).get('critical', 0)}
    - Estimated time: {original_plan.get('estimated_total_time', 0)} minutes

    Original Fix Items:
    {json.dumps(original_plan.get('fix_items', [])[:10], indent=2)}

    Human Feedback:
    {modifications}

    Apply the requested modifications. Common requests:
    - "Skip linting fixes" - remove code_quality items
    - "Focus on security" - prioritize security items
    - "Only critical issues" - filter to critical priority only
    - "Add X" - include additional considerations

    Return the complete modified plan in the same format, ensuring:
    1. All requested changes are applied
    2. Plan remains coherent
    3. Priorities are recalculated if needed
    4. Summary is updated
    """

    # Get text response for modification feedback
    modified_plan_response = await app.ai(user=modification_prompt, schema=ExecutionPlan)
    modified_plan = sanitize_llm_output(modified_plan_response)

    # Ensure modified plan has required structure
    if isinstance(modified_plan, dict):
        modified_plan['modified'] = True
        modified_plan['original_summary'] = original_plan.get('summary', '')
        modified_plan['modifications_applied'] = modifications
    
    return modified_plan


@app.reasoner()
async def validate_plan(plan: Dict) -> Dict:
    """
    Validate a remediation plan for completeness and feasibility
    
    Args:
        plan: Remediation plan to validate
        
    Returns:
        Validation results with issues and suggestions
    """
    
    validation_prompt = f"""
    Validate this remediation plan for completeness and feasibility:

    {json.dumps(plan, indent=2)}

    Check for:
    1. All critical issues are addressed
    2. Execution order is logical (no circular dependencies)
    3. Time estimates are realistic
    4. Adequate testing/validation steps
    5. Clear rollback strategy
    6. Human review points are appropriate

    Return as JSON:
    {{
        "valid": true/false,
        "completeness_score": 0-100,
        "issues": [
            {{
                "severity": "critical|high|medium|low",
                "issue": "description of problem",
                "suggestion": "how to fix"
            }}
        ],
        "warnings": ["list of warnings"],
        "suggestions": ["list of improvements"],
        "confidence": "low|medium|high",
        "recommendation": "approve|revise|reject"
    }}
    """

    # Use Pydantic schema for structured validation results
    validation_results_raw = await app.ai(
        user=validation_prompt,
        schema=PlanValidationResult
    )
    validation_results = sanitize_llm_output(validation_results_raw)

    return validation_results


if __name__ == "__main__":
    # Run the agent - it will register with the control plane
    app.run()

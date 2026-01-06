"""
Generator Agent - Final Production Version
Generates final PR updates or performs merge with human oversight
"""

from agentfield import Agent
from typing import Dict, List, Optional
import os
import subprocess
import json
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import (
    CommitMessage,
    PRDescription,
    ActionDecision,
    MergeSafetyCheck,
    FinalReport
)
from utils.llm_sanitizer import sanitize_llm_output

# Initialize Generator Agent
app = Agent(
    node_id="pr-reviewer-generator",
    agentfield_url=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080")
)


@app.skill()
def get_changed_files() -> List[str]:
    """Get list of files changed in working directory"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except Exception:
        return []


@app.skill()
def git_add(files: List[str]) -> Dict:
    """Stage files for commit"""
    try:
        subprocess.run(
            ["git", "add"] + files,
            capture_output=True,
            text=True,
            check=True
        )
        return {"success": True, "files_staged": len(files)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.skill()
def git_commit(message: str) -> Dict:
    """Create git commit"""
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "commit_hash": hash_result.stdout.strip(),
            "message": message
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.skill()
def git_push(branch: str = "HEAD") -> Dict:
    """Push changes to remote"""
    try:
        subprocess.run(
            ["git", "push", "origin", branch],
            capture_output=True,
            text=True,
            check=True
        )
        return {"success": True, "branch": branch}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.skill()
def get_git_diff_summary() -> str:
    """Get summary of git diff"""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"


@app.reasoner()
async def generate_commit_message(
    execution_results: Dict,
    verification_results: Dict
) -> str:
    """
    Generate descriptive commit message using AI
    
    Args:
        execution_results: Results from executor agent
        verification_results: Results from verifier agent
        
    Returns:
        Generated commit message following conventional commits format
    """
    
    diff_summary = get_git_diff_summary()
    
    commit_prompt = f"""
    Generate a clear, descriptive commit message for these PR review fixes:
    
    Execution Summary:
    - Successful fixes: {execution_results.get('successful_fixes', 0)}
    - Failed fixes: {execution_results.get('failed_fixes', 0)}
    - Categories: {', '.join(set(d.get('category', '') for d in execution_results.get('details', [])))}
    
    Verification:
    - All tests pass: {verification_results.get('summary', {}).get('all_tests_pass', False)}
    - Quality improvement: {verification_results.get('summary', {}).get('quality_improvement', 'unknown')}
    
    Diff Summary:
    {diff_summary}
    
    Create a commit message following conventional commits format:

    <type>(<scope>): <subject>

    <body>

    Types: fix, feat, refactor, test, docs, style, chore
    Keep subject under 50 chars
    Body should explain what was fixed and why

    Example:
    fix(auth): resolve OAuth token validation issues

    - Fixed failing test_oauth_google test
    - Addressed security vulnerability in token storage
    - Improved error handling for invalid tokens

    Generate the commit message for the current changes.
    """

    # Use Pydantic schema for structured response
    commit_message_response_raw = await app.ai(
        user=commit_prompt,
        schema=CommitMessage
    )
    commit_message_response = sanitize_llm_output(commit_message_response_raw)

    # Return the full commit message text
    return f"{commit_message_response['subject']}\n\n{commit_message_response['body']}"


@app.reasoner()
async def generate_pr_description(
    summary: Dict,
    execution_results: Dict,
    verification_results: Dict
) -> str:
    """
    Generate comprehensive PR description
    
    Args:
        summary: Original summary from summarization agent
        execution_results: Results from executor agent
        verification_results: Results from verifier agent
        
    Returns:
        Markdown-formatted PR description
    """
    
    description_prompt = f"""
    Generate a comprehensive PR description based on these results:
    
    Original Analysis:
    {json.dumps(summary.get('llm_summary', {}), indent=2)}
    
    Fixes Applied:
    - Successful: {execution_results.get('successful_fixes', 0)}
    - Failed: {execution_results.get('failed_fixes', 0)}
    
    Verification:
    {json.dumps(verification_results.get('summary', {}), indent=2)}
    
    Create a markdown PR description with:

    ## Summary
    [Brief 2-3 sentence overview]

    ## Changes Made
    [Bullet list of key changes]

    ## Fixes Applied by AI
    [What the PR Reviewer Agent fixed]

    ## Testing
    [Testing status and coverage]

    ## Verification
    [Quality improvements and checks]

    ## Notes for Reviewers
    [Important points to review]

    Keep it professional, clear, and actionable.
    """

    # Use Pydantic schema for structured response
    pr_description_response_raw = await app.ai(
        user=description_prompt,
        schema=PRDescription
    )
    pr_description_response = sanitize_llm_output(pr_description_response_raw)

    # Format into markdown
    return f"""## Summary
{pr_description_response['summary']}

## Changes Made
{chr(10).join('- ' + change for change in pr_description_response['changes_made'])}

## Fixes Applied by AI
{pr_description_response['fixes_applied']}

## Testing
{pr_description_response['testing']}

## Verification
{pr_description_response['verification']}

## Notes for Reviewers
{pr_description_response['notes_for_reviewers']}"""


@app.reasoner()
async def decide_action(
    verification_results: Dict,
    execution_results: Dict
) -> Dict:
    """
    Decide what action to take based on verification results
    
    Args:
        verification_results: Verification results
        execution_results: Execution results
        
    Returns:
        Decision with reasoning and recommended action
    """
    
    changed_files = get_changed_files()
    
    decision_prompt = f"""
    Decide the best action based on these results:
    
    Files Changed: {len(changed_files)}
    Successful Fixes: {execution_results.get('successful_fixes', 0)}
    Failed Fixes: {execution_results.get('failed_fixes', 0)}
    
    Verification:
    - Ready to merge: {verification_results.get('ready_to_merge', False)}
    - All tests pass: {verification_results.get('summary', {}).get('all_tests_pass', False)}
    - Quality improvement: {verification_results.get('summary', {}).get('quality_improvement', 'unknown')}
    - Recommendation: {verification_results.get('recommendation', 'unknown')}
    
    Options:
    1. **merge** - Merge to target branch (only if no bot changes and verification passed)
    2. **update_pr** - Update PR with fixes and restart review cycle (if files changed)
    3. **manual_review** - Request human review before proceeding
    4. **abort** - Stop process (if verification failed badly)
    
    Decision Logic:
    - If files changed: must be update_pr (never merge bot changes directly)
    - If ready_to_merge and no changes: can merge
    - If quality improved but issues remain: manual_review
    - If quality decreased: abort

    Return JSON:
    {{
        "action": "merge|update_pr|manual_review|abort",
        "confidence": "low|medium|high",
        "reasoning": "clear explanation of why this action",
        "requires_human_approval": true/false,
        "next_steps": ["what happens next"]
    }}
    """

    # Use Pydantic schema for structured response
    decision_raw = await app.ai(
        user=decision_prompt,
        schema=ActionDecision
    )
    decision = sanitize_llm_output(decision_raw)

    return decision


@app.reasoner()
async def update_pr(
    pr_number: int,
    execution_results: Dict,
    verification_results: Dict
) -> Dict:
    """
    Update PR with fixes and push changes
    
    Args:
        pr_number: PR number
        execution_results: Results from executor agent
        verification_results: Results from verifier agent
        
    Returns:
        Update status with details
    """
    
    # Get changed files
    changed_files = get_changed_files()
    
    if not changed_files:
        return {
            "status": "no_changes",
            "message": "No files were modified",
            "action_taken": "none"
        }
    
    # Stage files
    stage_result = git_add(changed_files)
    
    if not stage_result['success']:
        return {
            "status": "error",
            "message": "Failed to stage files",
            "error": stage_result.get('error')
        }
    
    # Generate commit message
    commit_message = await generate_commit_message(
        execution_results,
        verification_results
    )
    
    # Add [skip ci] to avoid triggering CI again
    if "[skip ci]" not in commit_message:
        commit_message += "\n\n[skip ci]"
    
    # Commit changes
    commit_result = git_commit(commit_message)
    
    if not commit_result['success']:
        return {
            "status": "error",
            "message": "Failed to commit changes",
            "error": commit_result.get('error')
        }
    
    # Push changes
    push_result = git_push()
    
    if not push_result['success']:
        return {
            "status": "error",
            "message": "Failed to push changes",
            "error": push_result.get('error')
        }
    
    return {
        "status": "success",
        "message": f"PR #{pr_number} updated successfully",
        "commit_hash": commit_result['commit_hash'],
        "files_changed": len(changed_files),
        "commit_message": commit_message,
        "note": "Changes pushed to PR branch - review cycle continues"
    }


@app.reasoner()
async def merge_pr(
    pr_number: int,
    source_branch: str,
    target_branch: str,
    summary: Dict,
    execution_results: Dict,
    verification_results: Dict
) -> Dict:
    """
    Merge PR to target branch (GitHub API integration)
    
    NOTE: This is a placeholder. In production, use GitHub API via GITHUB_TOKEN
    
    Args:
        pr_number: PR number
        source_branch: Source branch (PR branch)
        target_branch: Target branch (e.g., main)
        summary: Original summary
        execution_results: Execution results
        verification_results: Verification results
        
    Returns:
        Merge status
    """
    
    # Final verification check
    if not verification_results.get('ready_to_merge', False):
        return {
            "status": "blocked",
            "message": "PR is not ready to merge",
            "reason": verification_results.get('ai_analysis', {}).get('rationale', 'Verification failed')
        }
    
    # Use AI to do final safety check
    merge_check_prompt = f"""
    Final safety check before merging PR #{pr_number}:
    
    Verification Summary:
    - All tests pass: {verification_results.get('summary', {}).get('all_tests_pass', False)}
    - Quality improvement: {verification_results.get('summary', {}).get('quality_improvement', 'unknown')}
    - No new issues: {not verification_results.get('summary', {}).get('new_issues_introduced', True)}
    
    Execution:
    - Successful fixes: {execution_results.get('successful_fixes', 0)}
    - Failed fixes: {execution_results.get('failed_fixes', 0)}
    
    Is it safe to merge? Consider:
    1. All tests passing
    2. No critical issues remaining
    3. Quality improved or maintained
    4. No new security issues
    5. No breaking changes introduced

    Return JSON:
    {{
        "safe_to_merge": true/false,
        "confidence": "low|medium|high",
        "concerns": ["any remaining concerns"],
        "recommendation": "merge|wait|manual_review",
        "final_checks": ["checklist for human"]
    }}
    """

    # Use Pydantic schema for structured response
    merge_check_raw = await app.ai(
        user=merge_check_prompt,
        schema=MergeSafetyCheck
    )
    merge_check = sanitize_llm_output(merge_check_raw)

    if not merge_check.get('safe_to_merge', False):
        return {
            "status": "blocked",
            "message": "AI safety check failed",
            "concerns": merge_check.get('concerns', []),
            "recommendation": merge_check.get('recommendation', 'manual_review'),
            "final_checks": merge_check.get('final_checks', [])
        }
    
    # In production, use GitHub API here
    # For now, return success with instructions
    return {
        "status": "success",
        "message": f"PR #{pr_number} is ready to merge",
        "source_branch": source_branch,
        "target_branch": target_branch,
        "timestamp": datetime.now().isoformat(),
        "note": "Human should complete merge via GitHub UI or use GitHub API integration",
        "merge_check": merge_check
    }


@app.reasoner()
async def generate_final_report(
    summary: Dict,
    execution_results: Dict,
    verification_results: Dict,
    action_taken: str
) -> Dict:
    """
    Generate comprehensive final report
    
    Args:
        summary: Original summary
        execution_results: Execution results
        verification_results: Verification results
        action_taken: Action taken (merged, updated, aborted)
        
    Returns:
        Complete final report with metrics and narrative
    """
    
    report_prompt = f"""
    Generate a comprehensive final report for this PR review:
    
    Original Analysis:
    {json.dumps(summary.get('llm_summary', {}), indent=2)}
    
    Execution:
    - Total fixes attempted: {execution_results.get('total_fixes', 0)}
    - Successful: {execution_results.get('successful_fixes', 0)}
    - Failed: {execution_results.get('failed_fixes', 0)}
    
    Verification:
    {json.dumps(verification_results.get('summary', {}), indent=2)}
    
    Action Taken: {action_taken}
    
    Create a report with:
    
    ## Executive Summary
    [2-3 sentences for stakeholders]
    
    ## Key Metrics
    - Files analyzed
    - Issues found and fixed
    - Quality improvement
    - Time saved
    
    ## What Was Accomplished
    [Detailed list with outcomes]
    
    ## Impact
    [Business and technical impact]
    
    ## Lessons Learned
    [What went well, what could improve]

    ## Recommendations for Future PRs
    [Actionable suggestions]

    Make it professional and suitable for stakeholders.
    """

    # Use Pydantic schema for structured response
    narrative_report_raw = await app.ai(
        user=report_prompt,
        schema=FinalReport
    )
    narrative_report = sanitize_llm_output(narrative_report_raw)

    # Compile complete report
    complete_report = {
        "timestamp": datetime.now().isoformat(),
        "action_taken": action_taken,
        "narrative_report": narrative_report,
        "metrics": {
            "files_changed": len(summary.get('metadata', {}).get('changed_files', [])) if isinstance(summary.get('metadata'), dict) else 0,
            "languages_analyzed": len(summary.get('metadata', {}).get('languages_detected', [])) if isinstance(summary.get('metadata'), dict) else 0,
            "issues_found": execution_results.get('total_fixes', 0),
            "fixes_applied": execution_results.get('successful_fixes', 0),
            "fixes_failed": execution_results.get('failed_fixes', 0),
            "tests_passing": verification_results.get('summary', {}).get('all_tests_pass', False),
            "quality_improvement": verification_results.get('summary', {}).get('quality_improvement', 'unknown'),
            "backups_created": len(execution_results.get('backups_created', []))
        },
        "summary": summary,
        "execution": execution_results,
        "verification": verification_results
    }
    
    return complete_report


if __name__ == "__main__":
    # Run the agent - it will register with the control plane
    app.run()

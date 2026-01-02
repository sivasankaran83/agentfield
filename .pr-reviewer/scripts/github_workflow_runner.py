#!/usr/bin/env python3
"""
GitHub Actions Workflow Runner
Orchestrates PR review workflow using AgentField API endpoints
API Format: /api/v1/execute/[node_id].[reasoner_function]
"""

import os
import sys
import argparse
import asyncio
import json
import httpx
from pathlib import Path
from typing import Dict, Any

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from github import Github
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Installing required packages...")
    os.system("pip install PyGithub rich httpx")
    from github import Github
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# AgentField server URL
AGENTFIELD_SERVER = os.getenv("AGENTFIELD_SERVER", "http://localhost:8080")

# AgentField API endpoints for each agent's reasoner
# Format: /api/v1/execute/[node_id].[reasoner_function_name]
AGENT_ENDPOINTS = {
    "summarizer": {
        "analyze_pr": f"{AGENTFIELD_SERVER}/api/v1/execute/pr-reviewer-summarizer.analyze_pr_comprehensive"
    },
    "planner": {
        "create_plan": f"{AGENTFIELD_SERVER}/api/v1/execute/pr-reviewer-planner.create_remediation_plan"
    },
    "executor": {
        "execute_fixes": f"{AGENTFIELD_SERVER}/api/v1/execute/pr-reviewer-executor.execute_remediation_plan"
    },
    "verifier": {
        "verify_changes": f"{AGENTFIELD_SERVER}/api/v1/execute/pr-reviewer-verifier.verify_fixes_comprehensive"
    }
}


async def call_agent_reasoner(
    agent: str,
    reasoner: str,
    input_data: Dict[str, Any],
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Call AgentField agent reasoner endpoint
    
    Args:
        agent: Agent name (e.g., "summarizer", "planner")
        reasoner: Reasoner function name (e.g., "analyze_pr", "create_plan")
        input_data: Input data for the reasoner
        timeout: Request timeout in seconds
    
    Returns:
        Reasoner output
    """
    endpoint = AGENT_ENDPOINTS.get(agent, {}).get(reasoner)
    if not endpoint:
        raise ValueError(f"Unknown agent/reasoner: {agent}.{reasoner}")
    
    console.print(f"[blue]📞 Calling {agent}.{reasoner}[/blue]")
    console.print(f"[dim]   Endpoint: {endpoint}[/dim]")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                endpoint,
                json=input_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            console.print(f"[green]✅ {agent}.{reasoner} completed[/green]")
            return result
                
    except httpx.TimeoutException:
        console.print(f"[red]❌ Timeout (>{timeout}s)[/red]")
        raise Exception(f"Timeout after {timeout}s")
    except httpx.HTTPStatusError as e:
        try:
            error_body = e.response.json()
            error_detail = error_body.get("detail", error_body.get("error", str(error_body)))
        except:
            error_detail = e.response.text
        console.print(f"[red]❌ HTTP {e.response.status_code}: {error_detail}[/red]")
        raise Exception(f"HTTP {e.response.status_code}: {error_detail}")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


async def check_agentfield_health() -> bool:
    """Check if AgentField is healthy"""
    console.print(f"[dim]Checking AgentField at: {AGENTFIELD_SERVER}[/dim]")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try multiple health check endpoints
            endpoints = ["/health", "/api/v1/health", "/healthz"]

            for endpoint in endpoints:
                try:
                    url = f"{AGENTFIELD_SERVER}{endpoint}"
                    console.print(f"[dim]  Trying {url}...[/dim]")
                    health = await client.get(url)

                    if health.status_code == 200:
                        console.print(f"[green]✅ AgentField healthy at {AGENTFIELD_SERVER}{endpoint}[/green]")
                        return True
                except Exception as e:
                    console.print(f"[dim]  {endpoint} failed: {e}[/dim]")
                    continue

            console.print(f"[red]❌ AgentField unhealthy - no health endpoint responded[/red]")
            return False

    except Exception as e:
        console.print(f"[red]❌ Cannot connect to AgentField: {e}[/red]")
        console.print(f"[dim]Server URL: {AGENTFIELD_SERVER}[/dim]")
        return False


def post_comment(pr, message: str):
    """Post comment to PR"""
    try:
        pr.create_issue_comment(message)
        console.print(f"[green]✅ Posted comment[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to post: {e}[/red]")


def get_pr_files(pr) -> list:
    """Get changed files"""
    return [f.filename for f in pr.get_files()]


def get_pr_diff(pr) -> str:
    """Get unified diff"""
    try:
        diff_text = ""
        for file in pr.get_files():
            if file.patch:
                diff_text += f"\n--- {file.filename}\n+++ {file.filename}\n{file.patch}\n"
        return diff_text
    except:
        return ""


def get_pr_info(pr) -> Dict[str, Any]:
    """Extract PR information"""
    return {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body or "",
        "base_branch": pr.base.ref,
        "head_branch": pr.head.ref,
        "base_sha": pr.base.sha,
        "head_sha": pr.head.sha,
        "author": pr.user.login,
        "changed_files": len(list(pr.get_files())),
        "additions": pr.additions,
        "deletions": pr.deletions
    }


def get_pr_comments(pr) -> list:
    """Get PR comments"""
    comments = []
    for comment in pr.get_issue_comments():
        comments.append({
            "author": comment.user.login,
            "body": comment.body,
            "created_at": comment.created_at.isoformat()
        })
    return comments


async def run_analyze(pr, repo):
    """Run analysis using Summarizer agent"""
    console.print(Panel.fit("🔍 ANALYZING PR", style="bold cyan"))
    
    post_comment(pr, """🤖 **PR Reviewer Agent** - Analysis Started

⏳ Running comprehensive analysis...

This will take 2-5 minutes.
""")
    
    pr_info = get_pr_info(pr)
    files = get_pr_files(pr)
    pr_diff = get_pr_diff(pr)
    
    console.print(f"Files: {len(files)}, +{pr_info['additions']} -{pr_info['deletions']}")
    
    input_data = {
        "pr_number": pr_info["number"],
        "base_branch": pr_info["base_branch"],
        "head_branch": pr_info["head_branch"],
        "repository": repo.full_name
    }
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Analyzing...", total=None)
            
            summary_result = await call_agent_reasoner(
                agent="summarizer",
                reasoner="analyze_pr",
                input_data=input_data,
                timeout=300
            )
            
            progress.update(task, completed=True)
    
    except Exception as e:
        console.print(f"[red]❌ Analysis failed: {e}[/red]")
        post_comment(pr, f"""## ❌ Analysis Error

```
{str(e)}
```

Check workflow logs.
""")
        raise
    
    # Parse and post results
    metadata = summary_result.get("metadata", {})
    language_analysis = summary_result.get("language_analysis", {})
    llm_summary = summary_result.get("llm_summary", {})
    architectural_analysis = summary_result.get("architectural_analysis", {})
    
    # Count issues
    total_issues = 0
    issues_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for lang, analysis in language_analysis.items():
        test_results = analysis.get("test_results", {})
        if test_results.get("summary", {}).get("failed", 0) > 0:
            issues_by_severity["high"] += test_results["summary"]["failed"]
            total_issues += test_results["summary"]["failed"]
        
        linting_results = analysis.get("linting_results", {})
        linting_issues = linting_results.get("summary", {}).get("total_issues", 0)
        total_issues += linting_issues
        issues_by_severity["medium"] += linting_issues
        
        security_results = analysis.get("security_results", {})
        security_issues = security_results.get("summary", {}).get("total_issues", 0)
        if security_issues > 0:
            issues_by_severity["critical"] += security_issues
            total_issues += security_issues
    
    arch_issues = architectural_analysis.get("anti_patterns_detected", [])
    for issue in arch_issues:
        severity = issue.get("severity", "medium").lower()
        issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
        total_issues += 1
    
    languages_str = ", ".join(metadata.get("languages_detected", []))
    risk_level = llm_summary.get("risk_assessment", "medium")
    pr_type = llm_summary.get("pr_type", "feature")
    
    result_comment = f"""## 🤖 PR Reviewer Agent - Analysis Complete

**Type:** {pr_type} | **Risk:** {risk_level}  
**Files:** {metadata.get('total_files_changed', 0)} | **Languages:** {languages_str}

### Issues Found
- 🔴 {issues_by_severity['critical']} critical
- 🟠 {issues_by_severity['high']} high
- 🟡 {issues_by_severity['medium']} medium
- ✅ {issues_by_severity['low']} low

**Total:** {total_issues} issues
"""
    
    if llm_summary:
        executive_summary = llm_summary.get("executive_summary", "")
        result_comment += f"""
### Summary
{executive_summary}

### Key Changes
"""
        for change in llm_summary.get("key_changes", [])[:5]:
            result_comment += f"- {change}\n"
    
    if arch_issues:
        result_comment += "\n### Architectural Issues\n"
        for issue in arch_issues[:3]:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.get("severity", "medium").lower(), "🟡")
            result_comment += f"{severity_emoji} **{issue.get('pattern_name', 'Unknown')}** - {issue.get('description', '')}\n"
    
    result_comment += """
---
🚦 **Next:** Comment `@pr-reviewer proceed` to create remediation plan
"""
    
    post_comment(pr, result_comment)
    
    # Save results
    results_dir = Path(".pr-reviewer/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "summary_result.json", "w") as f:
        json.dump(summary_result, f, indent=2)
    
    console.print("[green]✅ Analysis complete[/green]")
    return summary_result


async def run_proceed(pr, repo, context: str = ""):
    """Create plan using Planner agent"""
    console.print(Panel.fit("📋 CREATING PLAN", style="bold yellow"))
    
    post_comment(pr, """📋 **Creating Remediation Plan**

⏳ Analyzing issues...
""")
    
    results_dir = Path(".pr-reviewer/results")
    try:
        with open(results_dir / "summary_result.json", "r") as f:
            summary_result = json.load(f)
    except FileNotFoundError:
        console.print("[red]❌ Summary not found[/red]")
        post_comment(pr, "❌ **Error:** Run analysis first")
        return
    
    pr_info = get_pr_info(pr)
    pr_comments = get_pr_comments(pr)
    
    input_data = {
        "summary": summary_result,
        "pr_info": pr_info,
        "pr_comments": pr_comments,
        "human_context": context,
        "repository": repo.full_name
    }
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Planning...", total=None)
            
            plan_result = await call_agent_reasoner(
                agent="planner",
                reasoner="create_plan",
                input_data=input_data,
                timeout=180
            )
            
            progress.update(task, completed=True)
    
    except Exception as e:
        console.print(f"[red]❌ Planning failed: {e}[/red]")
        post_comment(pr, f"""## ❌ Planning Error

```
{str(e)}
```
""")
        raise
    
    total_fixes = plan_result.get("total_fixes", 0)
    by_priority = plan_result.get("by_priority", {})
    fixes = plan_result.get("fix_items", plan_result.get("fixes", []))
    estimated_time = plan_result.get("estimated_time_minutes", 0)
    
    context_note = f"\n**Your Context:** {context}\n" if context else ""
    
    plan_comment = f"""## 📋 Remediation Plan

{context_note}
**Fixes:** {total_fixes} | **Time:** {estimated_time} min

### By Priority
- 🔴 Critical: {by_priority.get('critical', 0)}
- 🟠 High: {by_priority.get('high', 0)}
- 🟡 Medium: {by_priority.get('medium', 0)}

### Plan
"""
    
    for i, fix in enumerate(fixes[:10], 1):
        priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(fix.get("priority", "medium"), "🟡")
        description = fix.get("description", "")
        time_est = fix.get("estimated_time_minutes", 5)
        plan_comment += f"{i}. {priority_emoji} {description} ({time_est} min)\n"
    
    if len(fixes) > 10:
        plan_comment += f"\n_...and {len(fixes) - 10} more_\n"
    
    plan_comment += """
---
🚦 **Next:** Comment `@pr-reviewer execute`
"""
    
    post_comment(pr, plan_comment)
    
    with open(results_dir / "plan_result.json", "w") as f:
        json.dump(plan_result, f, indent=2)
    
    console.print("[green]✅ Plan created[/green]")
    return plan_result


async def run_execute(pr, repo):
    """Execute fixes using Executor agent"""
    console.print(Panel.fit("⚙️ EXECUTING", style="bold blue"))
    
    post_comment(pr, """⚙️ **Executing Fixes**

⏳ Applying fixes...

This may take 10-15 minutes.
""")
    
    results_dir = Path(".pr-reviewer/results")
    try:
        with open(results_dir / "plan_result.json", "r") as f:
            plan_result = json.load(f)
    except FileNotFoundError:
        console.print("[red]❌ Plan not found[/red]")
        post_comment(pr, "❌ **Error:** Create plan first")
        return
    
    pr_info = get_pr_info(pr)
    
    input_data = {
        "plan": plan_result,
        "pr_info": pr_info,
        "repository": repo.full_name,
        "branch": pr_info["head_branch"]
    }
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Executing...", total=None)
            
            execution_result = await call_agent_reasoner(
                agent="executor",
                reasoner="execute_fixes",
                input_data=input_data,
                timeout=900
            )
            
            progress.update(task, completed=True)
    
    except Exception as e:
        console.print(f"[red]❌ Execution failed: {e}[/red]")
        post_comment(pr, f"""## ❌ Execution Error

```
{str(e)}
```
""")
        raise
    
    successful = execution_result.get("successful_fixes", execution_result.get("details", []))
    failed = execution_result.get("failed_fixes", [])
    changes = execution_result.get("changes_applied", execution_result.get("changes_made", {}))
    
    successful_count = len([s for s in successful if isinstance(s, dict) and s.get("status") == "success"])
    failed_count = len([f for f in successful if isinstance(f, dict) and f.get("status") == "failed"]) + len(failed)
    
    execute_comment = f"""## ⚙️ Execution Complete

✅ **Applied:** {successful_count}  
❌ **Failed:** {failed_count}

### Results
"""
    
    for fix in successful[:5]:
        if isinstance(fix, dict):
            desc = fix.get("description", fix.get("result", {}).get("message", "Fix applied"))
            execute_comment += f"- ✅ {desc}\n"
    
    if failed:
        execute_comment += "\n### Failed\n"
        for fix in failed[:3]:
            desc = fix.get("description", fix.get("error", "Unknown"))
            execute_comment += f"- ❌ {desc}\n"
    
    execute_comment += """
---
⏳ **Verifying...**
"""
    
    post_comment(pr, execute_comment)
    
    with open(results_dir / "execution_result.json", "w") as f:
        json.dump(execution_result, f, indent=2)
    
    console.print("[green]✅ Execution complete[/green]")
    
    await run_verify(pr, repo)
    return execution_result


async def run_verify(pr, repo):
    """Verify using Verifier agent"""
    console.print(Panel.fit("✅ VERIFYING", style="bold magenta"))
    
    results_dir = Path(".pr-reviewer/results")
    try:
        with open(results_dir / "summary_result.json", "r") as f:
            summary_result = json.load(f)
        with open(results_dir / "plan_result.json", "r") as f:
            plan_result = json.load(f)
        with open(results_dir / "execution_result.json", "r") as f:
            execution_result = json.load(f)
    except FileNotFoundError as e:
        console.print(f"[red]❌ Results missing: {e}[/red]")
        return
    
    pr_info = get_pr_info(pr)
    pr_comments = get_pr_comments(pr)
    
    input_data = {
        "original_summary": summary_result,
        "remediation_plan": plan_result,
        "execution_result": execution_result,
        "pr_info": pr_info,
        "pr_comments": pr_comments
    }
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Verifying...", total=None)
            
            verification_result = await call_agent_reasoner(
                agent="verifier",
                reasoner="verify_changes",
                input_data=input_data,
                timeout=300
            )
            
            progress.update(task, completed=True)
    
    except Exception as e:
        console.print(f"[red]❌ Verification failed: {e}[/red]")
        post_comment(pr, f"""## ❌ Verification Error

```
{str(e)}
```
""")
        raise
    
    ready_to_merge = verification_result.get("ready_to_merge", False)
    requires_replanning = verification_result.get("requires_replanning", False)
    feedback_alignment = verification_result.get("feedback_alignment_check", {})
    
    verify_comment = f"""## ✅ Verification Complete

**Status:** {"✅ Ready to merge" if ready_to_merge else "⚠️ Needs work"}

"""
    
    if feedback_alignment:
        alignment_score = feedback_alignment.get("alignment_score", 0)
        verify_comment += f"""
### Feedback Alignment
**Score:** {alignment_score}/100
"""
    
    if requires_replanning:
        verify_comment += """
⚠️ **Replanning required**

🔄 Creating updated plan...
"""
        post_comment(pr, verify_comment)
        
        console.print("[yellow]⚠️ Replanning...[/yellow]")
        context = "Address misalignments"
        await run_proceed(pr, repo, context)
        
    elif ready_to_merge:
        verify_comment += """
---
🚦 **Next:** Comment `@pr-reviewer merge`
"""
        post_comment(pr, verify_comment)
        
    else:
        verify_comment += """
---
🚦 Review issues and fix manually or modify plan
"""
        post_comment(pr, verify_comment)
    
    with open(results_dir / "verification_result.json", "w") as f:
        json.dump(verification_result, f, indent=2)
    
    console.print("[green]✅ Verification complete[/green]")
    return verification_result


async def run_merge(pr, repo):
    """Final approval"""
    console.print(Panel.fit("🚀 MERGE", style="bold green"))
    
    post_comment(pr, """🚀 **Final Check**

⏳ Verifying...
""")
    
    results_dir = Path(".pr-reviewer/results")
    try:
        with open(results_dir / "verification_result.json", "r") as f:
            verification_result = json.load(f)
    except FileNotFoundError:
        console.print("[yellow]⚠️ No verification, running...[/yellow]")
        await run_verify(pr, repo)
        with open(results_dir / "verification_result.json", "r") as f:
            verification_result = json.load(f)
    
    ready = verification_result.get("ready_to_merge", False)
    
    if not ready:
        post_comment(pr, """## ⚠️ Not Ready

Review verification results.
""")
        console.print("[yellow]⚠️ Not ready[/yellow]")
        return
    
    post_comment(pr, """## ✅ Ready to Merge!

**Final Check:** ✅ Passed

### Summary
- ✅ Tests passing
- ✅ No critical issues
- ✅ Quality improved
- ✅ Expectations met

---
✨ **Status:** Approved

Merge via GitHub UI when ready.

**Great work! 🎉**
""")
    
    console.print("[green]✅ Approved[/green]")


async def main():
    """Main orchestration"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--pr-number', type=int, required=True)
    parser.add_argument('--action', required=True, choices=['analyze', 'proceed', 'execute', 'merge'])
    parser.add_argument('--repo', required=True)
    parser.add_argument('--context', default='')
    args = parser.parse_args()

    console.print(f"\n[bold]Environment Check[/bold]")
    console.print(f"AGENTFIELD_SERVER: {AGENTFIELD_SERVER}")
    console.print(f"GITHUB_TOKEN: {'set' if os.getenv('GITHUB_TOKEN') else 'NOT SET'}")
    console.print(f"ANTHROPIC_API_KEY: {'set' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
    console.print()

    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        console.print("[red]❌ GITHUB_TOKEN not set[/red]")
        sys.exit(1)

    console.print("[bold]Checking AgentField connection...[/bold]")
    if not await check_agentfield_health():
        console.print(f"[red]❌ AgentField unavailable at {AGENTFIELD_SERVER}[/red]")
        console.print("[yellow]Tip: Ensure AgentField server is running and accessible[/yellow]")
        sys.exit(1)
    
    g = Github(github_token)
    repo = g.get_repo(args.repo)
    pr = repo.get_pull(args.pr_number)
    
    console.print(f"\n[bold cyan]🤖 PR Reviewer[/bold cyan]")
    console.print(f"PR #{pr.number}: {pr.title}")
    console.print(f"Action: {args.action}\n")
    
    try:
        if args.action == 'analyze':
            await run_analyze(pr, repo)
        elif args.action == 'proceed':
            await run_proceed(pr, repo, args.context)
        elif args.action == 'execute':
            await run_execute(pr, repo)
        elif args.action == 'merge':
            await run_merge(pr, repo)
        
        console.print("\n[bold green]✅ Complete![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        
        error_comment = f"""## ❌ Workflow Error

```
{str(e)}
```

Check [workflow logs](https://github.com/{args.repo}/actions).
"""
        try:
            post_comment(pr, error_comment)
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""
Executor Agent - Final Production Version
Executes remediation plans and applies fixes with human oversight
"""

from agentfield import AIConfig, Agent
from typing import Dict, List, Optional
import os
import subprocess
import json
from pathlib import Path
import shutil
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas import (
    TestFixSuggestion,
    LintingFixSuggestion,
    SecurityFixSuggestion,
    ExecutionSummary
)
from utils.llm_sanitizer import sanitize_llm_output

# Initialize Executor Agent
app = Agent(
    node_id="pr-reviewer-executor",
    agentfield_url=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
    ai_config=AIConfig(
        model=os.getenv("AI_MODEL", "openrouter/anthropic/claude-sonnet-4.5"),
        api_key=os.getenv("OPENROUTER_API_KEY"),  # or set OPENAI_API_KEY env var
    )
)


@app.skill()
def read_file(filepath: str) -> str:
    """
    Read contents of a file safely
    
    Args:
        filepath: Path to file
        
    Returns:
        File contents or error message
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


@app.skill()
def write_file(filepath: str, content: str) -> Dict:
    """
    Write content to a file safely
    
    Args:
        filepath: Path to file
        content: Content to write
        
    Returns:
        Result status
    """
    try:
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "filepath": filepath,
            "size": len(content)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filepath": filepath
        }


@app.skill()
def run_command(command: str, cwd: Optional[str] = None, timeout: int = 300) -> Dict:
    """
    Run a shell command safely
    
    Args:
        command: Command to run
        cwd: Working directory
        timeout: Timeout in seconds
        
    Returns:
        Command result with stdout, stderr, return code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "command": command
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command
        }


@app.skill()
def create_backup(filepath: str) -> Dict:
    """
    Create backup of a file before modifying
    
    Args:
        filepath: Path to file
        
    Returns:
        Backup info including backup path
    """
    try:
        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": f"File does not exist: {filepath}"
            }
        
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)
        
        return {
            "success": True,
            "backup_path": backup_path,
            "original_path": filepath,
            "timestamp": os.path.getmtime(filepath)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filepath": filepath
        }


@app.skill()
def restore_backup(backup_path: str) -> Dict:
    """
    Restore file from backup
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        Restore status
    """
    try:
        if not os.path.exists(backup_path):
            return {
                "success": False,
                "error": f"Backup file does not exist: {backup_path}"
            }
        
        original_path = backup_path.replace('.backup', '')
        shutil.copy2(backup_path, original_path)
        
        return {
            "success": True,
            "restored_path": original_path,
            "backup_path": backup_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.skill()
def git_diff(filepath: Optional[str] = None) -> str:
    """
    Get git diff for a file or all changes
    
    Args:
        filepath: Specific file to diff (optional)
        
    Returns:
        Git diff output
    """
    command = f"git diff {filepath}" if filepath else "git diff"
    result = run_command(command)
    return result.get('stdout', '')


@app.skill()
def apply_formatting(language: str, files: List[str]) -> Dict:
    """
    Apply automatic formatting to files
    
    Args:
        language: Programming language
        files: List of files to format
        
    Returns:
        Formatting results
    """
    results = {"formatted": [], "errors": [], "skipped": []}
    
    formatters = {
        "python": [{"cmd": "black", "args": []}, {"cmd": "isort", "args": []}],
        "go": [{"cmd": "gofmt", "args": ["-w"]}],
        "typescript": [{"cmd": "prettier", "args": ["--write"]}],
        "javascript": [{"cmd": "prettier", "args": ["--write"]}],
        "rust": [{"cmd": "rustfmt", "args": []}]
    }
    
    commands = formatters.get(language.lower(), [])
    
    if not commands:
        results['skipped'] = files
        return results
    
    for file in files:
        if not os.path.exists(file):
            results['errors'].append({'file': file, 'error': 'File not found'})
            continue
        
        for formatter in commands:
            cmd = f"{formatter['cmd']} {' '.join(formatter['args'])} {file}"
            result = run_command(cmd)
            
            if result['success']:
                results['formatted'].append(file)
            else:
                results['errors'].append({
                    'file': file,
                    'formatter': formatter['cmd'],
                    'error': result.get('stderr', 'Unknown error')
                })
    
    # Deduplicate formatted files
    results['formatted'] = list(set(results['formatted']))
    
    return results


@app.reasoner()
async def fix_test_failure(
    test_name: str,
    error_message: str,
    language: str,
    test_file: Optional[str] = None,
    source_files: Optional[List[str]] = None
) -> Dict:
    """
    Fix a failing test using AI assistance
    
    Args:
        test_name: Name of failing test
        error_message: Error message from test
        language: Programming language
        test_file: Path to test file
        source_files: Related source files
        
    Returns:
        Fix result with changes made
    """
    
    # Get context from files
    file_contents = {}
    
    if test_file and os.path.exists(test_file):
        file_contents[test_file] = read_file(test_file)
    
    if source_files:
        for file in source_files:
            if os.path.exists(file):
                file_contents[file] = read_file(file)
    
    # Use AI to analyze and suggest fix
    fix_prompt = f"""
    A test is failing and needs to be fixed:

    Test Name: {test_name}
    Language: {language}
    Error Message:
    {error_message}

    Available File Contents:
    {json.dumps({k: v[:2000] for k, v in file_contents.items()}, indent=2)}

    Analyze the error and provide a fix:
    1. Identify the root cause
    2. Determine which file(s) need modification
    3. Provide exact code changes

    Return as JSON:
    {{
        "root_cause": "explanation of why test is failing",
        "files_to_modify": ["list of file paths"],
        "changes": [
            {{
                "file": "path/to/file.py",
                "action": "replace",
                "line_number": 42,
                "old_code": "code to replace",
                "new_code": "corrected code",
                "explanation": "why this fixes it"
            }}
        ],
        "confidence": "low|medium|high",
        "test_after_fix": true,
        "additional_steps": ["any manual steps needed"]
    }}
    """

    # Use Pydantic schema for structured response
    fix_suggestion_raw = await app.ai(
        user=fix_prompt,
        schema=TestFixSuggestion
    )
    fix_suggestion = sanitize_llm_output(fix_suggestion_raw)

    # Create backups
    backups = []
    files_to_modify = fix_suggestion.get('files_to_modify', [])
    
    for file in files_to_modify:
        if os.path.exists(file):
            backup = create_backup(file)
            if backup['success']:
                backups.append(backup['backup_path'])
    
    # Apply changes
    applied_changes = []
    errors = []
    
    for change in fix_suggestion.get('changes', []):
        file = change['file']
        
        if not os.path.exists(file):
            errors.append({
                'file': file,
                'error': 'File does not exist'
            })
            continue
        
        try:
            content = read_file(file)
            
            if change['action'] == 'replace':
                old_code = change.get('old_code', '')
                new_code = change.get('new_code', '')
                
                if old_code in content:
                    new_content = content.replace(old_code, new_code)
                    write_result = write_file(file, new_content)
                    
                    if write_result['success']:
                        applied_changes.append({
                            'file': file,
                            'action': 'replace',
                            'explanation': change.get('explanation', ''),
                            'diff': git_diff(file)
                        })
                    else:
                        errors.append(write_result)
                else:
                    errors.append({
                        'file': file,
                        'error': 'Old code not found in file'
                    })
        
        except Exception as e:
            errors.append({
                'file': file,
                'error': str(e)
            })
    
    return {
        "test_name": test_name,
        "fix_applied": len(errors) == 0,
        "root_cause": fix_suggestion.get('root_cause', ''),
        "confidence": fix_suggestion.get('confidence', 'unknown'),
        "changes": applied_changes,
        "errors": errors,
        "backups": backups,
        "test_after_fix": fix_suggestion.get('test_after_fix', True),
        "additional_steps": fix_suggestion.get('additional_steps', [])
    }


@app.reasoner()
async def fix_linting_issue(
    issue: Dict,
    language: str
) -> Dict:
    """
    Fix a linting issue using AI
    
    Args:
        issue: Linting issue details (file, line, message)
        language: Programming language
        
    Returns:
        Fix result
    """
    
    file = issue.get('file', '')
    line = issue.get('line', 0)
    message = issue.get('message', '')
    
    if not os.path.exists(file):
        return {
            "issue": message,
            "fixed": False,
            "error": f"File not found: {file}"
        }
    
    # Get file context
    content = read_file(file)
    lines = content.split('\n')
    
    # Get context around the issue
    start_line = max(0, line - 10)
    end_line = min(len(lines), line + 10)
    context = '\n'.join(lines[start_line:end_line])
    
    # Use AI to fix
    fix_prompt = f"""
    Fix this linting issue:

    File: {file}
    Line: {line}
    Language: {language}
    Issue: {message}

    Code Context (lines {start_line}-{end_line}):
    ```
    {context}
    ```

    Provide the corrected code for this section.

    Return as JSON:
    {{
        "fixed_code": "corrected code for the section",
        "explanation": "what was fixed and why",
        "confidence": "low|medium|high"
    }}
    """

    # Use Pydantic schema for structured response
    fix_suggestion_raw = await app.ai(
        user=fix_prompt,
        schema=LintingFixSuggestion
    )
    fix_suggestion = sanitize_llm_output(fix_suggestion_raw)

    # Create backup
    backup = create_backup(file)
    
    # Apply fix
    if 'fixed_code' in fix_suggestion:
        new_lines = lines.copy()
        fixed_lines = fix_suggestion['fixed_code'].split('\n')
        new_lines[start_line:end_line] = fixed_lines
        new_content = '\n'.join(new_lines)
        
        write_result = write_file(file, new_content)
        
        return {
            "issue": message,
            "fixed": write_result['success'],
            "explanation": fix_suggestion.get('explanation', ''),
            "confidence": fix_suggestion.get('confidence', 'unknown'),
            "diff": git_diff(file) if write_result['success'] else None,
            "backup": backup.get('backup_path') if backup['success'] else None
        }
    
    return {
        "issue": message,
        "fixed": False,
        "error": "Could not generate fix"
    }


@app.reasoner()
async def fix_security_issue(
    issue: Dict,
    language: str
) -> Dict:
    """
    Fix a security issue using AI
    
    Args:
        issue: Security issue details
        language: Programming language
        
    Returns:
        Fix result with security explanation
    """
    
    file = issue.get('file', '')
    line = issue.get('line', 0)
    message = issue.get('message', '')
    severity = issue.get('severity', 'unknown')
    
    if not os.path.exists(file):
        return {
            "issue": message,
            "fixed": False,
            "error": f"File not found: {file}"
        }
    
    # Get file content
    content = read_file(file)
    
    # Use AI to analyze and fix
    fix_prompt = f"""
    Fix this security vulnerability:

    File: {file}
    Line: {line}
    Severity: {severity}
    Language: {language}
    Issue: {message}

    Full file content:
    ```
    {content[:5000]}  # Limit to first 5000 chars
    ```

    Provide a secure fix that properly addresses the vulnerability.

    Return as JSON:
    {{
        "vulnerability_type": "specific type of vulnerability",
        "risk_explanation": "why this is dangerous",
        "fix_strategy": "high-level approach to fixing",
        "fixed_code": "complete fixed file content",
        "security_best_practices": ["practices applied"],
        "additional_steps": ["any other security measures needed"],
        "confidence": "low|medium|high"
    }}
    """

    # Use Pydantic schema for structured response
    fix_suggestion_raw = await app.ai(
        user=fix_prompt,
        schema=SecurityFixSuggestion
    )
    fix_suggestion = sanitize_llm_output(fix_suggestion_raw)
    
    # Create backup
    backup = create_backup(file)
    
    # Apply fix
    if 'fixed_code' in fix_suggestion:
        write_result = write_file(file, fix_suggestion['fixed_code'])
        
        return {
            "issue": message,
            "severity": severity,
            "fixed": write_result['success'],
            "vulnerability_type": fix_suggestion.get('vulnerability_type', 'unknown'),
            "risk_explanation": fix_suggestion.get('risk_explanation', ''),
            "fix_strategy": fix_suggestion.get('fix_strategy', ''),
            "security_best_practices": fix_suggestion.get('security_best_practices', []),
            "diff": git_diff(file) if write_result['success'] else None,
            "additional_steps": fix_suggestion.get('additional_steps', []),
            "confidence": fix_suggestion.get('confidence', 'unknown'),
            "backup": backup.get('backup_path') if backup['success'] else None
        }
    
    return {
        "issue": message,
        "fixed": False,
        "error": "Could not generate secure fix"
    }


@app.reasoner()
async def execute_remediation_plan(plan: Dict) -> Dict:
    """
    Main reasoning function: Execute complete remediation plan
    
    This agent:
    1. Processes each fix item in priority order
    2. Uses AI to generate fixes
    3. Applies changes with backups
    4. Tracks successes and failures
    5. Handles rollback if needed
    
    Args:
        plan: Remediation plan from planner agent
        
    Returns:
        Execution results with all fixes attempted
    """
    
    results = {
        "total_fixes": len(plan.get('fix_items', [])),
        "successful_fixes": 0,
        "failed_fixes": 0,
        "skipped_fixes": 0,
        "details": [],
        "backups_created": [],
        "changes_applied": [],
        "time_taken": 0
    }
    
    fix_items = plan.get('fix_items', [])
    
    if not fix_items:
        return {
            "status": "success",
            "message": "No fixes to apply",
            "total_fixes": 0
        }
    
    # Process each fix item
    for idx, fix_item in enumerate(fix_items):
        category = fix_item['category']
        details = fix_item['details']
        language = fix_item.get('language', 'unknown')
        fix_id = fix_item.get('id', f"fix_{idx}")
        
        print(f"Processing fix {idx+1}/{len(fix_items)}: {fix_item['description']}")
        
        try:
            if category == 'test_fix':
                # Fix test failure
                fix_result = await fix_test_failure(
                    test_name=details.get('test', 'unknown'),
                    error_message=details.get('error', ''),
                    language=language,
                    test_file=details.get('file'),
                    source_files=[]
                )
                
                if fix_result['fix_applied']:
                    results['successful_fixes'] += 1
                else:
                    results['failed_fixes'] += 1
                
                results['details'].append({
                    'fix_id': fix_id,
                    'category': category,
                    'status': 'success' if fix_result['fix_applied'] else 'failed',
                    'result': fix_result
                })
                
                if fix_result.get('backups'):
                    results['backups_created'].extend(fix_result['backups'])
                
                if fix_result.get('changes'):
                    results['changes_applied'].extend(fix_result['changes'])
            
            elif category == 'code_quality':
                # Fix linting issue
                fix_result = await fix_linting_issue(details, language)
                
                if fix_result['fixed']:
                    results['successful_fixes'] += 1
                else:
                    results['failed_fixes'] += 1
                
                results['details'].append({
                    'fix_id': fix_id,
                    'category': category,
                    'status': 'success' if fix_result['fixed'] else 'failed',
                    'result': fix_result
                })
                
                if fix_result.get('backup'):
                    results['backups_created'].append(fix_result['backup'])
            
            elif category == 'security':
                # Fix security issue
                fix_result = await fix_security_issue(details, language)
                
                if fix_result['fixed']:
                    results['successful_fixes'] += 1
                else:
                    results['failed_fixes'] += 1
                
                results['details'].append({
                    'fix_id': fix_id,
                    'category': category,
                    'status': 'success' if fix_result['fixed'] else 'failed',
                    'result': fix_result
                })
                
                if fix_result.get('backup'):
                    results['backups_created'].append(fix_result['backup'])
        
        except Exception as e:
            results['failed_fixes'] += 1
            results['details'].append({
                'fix_id': fix_id,
                'category': category,
                'status': 'error',
                'error': str(e)
            })
    
    # Use AI to summarize execution
    summary_prompt = f"""
    Summarize this remediation execution for human review:

    Total attempted: {results['total_fixes']}
    Successful: {results['successful_fixes']}
    Failed: {results['failed_fixes']}

    Sample results:
    {json.dumps(results['details'][:5], indent=2)}

    Provide a brief 2-3 sentence summary explaining:
    - What was accomplished
    - Any failures and why
    - Next steps if needed
    """

    # Use Pydantic schema for structured summary
    summary_response_raw = await app.ai(
        user=summary_prompt,
        schema=ExecutionSummary
    )
    summary_response = sanitize_llm_output(summary_response_raw)
    results['summary'] = summary_response
    results['status'] = 'success' if results['failed_fixes'] == 0 else 'partial'
    
    return results


@app.reasoner()
async def rollback_changes(backups: List[str]) -> Dict:
    """
    Rollback changes using backup files
    
    Args:
        backups: List of backup file paths
        
    Returns:
        Rollback results
    """
    results = {
        "total": len(backups),
        "restored": 0,
        "failed": 0,
        "details": []
    }
    
    for backup_path in backups:
        restore_result = restore_backup(backup_path)
        
        if restore_result['success']:
            results['restored'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append(restore_result)
    
    return results


if __name__ == "__main__":
    # Run the agent - it will register with the control plane
    app.run()

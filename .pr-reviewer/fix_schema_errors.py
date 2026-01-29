#!/usr/bin/env python3
"""
Script to fix "compiled grammar too large" errors in all PR reviewer agents.

This script replaces schema= parameter usage with manual JSON parsing to avoid
the Anthropic API error that occurs when using complex Pydantic schemas with
many registered tools.

Usage:
    python fix_schema_errors.py
"""

import re
from pathlib import Path


def fix_agent_file(filepath: Path) -> bool:
    """
    Fix schema= usage in an agent file.

    Args:
        filepath: Path to agent file

    Returns:
        True if changes were made
    """
    print(f"Processing {filepath.name}...")

    content = filepath.read_text(encoding='utf-8')
    original_content = content

    # Step 1: Add parse_ai_json_response to imports if not already there
    if 'from utils.llm_sanitizer import' in content:
        if 'parse_ai_json_response' not in content:
            content = re.sub(
                r'from utils\.llm_sanitizer import ([^\n]+)',
                r'from utils.llm_sanitizer import \1, parse_ai_json_response',
                content
            )
            print(f"  ✓ Added parse_ai_json_response to imports")

    # Step 2: Find and replace all schema= usage patterns
    # Pattern: await app.ai(..., schema=SomeSchema)

    # This regex finds:
    # - await app.ai(
    # - optional parameters before schema
    # - schema=SomeName
    # - closing parenthesis
    pattern = r'(await app\.ai\([^)]*?)(,\s*schema=\w+)(\s*\))'

    def replace_schema_call(match):
        before_schema = match.group(1)
        schema_param = match.group(2)
        after_schema = match.group(3)

        # Remove schema parameter
        result = before_schema + after_schema

        # Add instruction to return JSON
        if 'user=' in before_schema:
            # Add JSON instruction to the user prompt
            result = result.replace(
                ')',
                ' + "\\n\\nReturn ONLY valid JSON. No markdown, no explanations.")'
            )

        return result

    new_content = re.sub(pattern, replace_schema_call, content)

    if new_content != content:
        print(f"  ✓ Removed schema= parameters")
        content = new_content

    # Step 3: Wrap AI calls with parse_ai_json_response
    # Find pattern: variable = await app.ai(...)
    # Replace with: variable_raw = await app.ai(...); variable = parse_ai_json_response(variable_raw)

    # Pattern to find: var_name = await app.ai(...)
    pattern = r'(\w+)\s*=\s*(await app\.ai\([^)]+\))'

    def wrap_with_parser(match):
        var_name = match.group(1)
        ai_call = match.group(2)

        # Check if this was a schema call (has JSON instruction)
        if 'Return ONLY valid JSON' in ai_call:
            return f'{var_name}_raw = {ai_call}\n    {var_name} = parse_ai_json_response({var_name}_raw)'

        return match.group(0)  # No change

    new_content = re.sub(pattern, wrap_with_parser, content, flags=re.MULTILINE)

    if new_content != content:
        print(f"  ✓ Wrapped AI calls with parse_ai_json_response")
        content = new_content

    # Step 4: Remove sanitize_llm_output calls after parse_ai_json_response
    # parse_ai_json_response already calls sanitize_llm_output internally
    content = re.sub(
        r'(\w+) = parse_ai_json_response\((\w+)\)\s*\n\s*\1 = sanitize_llm_output\(\1\)',
        r'\1 = parse_ai_json_response(\2)',
        content
    )

    # Write back if changes were made
    if content != original_content:
        filepath.write_text(content, encoding='utf-8')
        print(f"  ✓ Fixed {filepath.name}")
        return True
    else:
        print(f"  - No changes needed for {filepath.name}")
        return False


def main():
    """Fix all agent files."""
    agents_dir = Path(__file__).parent / 'agents'

    if not agents_dir.exists():
        print(f"Error: agents directory not found at {agents_dir}")
        return

    agent_files = list(agents_dir.glob('*_agent.py'))

    print(f"Found {len(agent_files)} agent files\n")

    fixed_count = 0
    for agent_file in agent_files:
        if fix_agent_file(agent_file):
            fixed_count += 1
        print()

    print(f"\nSummary: Fixed {fixed_count}/{len(agent_files)} agent files")
    print("\n✅ All agents updated to avoid 'compiled grammar too large' error")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Test script for analyze_code_complexity refactoring
Tests the new configuration-based complexity analysis
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_loader import config
from utils.tool_checker import ToolChecker


def test_config_loading():
    """Test configuration loading"""
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)

    max_cyclomatic = config.get_max_cyclomatic_complexity()
    max_cognitive = config.get_max_cognitive_complexity()
    code_analysis_tools = config.get_code_analysis_tools()

    print(f"[OK] Max Cyclomatic Complexity: {max_cyclomatic}")
    print(f"[OK] Max Cognitive Complexity: {max_cognitive}")
    print(f"[OK] Code Analysis Tools: {code_analysis_tools}")
    print()


def test_tool_checking():
    """Test tool availability checking"""
    print("=" * 60)
    print("Testing Tool Availability Checking")
    print("=" * 60)

    # Test Python tools
    print("\nPython (.py) tools:")
    py_tools = ToolChecker.get_available_tools_for_extension('.py')
    print(f"  Available: {py_tools if py_tools else 'None'}")

    all_py_tools = ToolChecker.COMPLEXITY_TOOLS.get('.py', [])
    for tool in all_py_tools:
        status = "[OK] Installed" if ToolChecker.is_tool_installed(tool) else "[X] Not installed"
        install_cmd = ToolChecker.get_tool_install_command(tool)
        print(f"  {tool}: {status}")
        if "Not installed" in status:
            print(f"    Install: {install_cmd}")

    # Test Go tools
    print("\nGo (.go) tools:")
    go_tools = ToolChecker.get_available_tools_for_extension('.go')
    print(f"  Available: {go_tools if go_tools else 'None'}")

    all_go_tools = ToolChecker.COMPLEXITY_TOOLS.get('.go', [])
    for tool in all_go_tools:
        status = "[OK] Installed" if ToolChecker.is_tool_installed(tool) else "[X] Not installed"
        install_cmd = ToolChecker.get_tool_install_command(tool)
        print(f"  {tool}: {status}")
        if "Not installed" in status:
            print(f"    Install: {install_cmd}")

    # Test JavaScript tools
    print("\nJavaScript (.js) tools:")
    js_tools = ToolChecker.get_available_tools_for_extension('.js')
    print(f"  Available: {js_tools if js_tools else 'None'}")

    all_js_tools = ToolChecker.COMPLEXITY_TOOLS.get('.js', [])
    for tool in all_js_tools:
        status = "[OK] Installed" if ToolChecker.is_tool_installed(tool) else "[X] Not installed"
        install_cmd = ToolChecker.get_tool_install_command(tool)
        print(f"  {tool}: {status}")
        if "Not installed" in status:
            print(f"    Install: {install_cmd}")

    print()


def test_all_supported_languages():
    """Show all supported languages and their tools"""
    print("=" * 60)
    print("All Supported Languages")
    print("=" * 60)

    for ext, tools in ToolChecker.COMPLEXITY_TOOLS.items():
        print(f"\n{ext} files:")
        print(f"  Supported tools: {', '.join(tools)}")
        available = ToolChecker.get_available_tools_for_extension(ext)
        if available:
            print(f"  [OK] Available: {', '.join(available)}")
        else:
            print(f"  [X] No tools installed")

    print()


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PR-Reviewer Complexity Analysis Tool Check")
    print("=" * 60 + "\n")

    test_config_loading()
    test_tool_checking()
    test_all_supported_languages()

    print("=" * 60)
    print("Test Complete")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Install missing tools for languages you want to analyze")
    print("2. Run: python test_complexity_analysis.py")
    print("3. Verify tools are detected correctly")
    print()


if __name__ == "__main__":
    main()

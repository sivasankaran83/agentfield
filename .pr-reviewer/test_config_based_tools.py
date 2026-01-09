"""
Test script to verify configuration-based tool checking and auto-installation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_config_loading():
    """Test that tools are loaded from config.yml"""
    from utils.tool_checker import ToolChecker

    print("=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)

    config_data = ToolChecker._load_config()

    print(f"Auto-install enabled: {config_data.get('auto_install', False)}")
    print(f"\nLanguages configured: {[k for k in config_data.keys() if k != 'auto_install']}")

    # Test that we can get tools for each extension
    for ext, lang in ToolChecker.EXT_TO_LANG.items():
        tools = ToolChecker._get_tools_for_extension(ext)
        print(f"  {ext} ({lang}): {tools}")

    print("\n[OK] Configuration loaded successfully from config.yml")
    return True


def test_tool_checking():
    """Test tool availability checking"""
    from utils.tool_checker import ToolChecker

    print("\n" + "=" * 60)
    print("TEST 2: Tool Availability Checking")
    print("=" * 60)

    # Check tools for each language
    for ext, lang in ToolChecker.EXT_TO_LANG.items():
        print(f"\n{lang.upper()} ({ext}):")
        tools = ToolChecker._get_tools_for_extension(ext)

        if not tools:
            print("  No tools configured")
            continue

        for tool in tools:
            is_installed = ToolChecker.is_tool_installed(tool)
            status = "[OK] Installed" if is_installed else "[X] Not installed"
            print(f"  {tool}: {status}")

            if not is_installed:
                install_cmd = ToolChecker.get_tool_install_command(tool, lang)
                print(f"    Install: {install_cmd}")

    print("\n[OK] Tool checking complete")
    return True


def test_get_install_command():
    """Test getting install commands from config"""
    from utils.tool_checker import ToolChecker

    print("\n" + "=" * 60)
    print("TEST 3: Install Command Retrieval")
    print("=" * 60)

    test_cases = [
        ('radon', 'python'),
        ('gocyclo', 'go'),
        ('eslint', 'javascript'),
        ('lizard', 'cpp'),
    ]

    for tool, lang in test_cases:
        cmd = ToolChecker.get_tool_install_command(tool, lang)
        print(f"{tool} ({lang}): {cmd}")

    print("\n[OK] Install commands retrieved from config.yml")
    return True


def test_check_all_tools():
    """Test checking all configured tools"""
    from utils.tool_checker import ToolChecker

    print("\n" + "=" * 60)
    print("TEST 4: Check All Configured Tools")
    print("=" * 60)

    all_tools = ToolChecker.check_all_tools()

    installed_count = sum(1 for installed in all_tools.values() if installed)
    total_count = len(all_tools)

    print(f"\nTotal tools configured: {total_count}")
    print(f"Tools installed: {installed_count}")
    print(f"Tools missing: {total_count - installed_count}")

    print("\nInstalled tools:")
    for tool, installed in sorted(all_tools.items()):
        if installed:
            print(f"  [OK] {tool}")

    print("\nMissing tools:")
    for tool, installed in sorted(all_tools.items()):
        if not installed:
            print(f"  [X] {tool}")

    print("\n[OK] All tools checked")
    return True


def test_auto_install_status():
    """Test auto-install configuration status"""
    from utils.tool_checker import ToolChecker

    print("\n" + "=" * 60)
    print("TEST 5: Auto-Install Configuration")
    print("=" * 60)

    config_data = ToolChecker._load_config()
    auto_install = config_data.get('auto_install', False)

    if auto_install:
        print("[ENABLED] Auto-installation is ENABLED in config.yml")
        print("  Missing tools will be automatically installed when needed")
    else:
        print("[DISABLED] Auto-installation is DISABLED in config.yml")
        print("  Missing tools will NOT be automatically installed")
        print("  To enable, set 'auto_install: true' in config.yml")

    print("\n[OK] Auto-install status checked")
    return True


def main():
    """Run all tests"""
    print("\nTesting Configuration-Based Tool Checking System")
    print("=" * 60)

    tests = [
        test_config_loading,
        test_tool_checking,
        test_get_install_command,
        test_check_all_tools,
        test_auto_install_status,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test to verify handshake_test.py is cross-platform compatible.
This test verifies that:
1. No hardcoded Windows paths are present
2. sys.executable is used for Python interpreter
3. Path objects are used for file paths
"""

import sys
from pathlib import Path
import re


def test_no_hardcoded_paths():
    """Verify no hardcoded Windows paths in handshake_test.py"""
    test_file = Path(__file__).parent / "handshake_test.py"

    if not test_file.exists():
        print(f"❌ FAIL: {test_file} not found")
        return False

    content = test_file.read_text()

    # Check for Windows-style hardcoded paths
    windows_path_patterns = [
        r'C:\\',
        r'[A-Z]:\\',
        r'\\Users\\',
        r'\\Documents\\',
        r'\\AppData\\',
    ]

    found_issues = []
    for pattern in windows_path_patterns:
        matches = re.findall(pattern, content)
        if matches:
            found_issues.append(f"Found Windows path pattern: {pattern}")

    if found_issues:
        print("❌ FAIL: Hardcoded Windows paths detected:")
        for issue in found_issues:
            print(f"  - {issue}")
        return False

    print("✓ PASS: No hardcoded Windows paths found")
    return True


def test_uses_sys_executable():
    """Verify sys.executable is used for Python interpreter"""
    test_file = Path(__file__).parent / "handshake_test.py"
    content = test_file.read_text()

    if "sys.executable" in content:
        print("✓ PASS: Uses sys.executable")
        return True
    else:
        print("❌ FAIL: Does not use sys.executable")
        return False


def test_imports_pathlib():
    """Verify pathlib is imported"""
    test_file = Path(__file__).parent / "handshake_test.py"
    content = test_file.read_text()

    if "from pathlib import Path" in content or "import pathlib" in content:
        print("✓ PASS: Imports pathlib")
        return True
    else:
        print("❌ FAIL: Does not import pathlib")
        return False


def test_uses_path_objects():
    """Verify Path objects are used for file paths"""
    test_file = Path(__file__).parent / "handshake_test.py"
    content = test_file.read_text()

    if "Path(__file__)" in content:
        print("✓ PASS: Uses Path objects for relative paths")
        return True
    else:
        print("❌ FAIL: Does not use Path objects")
        return False


def test_variables_renamed():
    """Verify variables are named appropriately"""
    test_file = Path(__file__).parent / "handshake_test.py"
    content = test_file.read_text()

    # Should have PYTHON_EXE and SERVER_PATH instead of COMMAND and SERVER
    has_python_exe = "PYTHON_EXE" in content
    has_server_path = "SERVER_PATH" in content

    # Check that old variable names are not used
    old_command_pattern = r'COMMAND\s*=\s*r"C:\\'
    old_server_pattern = r'SERVER\s*=\s*r"C:\\'
    has_old_command = re.search(old_command_pattern, content)
    has_old_server = re.search(old_server_pattern, content)

    if has_python_exe and has_server_path and not has_old_command and not has_old_server:
        print("✓ PASS: Variables renamed to PYTHON_EXE and SERVER_PATH")
        return True
    else:
        print("❌ FAIL: Variables not properly renamed")
        if not has_python_exe:
            print("  - Missing PYTHON_EXE")
        if not has_server_path:
            print("  - Missing SERVER_PATH")
        if has_old_command:
            print("  - Still has old COMMAND variable")
        if has_old_server:
            print("  - Still has old SERVER variable")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Cross-Platform Compatibility Test for handshake_test.py")
    print("=" * 60)
    print()

    tests = [
        test_no_hardcoded_paths,
        test_uses_sys_executable,
        test_imports_pathlib,
        test_uses_path_objects,
        test_variables_renamed,
    ]

    results = []
    for test in tests:
        print(f"\nRunning: {test.__name__}")
        print("-" * 60)
        results.append(test())

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests PASSED! handshake_test.py is cross-platform compatible.")
        return 0
    else:
        print("\n❌ Some tests FAILED. Please review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

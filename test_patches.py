#!/usr/bin/env python3
"""
Test script to verify all patches are correctly applied and functional.
"""

import sys
import asyncio
from pathlib import Path

def test_patch_1_cross_platform_paths():
    """Test PATCH 1: Cross-platform paths in validate_mcp.py"""
    print("\n=== Testing PATCH 1: Cross-platform paths ===")

    # Read validate_mcp.py
    content = Path("/home/user/MCP/validate_mcp.py").read_text()

    # Check that hardcoded paths are removed
    assert 'r"C:\\Users\\Admin' not in content, "FAIL: Hardcoded Windows path still present"
    assert 'sys.executable' in content, "FAIL: sys.executable not found"
    assert 'Path(__file__).parent' in content, "FAIL: Path(__file__).parent not found"

    print("✓ Hardcoded Windows paths removed")
    print("✓ sys.executable is used for COMMAND")
    print("✓ Path(__file__).parent is used for SERVER_SCRIPT")
    print("PATCH 1: PASSED")
    return True

def test_patch_2_async_redis():
    """Test PATCH 2: Async Redis connection in server.py"""
    print("\n=== Testing PATCH 2: Async Redis connection ===")

    # Read server.py
    content = Path("/home/user/MCP/server.py").read_text()

    # Check that blocking ping is removed from module level
    lines = content.split('\n')

    # Find the Redis client initialization section
    found_async_check = False
    found_blocking_ping_removed = True
    found_startup_call = False

    for i, line in enumerate(lines):
        # Check for the async function
        if 'async def _check_redis_connection' in line:
            found_async_check = True

        # Check that we don't have blocking ping at module level (lines 67-82)
        if i in range(66, 91):  # Around the old blocking section
            if 'redis_client.ping()' in line and 'await' not in line:
                # Make sure it's not in the async function
                if 'async def _check_redis_connection' not in '\n'.join(lines[max(0,i-15):i]):
                    found_blocking_ping_removed = False

        # Check that _check_redis_connection is called in main
        if 'await _check_redis_connection()' in line:
            found_startup_call = True

    assert found_async_check, "FAIL: _check_redis_connection() function not found"
    assert found_blocking_ping_removed, "FAIL: Blocking ping() still present at module level"
    assert found_startup_call, "FAIL: _check_redis_connection() not called in main()"

    print("✓ Blocking redis_client.ping() removed from module initialization")
    print("✓ async _check_redis_connection() function added")
    print("✓ _check_redis_connection() called during startup in main()")
    print("PATCH 2: PASSED")
    return True

def test_patch_3_requirements():
    """Test PATCH 3: requirements.txt exists and has correct dependencies"""
    print("\n=== Testing PATCH 3: requirements.txt ===")

    req_file = Path("/home/user/MCP/requirements.txt")
    assert req_file.exists(), "FAIL: requirements.txt not found"

    content = req_file.read_text()

    required_deps = [
        'mcp[cli]',
        'numpy',
        'scipy',
        'sympy',
        'redis',
        'sentence-transformers',
        'anyio'
    ]

    for dep in required_deps:
        assert dep in content, f"FAIL: {dep} not in requirements.txt"
        print(f"✓ {dep} is listed")

    print("PATCH 3: PASSED")
    return True

def test_patch_4_env_example():
    """Test PATCH 4: .env.example exists with correct configuration"""
    print("\n=== Testing PATCH 4: .env.example ===")

    env_file = Path("/home/user/MCP/.env.example")
    assert env_file.exists(), "FAIL: .env.example not found"

    content = env_file.read_text()

    required_vars = [
        'MCP_MEMORY_REDIS_HOST',
        'MCP_MEMORY_REDIS_PORT',
        'MCP_MEMORY_REDIS_DB',
        'MCP_RUNTIME_ALLOW_SHELL',
        'MCP_EMBED_MODEL',
        'MCP_EMBED_DIM',
        'MCP_INDEX_MAX_SIZE',
        'MCP_INDEX_MAX_CHARS'
    ]

    for var in required_vars:
        assert var in content, f"FAIL: {var} not in .env.example"
        print(f"✓ {var} is documented")

    print("PATCH 4: PASSED")
    return True

def test_backward_compatibility():
    """Test that all patches maintain backward compatibility"""
    print("\n=== Testing Backward Compatibility ===")

    # Test that server.py still has all the same tool functions
    server_content = Path("/home/user/MCP/server.py").read_text()

    tools = [
        'def ping()',
        'def echo(',
        'def server_status()',
        'def column_stats(',
        'def normalize(',
        'def shell(',
        'def set_memory(',
        'def get_memory(',
    ]

    for tool in tools:
        assert tool in server_content, f"FAIL: Tool {tool} not found - breaking change!"
        print(f"✓ {tool} still exists")

    print("✓ All existing tools preserved")
    print("BACKWARD COMPATIBILITY: PASSED")
    return True

def main():
    """Run all patch tests"""
    print("=" * 60)
    print("PATCH VERIFICATION TEST SUITE")
    print("=" * 60)

    results = []

    try:
        results.append(("PATCH 1: Cross-platform paths", test_patch_1_cross_platform_paths()))
    except AssertionError as e:
        print(f"PATCH 1 FAILED: {e}")
        results.append(("PATCH 1", False))

    try:
        results.append(("PATCH 2: Async Redis", test_patch_2_async_redis()))
    except AssertionError as e:
        print(f"PATCH 2 FAILED: {e}")
        results.append(("PATCH 2", False))

    try:
        results.append(("PATCH 3: requirements.txt", test_patch_3_requirements()))
    except AssertionError as e:
        print(f"PATCH 3 FAILED: {e}")
        results.append(("PATCH 3", False))

    try:
        results.append(("PATCH 4: .env.example", test_patch_4_env_example()))
    except AssertionError as e:
        print(f"PATCH 4 FAILED: {e}")
        results.append(("PATCH 4", False))

    try:
        results.append(("Backward Compatibility", test_backward_compatibility()))
    except AssertionError as e:
        print(f"Backward Compatibility FAILED: {e}")
        results.append(("Backward Compatibility", False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL PATCHES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

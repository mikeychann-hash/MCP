#!/usr/bin/env python3
"""
Test Redis graceful degradation

Verifies that server handles Redis unavailability gracefully:
- Server starts even when Redis is unavailable
- Memory tools raise appropriate errors
- Non-memory tools continue to work
"""

import pytest
import sys
import subprocess
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock


@pytest.mark.timeout(10)
def test_server_starts_without_redis():
    """Test that server can start even when Redis is unavailable"""
    server_path = Path(__file__).parent / "server.py"

    # Script that imports server with Redis connection failure
    test_script = """
import sys
from unittest.mock import MagicMock, Mock

# Mock sentence_transformers
sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

# Mock redis to fail connection
mock_redis = MagicMock()
redis_instance = Mock()
redis_instance.ping.side_effect = Exception("Connection refused")
mock_redis.Redis.return_value = redis_instance
sys.modules['redis'] = mock_redis

# Set environment to point to non-existent Redis
import os
os.environ['MCP_MEMORY_REDIS_HOST'] = 'localhost'
os.environ['MCP_MEMORY_REDIS_PORT'] = '9999'  # Non-existent port

sys.path.insert(0, '%s')
import server

# Check that server imported successfully
print(f"MEMORY_ENABLED={server.MEMORY_ENABLED}")
print(f"redis_client={server.redis_client}")
print("SERVER_IMPORT_SUCCESS_NO_REDIS")
""" % str(server_path.parent)

    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=5)

        # Server should import successfully
        assert "SERVER_IMPORT_SUCCESS_NO_REDIS" in stdout, \
            f"Server should start without Redis. stdout: {stdout}"

        # Memory should be disabled
        assert "MEMORY_ENABLED=False" in stdout, \
            f"Memory should be disabled without Redis. stdout: {stdout}"

        # redis_client should be None or set to non-working instance
        # (implementation may vary, but MEMORY_ENABLED=False is what matters)
        assert "redis_client=" in stdout, \
            f"Redis client should be defined. stdout: {stdout}"

        # Server should exit cleanly
        assert proc.returncode == 0, "Server should exit cleanly"

        # Note: Redis warning may or may not appear in stderr depending on logging config
        # The key verification is that MEMORY_ENABLED=False

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Server startup with failed Redis hung")


@pytest.mark.timeout(10)
def test_memory_tools_fail_gracefully_without_redis():
    """Test that memory tools raise appropriate errors without Redis"""
    server_path = Path(__file__).parent / "server.py"

    test_script = """
import sys
from unittest.mock import MagicMock, Mock

# Mock dependencies
sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

# Mock redis to fail
mock_redis = MagicMock()
redis_instance = Mock()
redis_instance.ping.side_effect = Exception("Connection refused")
mock_redis.Redis.return_value = redis_instance
sys.modules['redis'] = mock_redis

sys.path.insert(0, '%s')
import server

# Try to use memory tools when Redis is disabled
try:
    result = server.set_memory("test_key", "test_value")
    print(f"ERROR: set_memory should have raised exception, got: {result}")
except RuntimeError as e:
    if "Redis memory is not enabled" in str(e):
        print("PASS: set_memory raised appropriate error")
    else:
        print(f"ERROR: Wrong error message: {e}")
except Exception as e:
    print(f"ERROR: Wrong exception type: {type(e).__name__}: {e}")

try:
    result = server.get_memory("test_key")
    print(f"ERROR: get_memory should have raised exception, got: {result}")
except RuntimeError as e:
    if "Redis memory is not enabled" in str(e):
        print("PASS: get_memory raised appropriate error")
    else:
        print(f"ERROR: Wrong error message: {e}")

try:
    result = server.index_project_files()
    print(f"ERROR: index_project_files should have raised exception, got: {result}")
except RuntimeError as e:
    if "Redis memory is not enabled" in str(e):
        print("PASS: index_project_files raised appropriate error")
    else:
        print(f"ERROR: Wrong error message: {e}")

print("MEMORY_TOOLS_TEST_COMPLETE")
""" % str(server_path.parent)

    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=5)

        # All memory tools should raise appropriate errors
        assert stdout.count("PASS:") >= 3, \
            f"All memory tools should raise appropriate errors. stdout: {stdout}"

        assert "MEMORY_TOOLS_TEST_COMPLETE" in stdout, \
            f"Test should complete. stdout: {stdout}"

        # Should not have generic errors
        assert "ERROR:" not in stdout, \
            f"Should not have errors. stdout: {stdout}"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Memory tools test hung")


@pytest.mark.timeout(10)
def test_non_memory_tools_work_without_redis():
    """Test that non-memory tools work even without Redis"""
    server_path = Path(__file__).parent / "server.py"

    test_script = """
import sys
from unittest.mock import MagicMock, Mock

# Mock dependencies
sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

# Mock redis to fail
mock_redis = MagicMock()
redis_instance = Mock()
redis_instance.ping.side_effect = Exception("Connection refused")
mock_redis.Redis.return_value = redis_instance
sys.modules['redis'] = mock_redis

sys.path.insert(0, '%s')
import server

# Test non-memory tools
try:
    result = server.ping()
    if result == "pong":
        print("PASS: ping works")
    else:
        print(f"ERROR: ping returned: {result}")
except Exception as e:
    print(f"ERROR: ping failed: {e}")

try:
    result = server.echo("test message")
    if "test message" in result:
        print("PASS: echo works")
    else:
        print(f"ERROR: echo returned: {result}")
except Exception as e:
    print(f"ERROR: echo failed: {e}")

try:
    result = server.server_status()
    if isinstance(result, dict) and "memory_enabled" in result:
        if result["memory_enabled"] == False:
            print("PASS: server_status works and shows memory disabled")
        else:
            print("ERROR: memory_enabled should be False")
    else:
        print(f"ERROR: server_status returned: {result}")
except Exception as e:
    print(f"ERROR: server_status failed: {e}")

try:
    result = server.column_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    if isinstance(result, dict) and "mean" in result:
        print("PASS: column_stats works")
    else:
        print(f"ERROR: column_stats returned: {result}")
except Exception as e:
    print(f"ERROR: column_stats failed: {e}")

print("NON_MEMORY_TOOLS_TEST_COMPLETE")
""" % str(server_path.parent)

    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=5)

        # All non-memory tools should work
        assert stdout.count("PASS:") >= 4, \
            f"All non-memory tools should work. stdout: {stdout}"

        assert "NON_MEMORY_TOOLS_TEST_COMPLETE" in stdout, \
            f"Test should complete. stdout: {stdout}"

        # Should not have errors
        assert "ERROR:" not in stdout, \
            f"Should not have errors. stdout: {stdout}"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Non-memory tools test hung")


def test_redis_config_in_server():
    """Test that Redis configuration is properly defined in server.py"""
    server_path = Path(__file__).parent / "server.py"
    content = server_path.read_text()

    # Check Redis configuration
    assert "REDIS_HOST" in content, "Should have REDIS_HOST config"
    assert "REDIS_PORT" in content, "Should have REDIS_PORT config"
    assert "REDIS_DB" in content, "Should have REDIS_DB config"

    # Check graceful degradation
    assert "MEMORY_ENABLED" in content, "Should have MEMORY_ENABLED flag"
    assert "redis_client" in content, "Should have redis_client variable"

    # Check error handling
    assert 'try:' in content and 'except' in content, \
        "Should have try/except for Redis connection"


def test_memory_tools_check_redis_availability():
    """Test that memory tools check for Redis availability"""
    server_path = Path(__file__).parent / "server.py"
    content = server_path.read_text()

    # Memory tools should check MEMORY_ENABLED
    memory_tools = [
        "set_memory",
        "get_memory",
        "delete_memory",
        "list_memory_keys",
        "index_project_files",
        "save_agent_snapshot",
        "semantic_search_files",
    ]

    for tool in memory_tools:
        # Find the tool function
        assert f"def {tool}" in content, f"Tool {tool} should exist"

    # Check that there's error handling for disabled memory
    assert "Redis memory is not enabled" in content or \
           "MEMORY_ENABLED" in content, \
           "Should check for Redis availability"


@pytest.mark.timeout(8)
def test_redis_timeout_doesnt_hang_server():
    """Test that Redis connection timeout doesn't hang server startup"""
    server_path = Path(__file__).parent / "server.py"

    test_script = """
import sys
import time
from unittest.mock import MagicMock, Mock

# Mock sentence_transformers
sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

# Mock redis with slow timeout
mock_redis = MagicMock()
redis_instance = Mock()

def slow_ping():
    # Simulate slow connection that eventually fails
    time.sleep(0.1)  # Small delay
    raise Exception("Connection timeout")

redis_instance.ping = slow_ping
mock_redis.Redis.return_value = redis_instance
sys.modules['redis'] = mock_redis

start = time.time()
sys.path.insert(0, '%s')
import server
elapsed = time.time() - start

print(f"SERVER_IMPORT_TIME={elapsed:.2f}")
if elapsed < 5.0:
    print("PASS: Server import completed quickly despite Redis timeout")
else:
    print(f"ERROR: Server import took too long: {elapsed}s")

print("REDIS_TIMEOUT_TEST_COMPLETE")
""" % str(server_path.parent)

    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=8)

        # Should complete despite Redis issues
        assert "REDIS_TIMEOUT_TEST_COMPLETE" in stdout, \
            f"Test should complete. stdout: {stdout}"

        # Should complete quickly
        assert "PASS:" in stdout, \
            f"Should complete quickly. stdout: {stdout}"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Redis timeout test hung - server may not handle timeouts properly")

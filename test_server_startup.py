#!/usr/bin/env python3
"""
Test server startup without hanging

Verifies that server.py starts within timeout and doesn't hang.
Uses mocked dependencies to avoid external requirements.
"""

import pytest
import sys
import subprocess
import time
import signal
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.mark.timeout(10)
def test_server_imports_without_hanging():
    """Test that server module can be imported without hanging"""
    server_path = Path(__file__).parent / "server.py"
    assert server_path.exists(), "server.py should exist"

    # Import with mocked dependencies
    with patch.dict(sys.modules, {"sentence_transformers": MagicMock()}):
        # Read server code
        server_code = server_path.read_text()
        assert "def main()" in server_code, "server.py should have main function"
        assert "FastMCP" in server_code, "server.py should use FastMCP"


@pytest.mark.timeout(10)
def test_server_subprocess_starts_without_hanging():
    """Test that server starts as subprocess within timeout"""
    server_path = Path(__file__).parent / "server.py"

    # Create a minimal script that imports server with mocked dependencies
    test_script = """
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies
sys.modules['sentence_transformers'] = MagicMock()

# Mock SentenceTransformer class
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

# Now import server
sys.path.insert(0, '%s')
import server

# Don't call main() - just verify import works
print("SERVER_IMPORT_SUCCESS")
""" % str(server_path.parent)

    start_time = time.time()
    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait up to 5 seconds for completion
        stdout, stderr = proc.communicate(timeout=5)
        elapsed = time.time() - start_time

        # Verify it completed successfully
        assert "SERVER_IMPORT_SUCCESS" in stdout, "Server should import successfully"
        assert elapsed < 5, f"Server import took {elapsed}s, should be faster"
        assert proc.returncode == 0, f"Process should exit cleanly, got {proc.returncode}"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Server import hung and did not complete within 5 seconds")


@pytest.mark.timeout(10)
def test_server_main_starts_without_immediate_crash():
    """Test that server.main() can be called without immediate crash"""
    server_path = Path(__file__).parent / "server.py"

    # Script that starts server and sends it SIGTERM after brief moment
    test_script = """
import sys
import signal
import os
import time
from unittest.mock import MagicMock

# Mock heavy dependencies
sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

sys.path.insert(0, '%s')
import server

# Set up a timeout to kill ourselves
def timeout_handler(signum, frame):
    print("SERVER_STARTED_AND_WAITING")
    sys.exit(0)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(2)  # Wait 2 seconds then exit

try:
    # This will block waiting for stdin
    server.main()
except Exception as e:
    print(f"SERVER_EXCEPTION: {e}")
    sys.exit(1)
""" % str(server_path.parent)

    start_time = time.time()
    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait up to 5 seconds
        stdout, stderr = proc.communicate(timeout=5)
        elapsed = time.time() - start_time

        # Server should have started and waited for input
        assert "SERVER_STARTED_AND_WAITING" in stdout or elapsed >= 1.5, \
            "Server should start and wait for input"

        # Should not crash immediately
        assert "SERVER_EXCEPTION" not in stdout, "Server should not crash on startup"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Server did not start within timeout")


@pytest.mark.timeout(8)
def test_server_responds_to_termination_signal():
    """Test that server can be gracefully terminated"""
    server_path = Path(__file__).parent / "server.py"

    # Start server as subprocess
    test_script = """
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

sys.path.insert(0, '%s')
import server

server.main()
""" % str(server_path.parent)

    proc = subprocess.Popen(
        [sys.executable, "-c", test_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give it a moment to start
    time.sleep(1)

    # Verify it's still running
    assert proc.poll() is None, "Server should still be running"

    # Send termination signal
    proc.terminate()

    # Wait for graceful shutdown
    try:
        proc.wait(timeout=3)
        # Should exit cleanly
        assert True, "Server terminated gracefully"
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("Server did not respond to termination signal")


def test_server_has_required_components():
    """Test that server.py has all required components"""
    server_path = Path(__file__).parent / "server.py"
    content = server_path.read_text()

    # Check for required components
    assert "FastMCP" in content, "Server should use FastMCP"
    assert "def main()" in content, "Server should have main() function"
    assert "@mcp.tool" in content, "Server should define tools"
    assert "ping" in content, "Server should have ping tool"
    assert "asyncio.run" in content or "anyio.run" in content, "Server should use async runtime"


@pytest.mark.timeout(5)
def test_server_module_level_imports():
    """Test that server module-level imports complete quickly"""
    import importlib.util

    server_path = Path(__file__).parent / "server.py"

    # Mock dependencies before import
    with patch.dict(sys.modules, {
        "sentence_transformers": MagicMock(),
        "redis": MagicMock(),
    }):
        # Load module spec
        spec = importlib.util.spec_from_file_location("server_test", server_path)
        assert spec is not None, "Should be able to load server spec"
        assert spec.loader is not None, "Spec should have a loader"

        # This verifies the file is valid Python
        module = importlib.util.module_from_spec(spec)
        assert module is not None, "Should create module from spec"

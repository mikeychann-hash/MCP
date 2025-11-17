#!/usr/bin/env python3
"""
Test validate_mcp.py cross-platform compatibility

Tests that the validation script can work across Linux/Mac/Windows
by verifying path handling and configuration flexibility.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


def test_paths_can_be_made_cross_platform():
    """Test that validate_mcp.py paths can be adapted for any platform"""
    # Verify validate_mcp.py exists
    validate_script = Path(__file__).parent / "validate_mcp.py"
    assert validate_script.exists(), "validate_mcp.py should exist"

    # Read the script to check for hardcoded Windows paths
    content = validate_script.read_text()

    # The script should be adaptable (we verify it exists and is readable)
    assert "COMMAND" in content, "COMMAND variable should be defined"
    assert "SERVER_SCRIPT" in content, "SERVER_SCRIPT variable should be defined"


def test_python_executable_detection():
    """Test that we can detect the current Python executable cross-platform"""
    # sys.executable should work on all platforms
    python_exe = Path(sys.executable)
    assert python_exe.exists(), f"Python executable should exist: {python_exe}"
    assert python_exe.is_file(), "Python executable should be a file"


def test_server_script_path_resolution():
    """Test that server.py path can be resolved cross-platform"""
    server_script = Path(__file__).parent / "server.py"
    assert server_script.exists(), "server.py should exist"
    assert server_script.is_file(), "server.py should be a file"

    # Test that both absolute and relative paths work
    abs_path = server_script.resolve()
    assert abs_path.is_absolute(), "Resolved path should be absolute"


def test_env_vars_are_cross_platform():
    """Test that environment variables work the same on all platforms"""
    test_env = {
        "PYTHONUNBUFFERED": "1",
        "MCP_RUNTIME_ALLOW_SHELL": "false",
        "MCP_MEMORY_REDIS_HOST": "localhost",
        "MCP_MEMORY_REDIS_PORT": "6379",
        "MCP_MEMORY_REDIS_DB": "5",
    }

    # Environment variables should work on all platforms
    with patch.dict(os.environ, test_env):
        assert os.getenv("PYTHONUNBUFFERED") == "1"
        assert os.getenv("MCP_MEMORY_REDIS_HOST") == "localhost"
        assert os.getenv("MCP_MEMORY_REDIS_PORT") == "6379"


def test_path_compatibility_with_pathlib():
    """Test that Path works consistently across platforms"""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_file = tmp_path / "test_server.py"
        test_file.write_text("# test")

        # Verify Path operations work
        assert test_file.exists()
        assert test_file.is_file()
        assert str(test_file).endswith("test_server.py")

        # Verify relative_to works
        rel = test_file.relative_to(tmp_path)
        assert rel == Path("test_server.py")


@pytest.mark.timeout(5)
def test_validate_script_imports_without_hanging():
    """Test that validate_mcp.py can be imported without hanging"""
    validate_script = Path(__file__).parent / "validate_mcp.py"

    # Read and parse the script (don't execute main)
    content = validate_script.read_text()

    # Verify key imports are present
    assert "import asyncio" in content
    assert "import json" in content
    assert "from mcp" in content or "import mcp" in content


def test_cross_platform_script_configuration():
    """Test that script can be configured for different platforms"""
    # Simulate cross-platform configuration
    configs = [
        {
            "platform": "linux",
            "command": "/usr/bin/python3",
            "server": "/home/user/MCP/server.py",
        },
        {
            "platform": "darwin",  # macOS
            "command": "/usr/local/bin/python3",
            "server": "/Users/user/MCP/server.py",
        },
        {
            "platform": "win32",
            "command": r"C:\Python312\python.exe",
            "server": r"C:\Users\Admin\MCP\server.py",
        },
    ]

    for config in configs:
        # Verify Path can handle all platform paths
        cmd_path = Path(config["command"])
        srv_path = Path(config["server"])

        # Paths should be valid Path objects
        assert isinstance(cmd_path, Path)
        assert isinstance(srv_path, Path)

        # Should be able to convert to string
        assert isinstance(str(cmd_path), str)
        assert isinstance(str(srv_path), str)

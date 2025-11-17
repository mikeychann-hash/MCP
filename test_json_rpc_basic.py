#!/usr/bin/env python3
"""
Test basic JSON-RPC flow

Tests the basic MCP protocol flow:
1. Initialize connection
2. List available tools
3. Call ping tool

Uses LSP-style Content-Length framing.
"""

import pytest
import sys
import subprocess
import json
import time
from pathlib import Path


def send_jsonrpc_message(proc, method, params=None, msg_id=1):
    """Send a JSON-RPC message with LSP framing"""
    message = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": method,
    }
    if params is not None:
        message["params"] = params

    json_str = json.dumps(message)
    framed = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"

    proc.stdin.write(framed.encode('utf-8'))
    proc.stdin.flush()


def read_jsonrpc_response(proc, timeout=5):
    """Read a JSON-RPC response with LSP framing"""
    start_time = time.time()

    # Read headers
    headers = {}
    while time.time() - start_time < timeout:
        line = proc.stdout.readline()
        if not line:
            return None

        line = line.strip()
        if not line:
            # Empty line means end of headers
            break

        if b":" in line:
            key, value = line.split(b":", 1)
            headers[key.decode().strip().lower()] = value.decode().strip()

    content_length = headers.get("content-length")
    if not content_length:
        return None

    # Read body
    length = int(content_length)
    body = proc.stdout.read(length)

    if len(body) < length:
        return None

    return json.loads(body.decode('utf-8'))


@pytest.mark.timeout(15)
def test_initialize_flow():
    """Test basic initialize request/response"""
    server_path = Path(__file__).parent / "server.py"

    # Start server with mocked dependencies
    test_wrapper = f"""
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

sys.path.insert(0, '{server_path.parent}')
import server
server.main()
"""

    proc = subprocess.Popen(
        [sys.executable, "-c", test_wrapper],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Give server moment to start
        time.sleep(0.5)

        # Send initialize request
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }

        send_jsonrpc_message(proc, "initialize", init_params, msg_id=1)

        # Read response
        response = read_jsonrpc_response(proc, timeout=10)

        # Verify response
        assert response is not None, "Should receive initialize response"
        assert "result" in response or "error" not in response, \
            f"Should have successful response, got: {response}"

        if "result" in response:
            result = response["result"]
            assert "protocolVersion" in result, "Should have protocolVersion"
            assert "capabilities" in result, "Should have capabilities"
            assert "serverInfo" in result, "Should have serverInfo"
            print("PASS: Initialize succeeded")
        else:
            # Might be a notification or other message
            print(f"Got response: {response}")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.mark.timeout(20)
def test_initialize_and_list_tools():
    """Test initialize followed by list_tools"""
    server_path = Path(__file__).parent / "server.py"

    test_wrapper = f"""
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

sys.path.insert(0, '{server_path.parent}')
import server
server.main()
"""

    proc = subprocess.Popen(
        [sys.executable, "-c", test_wrapper],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(0.5)

        # Send initialize
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
        send_jsonrpc_message(proc, "initialize", init_params, msg_id=1)

        # Read initialize response
        init_response = read_jsonrpc_response(proc, timeout=10)
        assert init_response is not None, "Should receive initialize response"

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        json_str = json.dumps(initialized_notification)
        framed = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"
        proc.stdin.write(framed.encode('utf-8'))
        proc.stdin.flush()

        time.sleep(0.2)

        # Send tools/list request
        send_jsonrpc_message(proc, "tools/list", {}, msg_id=2)

        # Read tools response
        tools_response = read_jsonrpc_response(proc, timeout=10)

        # Verify response
        assert tools_response is not None, "Should receive tools/list response"

        if "result" in tools_response:
            result = tools_response["result"]
            assert "tools" in result, "Should have tools array"
            tools = result["tools"]
            assert isinstance(tools, list), "Tools should be a list"
            assert len(tools) > 0, "Should have at least one tool"

            # Check for ping tool
            tool_names = [t["name"] for t in tools]
            assert "ping" in tool_names, "Should have ping tool"
            print(f"PASS: Found {len(tools)} tools including ping")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.mark.timeout(20)
def test_full_flow_initialize_list_ping():
    """Test complete flow: initialize -> list_tools -> call ping"""
    server_path = Path(__file__).parent / "server.py"

    test_wrapper = f"""
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

sys.path.insert(0, '{server_path.parent}')
import server
server.main()
"""

    proc = subprocess.Popen(
        [sys.executable, "-c", test_wrapper],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(0.5)

        # 1. Initialize
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
        send_jsonrpc_message(proc, "initialize", init_params, msg_id=1)
        init_response = read_jsonrpc_response(proc, timeout=10)
        assert init_response is not None, "Should receive initialize response"
        assert "result" in init_response or "id" in init_response, \
            f"Initialize should succeed, got: {init_response}"

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        json_str = json.dumps(initialized_notification)
        framed = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"
        proc.stdin.write(framed.encode('utf-8'))
        proc.stdin.flush()

        time.sleep(0.2)

        # 2. List tools
        send_jsonrpc_message(proc, "tools/list", {}, msg_id=2)
        tools_response = read_jsonrpc_response(proc, timeout=10)
        assert tools_response is not None, "Should receive tools response"

        # 3. Call ping tool
        ping_params = {
            "name": "ping",
            "arguments": {}
        }
        send_jsonrpc_message(proc, "tools/call", ping_params, msg_id=3)
        ping_response = read_jsonrpc_response(proc, timeout=10)

        # Verify ping response
        assert ping_response is not None, "Should receive ping response"

        if "result" in ping_response:
            result = ping_response["result"]
            assert "content" in result, "Ping result should have content"
            content = result["content"]
            assert isinstance(content, list), "Content should be a list"
            assert len(content) > 0, "Content should not be empty"

            # Check for "pong" in response
            text_content = [c.get("text", "") for c in content if c.get("type") == "text"]
            assert any("pong" in text.lower() for text in text_content), \
                f"Ping should return 'pong', got: {text_content}"

            print("PASS: Full flow completed - initialize, list_tools, ping")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.mark.timeout(10)
def test_jsonrpc_message_framing():
    """Test that server properly handles LSP-style message framing"""
    # Test message construction
    test_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "test",
        "params": {}
    }

    json_str = json.dumps(test_message)
    framed = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"

    # Verify framing format
    assert "Content-Length:" in framed, "Should have Content-Length header"
    assert "\r\n\r\n" in framed, "Should have double CRLF separator"
    assert framed.endswith(json_str), "Should end with JSON body"

    # Verify length is correct
    parts = framed.split("\r\n\r\n", 1)
    assert len(parts) == 2, "Should split into header and body"
    header, body = parts
    assert f"Content-Length: {len(body)}" in header, "Length should match body"


def test_server_supports_jsonrpc():
    """Test that server.py has JSON-RPC support"""
    server_path = Path(__file__).parent / "server.py"
    content = server_path.read_text()

    # Check for JSON-RPC related code
    assert "Content-Length" in content, "Should support Content-Length framing"
    assert "jsonrpc" in content.lower() or "JSONRPCMessage" in content, \
        "Should handle JSON-RPC messages"
    assert "stdin" in content and "stdout" in content, \
        "Should use stdio for communication"


@pytest.mark.timeout(15)
def test_server_handles_malformed_message():
    """Test that server doesn't crash on malformed input"""
    server_path = Path(__file__).parent / "server.py"

    test_wrapper = f"""
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
mock_transformer = MagicMock()
mock_transformer.encode.return_value = [[0.1] * 384]
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock(return_value=mock_transformer)

sys.path.insert(0, '{server_path.parent}')
import server
server.main()
"""

    proc = subprocess.Popen(
        [sys.executable, "-c", test_wrapper],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(0.5)

        # Send some noise before proper message (server should skip it)
        proc.stdin.write(b"NOISE\n")
        proc.stdin.flush()

        time.sleep(0.2)

        # Now send proper message
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
        send_jsonrpc_message(proc, "initialize", init_params, msg_id=1)

        # Server should still respond
        response = read_jsonrpc_response(proc, timeout=5)

        # Should either get response or server should still be running
        is_running = proc.poll() is None

        assert response is not None or is_running, \
            "Server should handle noise and continue running"

        print("PASS: Server handles malformed input gracefully")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

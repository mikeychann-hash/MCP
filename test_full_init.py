#!/usr/bin/env python3
"""Comprehensive test of server initialization and basic RPC"""

import sys
from unittest.mock import MagicMock
import subprocess
import json
import time
import threading

# Mock sentence_transformers
sys.modules['sentence_transformers'] = MagicMock()

def test_server():
    # Create test messages
    initialize_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    json_str = json.dumps(initialize_msg)
    message = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"

    print("[TEST] Starting server subprocess...")

    # Start server
    proc = subprocess.Popen(
        [sys.executable, '-c', '''
import sys
from unittest.mock import MagicMock
sys.modules['sentence_transformers'] = MagicMock()
sys.path.insert(0, '/home/user/MCP')
import server
server.main()
'''],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        bufsize=0  # Unbuffered
    )

    stderr_lines = []
    stdout_data = []

    def read_stderr():
        """Read stderr in background"""
        while True:
            line = proc.stderr.readline()
            if not line:
                break
            try:
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    stderr_lines.append(decoded)
                    print(f"[STDERR] {decoded}")
            except Exception as e:
                print(f"[ERROR reading stderr] {e}")

    def read_stdout():
        """Read stdout in background"""
        while True:
            chunk = proc.stdout.read(1024)
            if not chunk:
                break
            stdout_data.append(chunk)

    # Start background threads to read output
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread.start()
    stdout_thread.start()

    # Wait for server to start
    print("[TEST] Waiting for server startup messages...")
    time.sleep(2)

    # Send initialize message
    print(f"[TEST] Sending initialize message...")
    try:
        proc.stdin.write(message.encode('utf-8'))
        proc.stdin.flush()
    except Exception as e:
        print(f"[ERROR] Failed to write to stdin: {e}")

    # Wait for response
    time.sleep(2)

    # Check results
    print(f"\n[TEST] === ANALYSIS ===")
    print(f"[TEST] Process running: {proc.poll() is None}")
    print(f"[TEST] Stderr lines captured: {len(stderr_lines)}")
    print(f"[TEST] Stdout bytes captured: {len(b''.join(stdout_data))}")

    # Check for key startup messages
    startup_reached = any("Starting MCP Runtime v3.0" in line for line in stderr_lines)
    stdio_ready = any("stdio transport ready" in line for line in stderr_lines)

    print(f"[TEST] Startup message found: {startup_reached}")
    print(f"[TEST] Stdio ready message found: {stdio_ready}")

    if stdout_data:
        stdout_str = b''.join(stdout_data).decode('utf-8', errors='replace')
        print(f"[TEST] STDOUT preview: {stdout_str[:200]}")

        # Try to parse as JSON-RPC response
        try:
            if 'Content-Length:' in stdout_str:
                print("[TEST] Found LSP-framed response!")
        except Exception as e:
            print(f"[TEST] Could not parse response: {e}")

    # Cleanup
    print("\n[TEST] Terminating server...")
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    print("[TEST] Test complete!")

    # Return findings
    return {
        "startup_reached": startup_reached,
        "stdio_ready": stdio_ready,
        "stderr_lines": stderr_lines,
        "has_stdout": len(stdout_data) > 0,
        "stdout_preview": b''.join(stdout_data)[:500].decode('utf-8', errors='replace') if stdout_data else ""
    }

if __name__ == "__main__":
    results = test_server()
    print("\n" + "="*60)
    print("FINAL RESULTS:")
    print(json.dumps({k: v for k, v in results.items() if k != 'stderr_lines'}, indent=2))

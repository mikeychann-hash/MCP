#!/usr/bin/env python3
"""Test script to send JSON-RPC initialize message to server"""

import sys
from unittest.mock import MagicMock
import subprocess
import json
import time

# Create test message - MCP initialize request
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

# Format as LSP-framed message
json_str = json.dumps(initialize_msg)
message = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"

print(f"[TEST] Sending initialize message:")
print(f"[TEST] {message[:100]}...")

# Start server as subprocess
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
    text=False
)

# Send message
try:
    proc.stdin.write(message.encode('utf-8'))
    proc.stdin.flush()

    # Wait a bit for response
    time.sleep(2)

    # Check if process is still running
    if proc.poll() is None:
        print("[TEST] Server is still running (good sign)")
        proc.terminate()
        proc.wait(timeout=2)
    else:
        print(f"[TEST] Server exited with code: {proc.returncode}")

    # Get output
    stdout, stderr = proc.communicate(timeout=1)

    print("\n[TEST] STDERR output:")
    print(stderr.decode('utf-8', errors='replace'))

    print("\n[TEST] STDOUT output:")
    print(stdout.decode('utf-8', errors='replace')[:500])

except subprocess.TimeoutExpired:
    proc.kill()
    stdout, stderr = proc.communicate()
    print("\n[TEST] Timeout - Server may be working but slow")
    print("\n[TEST] STDERR:")
    print(stderr.decode('utf-8', errors='replace'))
    print("\n[TEST] STDOUT:")
    print(stdout.decode('utf-8', errors='replace')[:500])
except Exception as e:
    print(f"\n[TEST] Error: {e}")
    proc.kill()
    proc.wait()

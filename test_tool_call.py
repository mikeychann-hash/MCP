#!/usr/bin/env python3
"""Test calling a tool to verify full functionality"""

import sys
from unittest.mock import MagicMock
import subprocess
import json
import time
import threading

# Mock sentence_transformers
sys.modules['sentence_transformers'] = MagicMock()

def make_message(msg_dict):
    json_str = json.dumps(msg_dict)
    return f"Content-Length: {len(json_str)}\r\n\r\n{json_str}".encode('utf-8')

def test_tool_call():
    print("[TEST] Testing tool call functionality...")

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
        bufsize=0
    )

    stdout_data = []
    def read_stdout():
        while True:
            chunk = proc.stdout.read(2048)
            if not chunk:
                break
            stdout_data.append(chunk)

    threading.Thread(target=read_stdout, daemon=True).start()
    time.sleep(2)

    # Initialize
    print("[TEST] 1. Initializing...")
    proc.stdin.write(make_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }))
    proc.stdin.flush()
    time.sleep(1)

    # Call ping tool
    print("[TEST] 2. Calling 'ping' tool...")
    proc.stdin.write(make_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "ping",
            "arguments": {}
        }
    }))
    proc.stdin.flush()
    time.sleep(1)

    # Call echo tool
    print("[TEST] 3. Calling 'echo' tool...")
    proc.stdin.write(make_message({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {"message": "Hello MCP!"}
        }
    }))
    proc.stdin.flush()
    time.sleep(1)

    # Parse responses
    full_stdout = b''.join(stdout_data).decode('utf-8', errors='replace')
    responses = []
    parts = full_stdout.split('Content-Length:')
    for part in parts[1:]:
        try:
            lines = part.split('\r\n\r\n', 1)
            if len(lines) == 2:
                length = int(lines[0].strip())
                json_data = lines[1][:length]
                responses.append(json.loads(json_data))
        except Exception as e:
            pass

    print(f"\n[TEST] Got {len(responses)} responses:")
    for i, resp in enumerate(responses, 1):
        print(f"\n--- Response {i} (id={resp.get('id')}) ---")
        if 'result' in resp:
            result = resp['result']
            if isinstance(result, dict):
                # Tool call result
                if 'content' in result:
                    for content in result['content']:
                        if content.get('type') == 'text':
                            print(f"Tool returned: {content.get('text')}")
                else:
                    print(f"Result: {json.dumps(result, indent=2)[:200]}")
            else:
                print(f"Result: {result}")
        elif 'error' in resp:
            print(f"ERROR: {resp['error']}")

    proc.terminate()
    proc.wait(timeout=2)

    return responses

if __name__ == "__main__":
    try:
        results = test_tool_call()
        print(f"\n[TEST] ✓ Tool call test complete!")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

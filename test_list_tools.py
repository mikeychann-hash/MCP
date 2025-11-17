#!/usr/bin/env python3
"""Test listing tools from the server"""

import sys
from unittest.mock import MagicMock
import subprocess
import json
import time
import threading

# Mock sentence_transformers
sys.modules['sentence_transformers'] = MagicMock()

def test_list_tools():
    # Initialize message first
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }

    # Then list tools
    list_tools_msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    def make_message(msg_dict):
        json_str = json.dumps(msg_dict)
        return f"Content-Length: {len(json_str)}\r\n\r\n{json_str}".encode('utf-8')

    print("[TEST] Starting server...")

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
            chunk = proc.stdout.read(1024)
            if not chunk:
                break
            stdout_data.append(chunk)
            print(f"[STDOUT CHUNK] {len(chunk)} bytes")

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stdout_thread.start()

    # Wait for startup
    time.sleep(2)

    # Send initialize
    print("[TEST] Sending initialize...")
    proc.stdin.write(make_message(init_msg))
    proc.stdin.flush()
    time.sleep(1)

    # Send list tools
    print("[TEST] Sending tools/list...")
    proc.stdin.write(make_message(list_tools_msg))
    proc.stdin.flush()
    time.sleep(2)

    # Parse responses
    print("\n[TEST] Parsing responses...")
    full_stdout = b''.join(stdout_data).decode('utf-8', errors='replace')

    # Split by Content-Length headers
    responses = []
    parts = full_stdout.split('Content-Length:')
    for part in parts[1:]:  # Skip first empty part
        try:
            lines = part.split('\r\n\r\n', 1)
            if len(lines) == 2:
                length = int(lines[0].strip())
                json_data = lines[1][:length]
                responses.append(json.loads(json_data))
        except Exception as e:
            print(f"[WARN] Could not parse response part: {e}")

    print(f"[TEST] Parsed {len(responses)} responses")

    for i, resp in enumerate(responses):
        print(f"\n[RESPONSE {i+1}]")
        if 'result' in resp and isinstance(resp['result'], dict):
            if 'tools' in resp['result']:
                tools = resp['result']['tools']
                print(f"Found {len(tools)} tools:")
                for tool in tools[:5]:  # Show first 5
                    print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', '')[:60]}")
            else:
                print(f"Result keys: {list(resp['result'].keys())}")
        else:
            print(json.dumps(resp, indent=2)[:200])

    # Cleanup
    proc.terminate()
    proc.wait(timeout=2)

    return responses

if __name__ == "__main__":
    try:
        results = test_list_tools()
        print(f"\n[TEST] Complete! Got {len(results)} responses")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

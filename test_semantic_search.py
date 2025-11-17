#!/usr/bin/env python3
"""Test what happens when calling semantic search without sentence-transformers"""

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

def test_semantic_feature():
    print("[TEST] Testing semantic search (without real sentence-transformers)...")

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
    stderr_data = []

    def read_stdout():
        while True:
            chunk = proc.stdout.read(2048)
            if not chunk:
                break
            stdout_data.append(chunk)

    def read_stderr():
        while True:
            chunk = proc.stderr.read(2048)
            if not chunk:
                break
            stderr_data.append(chunk)

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()
    time.sleep(2)

    # Initialize
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

    # Try to call semantic_search_files (which requires embeddings)
    print("[TEST] Calling 'semantic_search_files' tool...")
    proc.stdin.write(make_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "semantic_search_files",
            "arguments": {"query": "test query", "top_k": 5}
        }
    }))
    proc.stdin.flush()
    time.sleep(2)

    # Parse responses
    full_stdout = b''.join(stdout_data).decode('utf-8', errors='replace')
    full_stderr = b''.join(stderr_data).decode('utf-8', errors='replace')

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

    print(f"\n[TEST] Got {len(responses)} responses")

    # Look for the semantic search response
    for resp in responses:
        if resp.get('id') == 2:
            print("\n[TEST] Semantic search response:")
            if 'result' in resp:
                print(f"Result: {json.dumps(resp['result'], indent=2)[:300]}")
            elif 'error' in resp:
                print(f"ERROR (expected): {json.dumps(resp['error'], indent=2)}")

    # Check stderr for any errors
    if 'error' in full_stderr.lower() or 'traceback' in full_stderr.lower():
        print("\n[TEST] STDERR contains error messages:")
        print(full_stderr[-500:])

    proc.terminate()
    proc.wait(timeout=2)

if __name__ == "__main__":
    try:
        test_semantic_feature()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

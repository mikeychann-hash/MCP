#!/usr/bin/env python3
"""Test script to run server with mocked sentence_transformers and timeout"""

import sys
from unittest.mock import MagicMock
import asyncio
import signal

# Mock sentence_transformers before importing server
sys.modules['sentence_transformers'] = MagicMock()

# Import server
sys.path.insert(0, '/home/user/MCP')
import server

# Set up timeout
def timeout_handler(signum, frame):
    print("\n[TEST] Timeout reached - server appears to be hanging/waiting for input")
    sys.exit(124)  # Standard timeout exit code

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)  # 5 second timeout

# Try to run the server
try:
    print("[TEST] Calling server.main()...")
    server.main()
except KeyboardInterrupt:
    print("\n[TEST] Received KeyboardInterrupt")
except SystemExit as e:
    print(f"\n[TEST] SystemExit with code: {e.code}")
    raise
except Exception as e:
    print(f"\n[TEST] Exception during main(): {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

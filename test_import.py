#!/usr/bin/env python3
"""Test script to import server with mocked sentence_transformers"""

import sys
from unittest.mock import MagicMock

# Mock sentence_transformers before importing server
sys.modules['sentence_transformers'] = MagicMock()

# Now try to import server
sys.path.insert(0, '/home/user/MCP')
try:
    import server
    print("SUCCESS: Server module imported successfully!")
    print(f"Server has main function: {hasattr(server, 'main')}")
    print(f"Server has mcp object: {hasattr(server, 'mcp')}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

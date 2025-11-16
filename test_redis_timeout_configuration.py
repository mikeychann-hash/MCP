"""
Test Redis timeout configuration via environment variables.
Verifies that MCP_REDIS_CONNECT_TIMEOUT and MCP_REDIS_SOCKET_TIMEOUT
environment variables are properly applied to the Redis client.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Mock sentence_transformers before any imports
sys.modules['sentence_transformers'] = MagicMock()


class TestRedisTimeoutConfiguration(unittest.TestCase):
    """Test cases for Redis timeout configuration."""

    def setUp(self):
        """Reset environment and module cache before each test."""
        # Clear any existing timeout env vars
        for key in ['MCP_REDIS_CONNECT_TIMEOUT', 'MCP_REDIS_SOCKET_TIMEOUT']:
            if key in os.environ:
                del os.environ[key]

        # Remove server module if already imported
        if 'server' in sys.modules:
            del sys.modules['server']

    def test_default_timeout_values(self):
        """Test that default timeout values are 5 seconds."""
        with patch('redis.Redis') as mock_redis:
            import server

            # Verify default values are set correctly
            self.assertEqual(server.REDIS_CONNECT_TIMEOUT, 5)
            self.assertEqual(server.REDIS_SOCKET_TIMEOUT, 5)

            # Verify Redis client was initialized with default timeouts
            mock_redis.assert_called_once()
            call_kwargs = mock_redis.call_args[1]
            self.assertEqual(call_kwargs['socket_connect_timeout'], 5)
            self.assertEqual(call_kwargs['socket_timeout'], 5)

    def test_custom_timeout_values(self):
        """Test that custom timeout values from environment are applied."""
        os.environ['MCP_REDIS_CONNECT_TIMEOUT'] = '10'
        os.environ['MCP_REDIS_SOCKET_TIMEOUT'] = '15'

        with patch('redis.Redis') as mock_redis:
            import server

            # Verify custom values are set correctly
            self.assertEqual(server.REDIS_CONNECT_TIMEOUT, 10)
            self.assertEqual(server.REDIS_SOCKET_TIMEOUT, 15)

            # Verify Redis client was initialized with custom timeouts
            mock_redis.assert_called_once()
            call_kwargs = mock_redis.call_args[1]
            self.assertEqual(call_kwargs['socket_connect_timeout'], 10)
            self.assertEqual(call_kwargs['socket_timeout'], 15)

    def test_backward_compatibility(self):
        """Test that system works without timeout env vars (backward compatible)."""
        # Ensure no timeout env vars are set
        for key in ['MCP_REDIS_CONNECT_TIMEOUT', 'MCP_REDIS_SOCKET_TIMEOUT']:
            if key in os.environ:
                del os.environ[key]

        with patch('redis.Redis') as mock_redis:
            import server

            # Should fall back to defaults (5 seconds, improved from 2)
            self.assertEqual(server.REDIS_CONNECT_TIMEOUT, 5)
            self.assertEqual(server.REDIS_SOCKET_TIMEOUT, 5)

            # Redis client should still initialize successfully
            mock_redis.assert_called_once()

    def test_timeout_values_are_integers(self):
        """Test that timeout values are properly converted to integers."""
        os.environ['MCP_REDIS_CONNECT_TIMEOUT'] = '7'
        os.environ['MCP_REDIS_SOCKET_TIMEOUT'] = '9'

        with patch('redis.Redis') as mock_redis:
            import server

            # Verify values are integers, not strings
            self.assertIsInstance(server.REDIS_CONNECT_TIMEOUT, int)
            self.assertIsInstance(server.REDIS_SOCKET_TIMEOUT, int)
            self.assertEqual(server.REDIS_CONNECT_TIMEOUT, 7)
            self.assertEqual(server.REDIS_SOCKET_TIMEOUT, 9)

    def test_increased_from_original_hardcoded_values(self):
        """Test that default values have been increased from original 2 seconds."""
        with patch('redis.Redis') as mock_redis:
            import server

            # New defaults should be 5 seconds (increased from 2)
            self.assertGreater(server.REDIS_CONNECT_TIMEOUT, 2)
            self.assertGreater(server.REDIS_SOCKET_TIMEOUT, 2)

            # Verify the improvement
            call_kwargs = mock_redis.call_args[1]
            self.assertEqual(call_kwargs['socket_connect_timeout'], 5)
            self.assertEqual(call_kwargs['socket_timeout'], 5)


if __name__ == '__main__':
    unittest.main()

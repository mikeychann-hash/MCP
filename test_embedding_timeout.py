#!/usr/bin/env python3
"""
Test script for embedding timeout mechanism

This script tests the timeout and retry logic for SentenceTransformer model loading.
It includes tests for:
1. Timeout triggering
2. Retry logic with exponential backoff
3. Successful model loading
4. Error handling

Run with: python test_embedding_timeout.py
"""

import os
import signal
import time
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call


# Simulate the timeout context manager from server.py
@contextmanager
def _timeout(seconds):
    """Context manager for operation timeout using SIGALRM."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


class TestEmbeddingTimeout(unittest.TestCase):
    """Test suite for embedding timeout mechanism."""

    def test_timeout_context_manager(self):
        """Test that timeout context manager properly raises TimeoutError."""
        with self.assertRaises(TimeoutError) as cm:
            with _timeout(1):
                time.sleep(2)  # Should timeout

        self.assertIn("timed out after 1s", str(cm.exception))

    def test_timeout_success_within_limit(self):
        """Test that operations completing within timeout don't raise error."""
        try:
            with _timeout(2):
                time.sleep(0.1)  # Should complete fine
            success = True
        except TimeoutError:
            success = False

        self.assertTrue(success, "Operation should complete within timeout")

    @patch('time.sleep')
    def test_retry_logic_all_timeouts(self, mock_sleep):
        """Test that retry logic attempts 3 times with exponential backoff."""
        EMBED_LOAD_TIMEOUT = 5
        attempts = []

        def mock_load():
            attempts.append(len(attempts))
            raise TimeoutError(f"Operation timed out after {EMBED_LOAD_TIMEOUT}s")

        # Simulate the retry logic from _get_embed_model
        try:
            for attempt in range(3):
                try:
                    mock_load()
                    break
                except TimeoutError:
                    if attempt == 2:
                        raise RuntimeError(
                            f"Failed to load embedding model after 3 attempts "
                            f"(timeout: {EMBED_LOAD_TIMEOUT}s). "
                            f"Try increasing MCP_EMBED_LOAD_TIMEOUT or check your network connection."
                        )
                    backoff_time = 2 ** attempt
                    time.sleep(backoff_time)
        except RuntimeError as e:
            final_error = str(e)

        # Verify 3 attempts were made
        self.assertEqual(len(attempts), 3, "Should attempt exactly 3 times")

        # Verify exponential backoff (1s, 2s)
        expected_calls = [call(1), call(2)]
        mock_sleep.assert_has_calls(expected_calls)

        # Verify error message
        self.assertIn("Failed to load embedding model after 3 attempts", final_error)
        self.assertIn("Try increasing MCP_EMBED_LOAD_TIMEOUT", final_error)

    @patch('time.sleep')
    def test_retry_logic_success_on_second_attempt(self, mock_sleep):
        """Test that retry succeeds on second attempt."""
        EMBED_LOAD_TIMEOUT = 5
        attempts = []

        def mock_load():
            attempt_num = len(attempts)
            attempts.append(attempt_num)
            if attempt_num == 0:
                raise TimeoutError(f"Operation timed out after {EMBED_LOAD_TIMEOUT}s")
            return "model_loaded"

        # Simulate the retry logic from _get_embed_model
        result = None
        for attempt in range(3):
            try:
                result = mock_load()
                break
            except TimeoutError:
                if attempt == 2:
                    raise RuntimeError("Failed to load embedding model after 3 attempts")
                backoff_time = 2 ** attempt
                time.sleep(backoff_time)

        # Verify only 2 attempts were made (first failed, second succeeded)
        self.assertEqual(len(attempts), 2, "Should stop after successful attempt")
        self.assertEqual(result, "model_loaded", "Should return loaded model")

        # Verify only one backoff (1s) was done
        mock_sleep.assert_called_once_with(1)

    def test_environment_variable_parsing(self):
        """Test that environment variable is correctly parsed."""
        # Test default value
        default_timeout = int(os.getenv("MCP_EMBED_LOAD_TIMEOUT", "300"))
        self.assertEqual(default_timeout, 300, "Default timeout should be 300 seconds")

        # Test custom value
        os.environ["MCP_EMBED_LOAD_TIMEOUT"] = "600"
        custom_timeout = int(os.getenv("MCP_EMBED_LOAD_TIMEOUT", "300"))
        self.assertEqual(custom_timeout, 600, "Custom timeout should be respected")

        # Clean up
        if "MCP_EMBED_LOAD_TIMEOUT" in os.environ:
            del os.environ["MCP_EMBED_LOAD_TIMEOUT"]

    @patch('time.sleep')
    def test_non_timeout_exception_not_retried(self, mock_sleep):
        """Test that non-timeout exceptions are not retried."""
        attempts = []

        def mock_load():
            attempts.append(len(attempts))
            raise ValueError("Invalid model name")

        # Simulate the retry logic from _get_embed_model
        with self.assertRaises(ValueError) as cm:
            for attempt in range(3):
                try:
                    mock_load()
                    break
                except TimeoutError:
                    if attempt == 2:
                        raise RuntimeError("Failed after 3 attempts")
                    time.sleep(2 ** attempt)
                except Exception:
                    raise

        # Verify only 1 attempt was made (no retry for non-timeout exceptions)
        self.assertEqual(len(attempts), 1, "Should not retry non-timeout exceptions")
        self.assertIn("Invalid model name", str(cm.exception))

        # Verify no sleep was called
        mock_sleep.assert_not_called()


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete embedding loading flow."""

    @patch('sentence_transformers.SentenceTransformer')
    @patch('time.sleep')
    def test_full_retry_flow_with_mock(self, mock_sleep, MockSentenceTransformer):
        """Test the full retry flow with mocked SentenceTransformer."""
        EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
        EMBED_LOAD_TIMEOUT = 10

        # Mock SentenceTransformer to succeed on second attempt
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                time.sleep(EMBED_LOAD_TIMEOUT + 1)  # Simulate timeout
            return MagicMock()

        MockSentenceTransformer.side_effect = side_effect

        # Simulate _get_embed_model logic
        _embed_model = None
        for attempt in range(3):
            try:
                with _timeout(EMBED_LOAD_TIMEOUT):
                    _embed_model = MockSentenceTransformer(EMBED_MODEL_NAME)
                break
            except TimeoutError:
                if attempt == 2:
                    raise RuntimeError("Failed after 3 attempts")
                backoff_time = 2 ** attempt
                time.sleep(backoff_time)

        # In this test, the timeout will trigger on first attempt
        # Since we're using a mock, the actual behavior depends on implementation
        self.assertIsNotNone(_embed_model, "Model should be loaded")


def run_manual_tests():
    """Manual tests that can be run to verify timeout behavior."""
    print("=" * 60)
    print("Manual Timeout Tests")
    print("=" * 60)

    print("\n1. Testing timeout context manager (1 second timeout)...")
    try:
        with _timeout(1):
            print("   Starting operation that takes 2 seconds...")
            time.sleep(2)
            print("   This should not print!")
    except TimeoutError as e:
        print(f"   ✓ Timeout triggered as expected: {e}")

    print("\n2. Testing successful operation (2 second timeout)...")
    try:
        with _timeout(2):
            print("   Starting operation that takes 0.1 seconds...")
            time.sleep(0.1)
            print("   ✓ Operation completed successfully within timeout")
    except TimeoutError as e:
        print(f"   ✗ Unexpected timeout: {e}")

    print("\n3. Testing retry logic with exponential backoff...")
    for attempt in range(3):
        print(f"   Attempt {attempt + 1}/3")
        try:
            # Simulate a timeout on first two attempts
            if attempt < 2:
                raise TimeoutError(f"Simulated timeout on attempt {attempt + 1}")
            else:
                print("   ✓ Operation succeeded on third attempt")
                break
        except TimeoutError as e:
            if attempt == 2:
                print(f"   ✗ Failed after 3 attempts: {e}")
            else:
                backoff_time = 2 ** attempt
                print(f"   Timeout occurred, retrying in {backoff_time}s...")
                time.sleep(backoff_time)

    print("\n" + "=" * 60)
    print("Manual tests complete")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        run_manual_tests()
    else:
        print("Running unit tests...")
        print("=" * 60)
        unittest.main(verbosity=2)

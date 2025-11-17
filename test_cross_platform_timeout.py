#!/usr/bin/env python3
"""
Test cross-platform timeout mechanism.

This test verifies that the _timeout context manager works on both
Windows (using threading.Timer) and Unix (using SIGALRM).
"""

import platform
import signal
import threading
import time
from contextlib import contextmanager


@contextmanager
def _timeout(seconds):
    """Context manager for operation timeout (cross-platform).

    Uses threading.Timer on Windows (SIGALRM not available).
    Uses SIGALRM on Unix/Linux/macOS for better precision.
    """
    is_windows = platform.system() == 'Windows'

    if is_windows:
        # Windows: Use threading.Timer
        timed_out = threading.Event()

        def timeout_handler():
            timed_out.set()

        timer = threading.Timer(seconds, timeout_handler)
        timer.daemon = True
        timer.start()

        try:
            yield
            # Check if we timed out after the operation completes
            if timed_out.is_set():
                raise TimeoutError(f"Operation timed out after {seconds}s")
        finally:
            timer.cancel()
    else:
        # Unix/Linux/macOS: Use SIGALRM for precision
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {seconds}s")

        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)


def test_timeout_triggers():
    """Test that timeout actually triggers."""
    print(f"Testing on platform: {platform.system()}")
    print(f"Has SIGALRM: {hasattr(signal, 'SIGALRM')}")

    try:
        with _timeout(1):
            print("  Starting 2-second sleep (should timeout)...")
            time.sleep(2)
            print("  ERROR: Should not reach here!")
            return False
    except TimeoutError as e:
        print(f"  ✓ Timeout triggered correctly: {e}")
        return True
    except AttributeError as e:
        if "SIGALRM" in str(e):
            print(f"  ✗ SIGALRM not available (Windows compatibility issue): {e}")
            return False
        raise


def test_timeout_doesnt_trigger():
    """Test that timeout doesn't trigger for fast operations."""
    try:
        with _timeout(2):
            print("  Starting 0.5-second sleep (should complete)...")
            time.sleep(0.5)
            print("  ✓ Completed without timeout")
            return True
    except TimeoutError:
        print("  ✗ Unexpected timeout!")
        return False
    except AttributeError as e:
        if "SIGALRM" in str(e):
            print(f"  ✗ SIGALRM not available (Windows compatibility issue): {e}")
            return False
        raise


def test_timeout_cancels_properly():
    """Test that timer is properly cancelled after success."""
    try:
        for i in range(5):
            with _timeout(10):
                time.sleep(0.1)

        # Check for leaked threads (Windows only)
        if platform.system() == 'Windows':
            active_threads = threading.active_count()
            # Should only be main thread (1) or main + a few others, not 5+ timers
            if active_threads > 3:
                print(f"  ✗ Potential thread leak: {active_threads} active threads")
                return False

        print("  ✓ No thread leaks detected")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Cross-Platform Timeout Test")
    print("=" * 60)

    results = []

    print("\nTest 1: Timeout triggers for slow operations")
    results.append(test_timeout_triggers())

    print("\nTest 2: Timeout doesn't trigger for fast operations")
    results.append(test_timeout_doesnt_trigger())

    print("\nTest 3: Timer cleanup (no thread leaks)")
    results.append(test_timeout_cancels_properly())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed! Cross-platform timeout is working correctly.")
        exit(0)
    else:
        print("✗ Some tests failed. Review the implementation.")
        exit(1)

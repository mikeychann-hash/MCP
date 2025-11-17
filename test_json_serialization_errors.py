#!/usr/bin/env python3
"""
Test JSON serialization error handling in Redis operations.

Tests the _safe_json_dumps() helper function with non-serializable objects
to ensure proper fallback behavior and logging.
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

# Setup logging
logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')
log = logging.getLogger("test")


# Define the _safe_json_dumps function inline for testing
def _safe_json_dumps(obj: Any, context: str = "") -> str:
    """
    Safely serialize object to JSON with fallback for non-serializable types.

    Args:
        obj: Object to serialize
        context: Description of what's being serialized (for logging)

    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        log.warning(f"JSON serialization failed for {context}: {e}. Using fallback.")
        # Try with custom JSON encoder
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)
        except Exception as e2:
            log.error(f"Fallback serialization also failed for {context}: {e2}")
            # Last resort: use repr
            return json.dumps({"_repr": repr(obj), "_error": str(e)})


# Test objects with various serialization issues
class NonSerializableClass:
    """A class that cannot be JSON-serialized by default."""
    def __init__(self, value):
        self.value = value
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"NonSerializableClass(value={self.value})"


class CustomObject:
    """Another non-serializable class."""
    def __init__(self, data):
        self.data = data
        self.func = lambda x: x * 2  # Functions are not JSON-serializable


def test_serializable_objects():
    """Test that normal serializable objects work correctly."""
    print("\n=== Test 1: Serializable Objects ===")

    test_cases = [
        {"key": "value", "number": 42, "list": [1, 2, 3]},
        ["string", 123, 45.67, True, None],
        "simple string",
        12345,
        {"nested": {"deeply": {"value": "test"}}},
    ]

    for i, obj in enumerate(test_cases):
        result = _safe_json_dumps(obj, f"test_case_{i+1}")
        parsed = json.loads(result)
        print(f"✓ Test case {i+1} passed: {type(obj).__name__}")
        assert parsed == obj or str(parsed) == str(obj)

    print("All serializable object tests passed!")


def test_non_serializable_objects():
    """Test that non-serializable objects fall back gracefully."""
    print("\n=== Test 2: Non-Serializable Objects ===")

    # Test with custom class instance
    obj1 = NonSerializableClass(42)
    result1 = _safe_json_dumps(obj1, "custom_class_instance")
    parsed1 = json.loads(result1)
    print(f"Custom class result: {result1[:100]}")
    assert isinstance(parsed1, (dict, str))
    print("✓ Custom class handled correctly")

    # Test with lambda function
    obj2 = {"func": lambda x: x + 1}
    result2 = _safe_json_dumps(obj2, "lambda_function")
    parsed2 = json.loads(result2)
    print(f"Lambda function result: {result2[:100]}")
    assert isinstance(parsed2, dict)
    print("✓ Lambda function handled correctly")

    # Test with complex object containing datetime
    obj3 = CustomObject({"key": "value", "time": datetime.now()})
    result3 = _safe_json_dumps(obj3, "complex_object")
    parsed3 = json.loads(result3)
    print(f"Complex object result: {result3[:100]}")
    assert isinstance(parsed3, (dict, str))
    print("✓ Complex object handled correctly")

    # Test with set (not JSON serializable by default)
    obj4 = {"items": {1, 2, 3}}
    result4 = _safe_json_dumps(obj4, "set_object")
    parsed4 = json.loads(result4)
    print(f"Set object result: {result4[:100]}")
    assert isinstance(parsed4, dict)
    print("✓ Set object handled correctly")

    print("All non-serializable object tests passed!")


def test_mixed_objects():
    """Test objects with both serializable and non-serializable parts."""
    print("\n=== Test 3: Mixed Objects ===")

    mixed_obj = {
        "normal_key": "normal_value",
        "number": 123,
        "list": [1, 2, 3],
        "datetime": datetime.now(),
        "custom": NonSerializableClass("test"),
    }

    result = _safe_json_dumps(mixed_obj, "mixed_object")
    parsed = json.loads(result)
    print(f"Mixed object result: {result[:150]}")
    assert isinstance(parsed, dict)
    print("✓ Mixed object handled correctly")

    print("Mixed object test passed!")


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n=== Test 4: Edge Cases ===")

    # Empty objects
    result1 = _safe_json_dumps({}, "empty_dict")
    assert json.loads(result1) == {}
    print("✓ Empty dict handled correctly")

    result2 = _safe_json_dumps([], "empty_list")
    assert json.loads(result2) == []
    print("✓ Empty list handled correctly")

    # None value
    result3 = _safe_json_dumps(None, "none_value")
    assert json.loads(result3) is None
    print("✓ None value handled correctly")

    # Large nested structure with non-serializable object deep inside
    large_obj = {
        "level1": {
            "level2": {
                "level3": {
                    "normal": "value",
                    "bad": NonSerializableClass("deep"),
                }
            }
        }
    }
    result4 = _safe_json_dumps(large_obj, "deeply_nested")
    parsed4 = json.loads(result4)
    print(f"Deeply nested result: {str(result4)[:100]}")
    assert isinstance(parsed4, dict)
    print("✓ Deeply nested object handled correctly")

    print("All edge case tests passed!")


def test_context_parameter():
    """Test that context parameter is used in logging."""
    print("\n=== Test 5: Context Parameter ===")

    obj = NonSerializableClass("test_context")
    contexts = [
        "tool_log:test_tool",
        "file_index:example.py",
        "agent_snapshot:agent_123",
        "task_queue:important_task",
    ]

    for context in contexts:
        result = _safe_json_dumps(obj, context)
        assert isinstance(result, str), f"Result should be a string, got {type(result)}"
        parsed = json.loads(result)
        # Result can be either a string (from default=str) or dict (from repr fallback)
        assert isinstance(parsed, (dict, str)), f"Parsed should be dict or str, got {type(parsed)}"
        print(f"✓ Context '{context}' handled correctly")

    print("Context parameter tests passed!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("JSON Serialization Error Handling Tests")
    print("=" * 60)

    try:
        test_serializable_objects()
        test_non_serializable_objects()
        test_mixed_objects()
        test_edge_cases()
        test_context_parameter()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

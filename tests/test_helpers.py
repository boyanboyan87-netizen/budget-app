# tests/test_helpers.py
"""
Tests for helper functions in helpers.py

Run with: pytest
"""

from helpers import normalise_description


def test_normalise_description_removes_dates():
    """Test that normalise_description removes date patterns."""
    # ARRANGE - Set up test input
    input_text = "TESCO SUPERSTORE 12/01/2024"
    
    # ACT - Call the function
    result = normalise_description(input_text)
    
    # ASSERT - Check the result
    assert result == "TESCO SUPERSTORE"
    print(f"✅ Test passed: '{input_text}' → '{result}'")


def test_normalise_description_removes_numbers():
    """Test that normalise_description removes reference numbers."""
    input_text = "AMAZON REF:123456789"
    result = normalise_description(input_text)
    assert result == "AMAZON"


def test_normalise_description_handles_empty_string():
    """Test edge case: empty string input."""
    input_text = ""
    result = normalise_description(input_text)
    assert result == ""


def test_normalise_description_already_clean():
    """Test that clean merchant names are unchanged."""
    input_text = "SAINSBURYS"
    result = normalise_description(input_text)
    assert result == "SAINSBURYS"

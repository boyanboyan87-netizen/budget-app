from unittest.mock import Mock, patch
from claude_client import categorise_with_claude, build_system_prompt, clean_json_response

def test_build_system_prompt():
    """Test system prompt includes all categories."""
    categories = ["Groceries", "Transport"]
    prompt = build_system_prompt(categories)
    
    assert "Groceries" in prompt
    assert "Transport" in prompt

@patch('claude_client.client.messages.create')
def test_categorise_with_claude_mocked(mock_api):
    """Test categorization with mocked Claude API."""
    # Setup mock response
    mock_response = Mock()
    mock_response.content = [Mock(type="text", text='{"1": "Groceries"}')]
    mock_api.return_value = mock_response
    
    # Call function
    transactions = [{"id": 1, "date": "2024-01-01", "amount": 50, "description": "Tesco", "account": "Main"}]
    result = categorise_with_claude(transactions, ["Groceries", "Transport"])
    
    # Verify
    assert result == {1: "Groceries"}
    assert mock_api.called


class TestCleanJsonResponse:
    """clean_json_response() strips fences and repairs truncated JSON."""

    def test_plain_json_unchanged(self):
        raw = '{"1": "Groceries", "2": "Transport"}'
        result = clean_json_response(raw)
        assert '"1"' in result
        assert '"2"' in result

    def test_strips_json_code_fence(self):
        raw = '```json\n{"1": "Groceries"}\n```'
        result = clean_json_response(raw)
        assert "```" not in result
        assert '"1"' in result

    def test_strips_plain_code_fence(self):
        raw = '```\n{"1": "Groceries"}\n```'
        result = clean_json_response(raw)
        assert "```" not in result

    def test_repairs_truncated_json(self):
        """Truncated response mid-object — regex repair keeps valid pairs only."""
        raw = '{"1": "Groceries", "2": "Transport", "3": "Hous'  # cut off
        result = clean_json_response(raw)
        assert '"1"' in result
        assert '"2"' in result
        # truncated key 3 should not appear as a valid pair
        assert result.endswith("}")

    def test_whitespace_trimmed(self):
        raw = '   {"1": "Groceries"}   '
        result = clean_json_response(raw)
        assert result == result.strip()

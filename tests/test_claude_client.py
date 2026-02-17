from unittest.mock import Mock, patch
from claude_client import categorise_with_claude, build_system_prompt

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

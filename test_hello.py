def test_hello_world():
    """Simple test to verify pytest is working."""
    assert 1 + 1 == 2
    
def test_string_operations():
    """Test basic string operations."""
    greeting = "Hello, MCP Firewall!"
    assert len(greeting) > 0
    assert "MCP" in greeting
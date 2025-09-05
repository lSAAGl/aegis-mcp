"""
Smoke tests for MCP Firewall application.
"""

import pytest
from src.app import __version__


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_basic_imports():
    """Test that basic imports work."""
    import src.app
    assert hasattr(src.app, '__version__')
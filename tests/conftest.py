"""Pytest configuration and fixtures for LOTSE tests."""

import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).resolve().parent / "data"


@pytest.fixture
def lotse_repo_root():
    """Return path to repository root."""
    return Path(__file__).resolve().parent.parent

"""Integration test configuration for semantic memory."""

import pytest
import os
import asyncio
from datetime import datetime


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def project_id():
    """Default project ID for tests."""
    return 1


@pytest.fixture
def memory_content_samples():
    """Sample memory content for testing."""
    return {
        "fact": "Python uses duck typing for variable types",
        "pattern": "Always validate input parameters at function entry",
        "decision": "Use PostgreSQL for persistent storage",
        "context": "Project is in alpha phase with 3 team members",
    }

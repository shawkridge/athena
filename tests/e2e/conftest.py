"""Fixtures for E2E tests (requiring external services like LLM)."""

import pytest


@pytest.fixture(scope="session")
def llm_provider():
    """Detect which LLM provider is available.

    Skips tests if no LLM is configured/available.
    """
    import os
    from athena.core.config import LLM_PROVIDER, ENABLE_LLM_FEATURES

    if not ENABLE_LLM_FEATURES:
        pytest.skip("LLM features disabled (ENABLE_LLM_FEATURES=false)")

    provider = os.environ.get("LLM_PROVIDER", LLM_PROVIDER)
    return provider


@pytest.fixture
def ensure_llm_available(llm_provider):
    """Ensure LLM service is available before running test."""
    import requests
    from athena.core.config import LLAMACPP_REASONING_URL, CLAUDE_API_KEY

    if llm_provider == "llamacpp":
        try:
            # Quick health check
            response = requests.get(
                LLAMACPP_REASONING_URL.replace("/completion", ""),
                timeout=2
            )
            if response.status_code != 200:
                pytest.skip(f"LLM server not responding: {LLAMACPP_REASONING_URL}")
        except (requests.ConnectionError, requests.Timeout):
            pytest.skip(f"LLM server not accessible: {LLAMACPP_REASONING_URL}")

    elif llm_provider == "claude":
        if not CLAUDE_API_KEY:
            pytest.skip("CLAUDE_API_KEY not set")

    elif llm_provider == "ollama":
        pytest.skip("Ollama LLM testing not yet implemented")

    yield

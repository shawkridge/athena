"""Pytest configuration and fixtures for compression tests (v1.1).

Provides:
- Test fixtures for each compression feature
- Mock database utilities
- Assertion helpers
- Data generators for realistic test scenarios
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
from unittest.mock import MagicMock, Mock

from athena.compression import (
    CompressionConfig,
    CompressedMemory,
    CompressionLevel,
    TemporalDecayConfig,
    ImportanceWeightedBudgetConfig,
    ConsolidationCompressionConfig,
)


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def compression_config():
    """Default compression configuration."""
    return CompressionConfig()


@pytest.fixture
def temporal_decay_config():
    """Temporal decay configuration with default schedule."""
    return TemporalDecayConfig(
        enable=True,
        decay_schedule={
            'recent': 7,
            'detailed': 30,
            'gist': 90,
            'reference': 999,
        }
    )


@pytest.fixture
def importance_budget_config():
    """Importance budgeting configuration with default weights."""
    config = ImportanceWeightedBudgetConfig(
        enable=True,
        weights={
            'usefulness': 0.40,
            'recency': 0.30,
            'frequency': 0.20,
            'domain': 0.10,
        }
    )
    config.validate()
    return config


@pytest.fixture
def consolidation_compression_config():
    """Consolidation compression configuration."""
    return ConsolidationCompressionConfig(
        enable=True,
        generate_executive_summary=True,
        target_compression_ratio=0.1,  # 10x compression
        min_fidelity=0.85,
    )


# ============================================================================
# Memory Fixtures (Different Ages)
# ============================================================================


@pytest.fixture
def mock_memory_recent():
    """Memory created < 7 days ago (recent, not compressed)."""
    return {
        'id': 1,
        'content': 'User implemented JWT authentication with bcrypt hashing. '
                  'Tested with 47 test cases, all passing. '
                  'Documented in auth/JWT.md.',
        'created_at': datetime.now(),
        'usefulness_score': 0.95,
        'access_count': 10,
        'entity_type': 'decision',
        'tags': ['auth', 'jwt', 'security'],
    }


@pytest.fixture
def mock_memory_30day():
    """Memory created 15 days ago (should compress to summary level)."""
    return {
        'id': 2,
        'content': 'Fixed CORS headers issue affecting preflight requests. '
                  'Added OPTIONS method handler and proper headers. '
                  'Resolves #456 in issue tracker. '
                  'All e2e tests pass after fix.',
        'created_at': datetime.now() - timedelta(days=15),
        'usefulness_score': 0.75,
        'access_count': 3,
        'entity_type': 'action',
        'tags': ['cors', 'frontend', 'bug-fix'],
    }


@pytest.fixture
def mock_memory_60day():
    """Memory created 60 days ago (should compress to gist level)."""
    return {
        'id': 3,
        'content': 'Database connection pooling implementation with HikariCP. '
                  'Configured max pool size 20, min idle 5. '
                  'Reduced connection latency by 40%. '
                  'Load testing shows sustainable 1000 req/sec.',
        'created_at': datetime.now() - timedelta(days=60),
        'usefulness_score': 0.65,
        'access_count': 2,
        'entity_type': 'pattern',
        'tags': ['database', 'performance', 'infrastructure'],
    }


@pytest.fixture
def mock_memory_150day():
    """Memory created 150 days ago (should compress to reference level)."""
    return {
        'id': 4,
        'content': 'Initial project architecture decisions. '
                  'Chose microservices pattern with Docker containers. '
                  'Kubernetes for orchestration. '
                  'Event-driven messaging with RabbitMQ.',
        'created_at': datetime.now() - timedelta(days=150),
        'usefulness_score': 0.40,
        'access_count': 1,
        'entity_type': 'context',
        'tags': ['architecture', 'infra', 'decisions'],
    }


@pytest.fixture
def mock_memories_mixed_age(
    mock_memory_recent,
    mock_memory_30day,
    mock_memory_60day,
    mock_memory_150day,
):
    """Collection of memories spanning different ages."""
    return [
        mock_memory_recent,
        mock_memory_30day,
        mock_memory_60day,
        mock_memory_150day,
    ]


# ============================================================================
# Database Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_db(tmp_path):
    """Mock database for testing (in-memory equivalent)."""
    class MockDatabase:
        def __init__(self):
            self.memories = {}
            self.compression_metrics = []

        def store_memory(self, memory_dict: Dict) -> int:
            """Store memory and return ID."""
            memory_id = max(self.memories.keys()) + 1 if self.memories else 1
            self.memories[memory_id] = memory_dict
            return memory_id

        def get_memory(self, memory_id: int) -> Dict:
            """Get memory by ID."""
            return self.memories.get(memory_id)

        def list_memories(self, limit: int = 10) -> List[Dict]:
            """List all memories."""
            return list(self.memories.values())[:limit]

        def update_memory(self, memory_id: int, updates: Dict):
            """Update memory fields."""
            if memory_id in self.memories:
                self.memories[memory_id].update(updates)

    return MockDatabase()


# ============================================================================
# Assertion Helpers
# ============================================================================


class CompressionAssertions:
    """Custom assertions for compression tests."""

    @staticmethod
    def assert_compression_valid(original: str,
                                compressed: str,
                                min_ratio: float = 0.1,
                                max_ratio: float = 1.0):
        """Assert compressed content is valid."""
        assert compressed, "Compressed should not be empty"
        assert len(compressed) < len(original), "Compressed should be shorter"

        ratio = len(compressed) / len(original)
        assert min_ratio <= ratio <= max_ratio, \
            f"Compression ratio {ratio:.2f} outside [{min_ratio}, {max_ratio}]"

    @staticmethod
    def assert_token_savings(original_tokens: int,
                            compressed_tokens: int,
                            min_savings_percent: float = 0.1):
        """Assert compression saves tokens."""
        assert compressed_tokens <= original_tokens, \
            "Compressed tokens should be less than or equal to original"

        if original_tokens > 0:
            savings_percent = 1.0 - (compressed_tokens / original_tokens)
            assert savings_percent >= min_savings_percent, \
                f"Savings {savings_percent:.1%} below minimum {min_savings_percent:.1%}"

    @staticmethod
    def assert_memory_age_matches_level(age_days: int,
                                       compression_level: CompressionLevel):
        """Assert compression level matches memory age."""
        if age_days < 7:
            assert compression_level == CompressionLevel.NONE
        elif age_days < 30:
            assert compression_level == CompressionLevel.SUMMARY
        elif age_days < 90:
            assert compression_level == CompressionLevel.GIST
        else:
            assert compression_level == CompressionLevel.REFERENCE

    @staticmethod
    def assert_importance_score_valid(score: float):
        """Assert importance score is in valid range."""
        assert 0.0 <= score <= 1.0, f"Score {score} not in [0.0, 1.0]"


@pytest.fixture
def compression_assert():
    """Provide compression assertions."""
    return CompressionAssertions()


# ============================================================================
# Data Generator Helpers
# ============================================================================


class TestDataGenerator:
    """Generate realistic test data."""

    @staticmethod
    def generate_memory(
        memory_id: int = 1,
        age_days: int = 0,
        usefulness: float = 0.8,
        access_count: int = 5,
        entity_type: str = 'fact',
        content_tokens: int = 100,
    ) -> Dict:
        """Generate a realistic memory."""
        return {
            'id': memory_id,
            'content': 'A' * (int(content_tokens * 4)),  # ~4 chars per token
            'created_at': datetime.now() - timedelta(days=age_days),
            'usefulness_score': usefulness,
            'access_count': access_count,
            'entity_type': entity_type,
            'tags': [entity_type, 'test'],
        }

    @staticmethod
    def generate_memories(count: int = 10) -> List[Dict]:
        """Generate multiple memories with realistic distribution."""
        memories = []
        for i in range(count):
            # Distribute ages: some recent, some old
            age = int((i / count) * 180)  # Spread from 0-180 days

            # Distribute usefulness: higher for recent
            usefulness = max(0.2, 1.0 - (age / 200.0))

            memory = TestDataGenerator.generate_memory(
                memory_id=i + 1,
                age_days=age,
                usefulness=usefulness,
                access_count=max(1, 10 - (age // 30)),  # More accesses = more recent
                entity_type=['fact', 'pattern', 'decision', 'context'][i % 4],
            )
            memories.append(memory)

        return memories


@pytest.fixture
def test_data_generator():
    """Provide test data generator."""
    return TestDataGenerator()


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "compression: mark test as compression-related"
    )
    config.addinivalue_line(
        "markers",
        "temporal_decay: mark test as temporal decay feature"
    )
    config.addinivalue_line(
        "markers",
        "importance_budgeting: mark test as importance budgeting feature"
    )
    config.addinivalue_line(
        "markers",
        "consolidation: mark test as consolidation compression feature"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (>1 second)"
    )


# ============================================================================
# Session-Wide Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_session_config():
    """Configuration for entire test session."""
    return {
        'compression_enabled': True,
        'max_age_recent': 7,
        'max_age_detailed': 30,
        'max_age_gist': 90,
        'target_compression_ratio': 0.1,  # 10x
        'min_fidelity': 0.85,
    }

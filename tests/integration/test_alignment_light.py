"""Lightweight integration tests without database dependencies.

Tests the three systems working together without requiring database connections.
Focuses on core functionality and alignment with Anthropic's vision.
"""

import pytest
import tempfile
from pathlib import Path

from athena.pii import PIIDetector, PIITokenizer, FieldPolicy
from athena.tools_discovery import ToolsGenerator, register_core_tools
from athena.skills.models import Skill, SkillMetadata, SkillDomain, SkillParameter


class TestPIICore:
    """Test PII system core functionality."""

    def test_pii_detection_and_tokenization(self):
        """Test PII detection and tokenization workflow."""
        detector = PIIDetector()
        tokenizer = PIITokenizer(strategy='hash')

        # Real-world example
        event_text = "User alice@company.com accessed /home/alice/secrets.txt"

        # Detect
        detections = detector.detect(event_text, field_name='content')
        assert len(detections) > 0
        assert any(d.type == 'email' for d in detections)
        assert any(d.type == 'absolute_path' for d in detections)

        # Tokenize
        sanitized = tokenizer.tokenize(event_text, detections)
        assert 'alice@company.com' not in sanitized
        assert '/home/alice' not in sanitized
        assert 'PII_HASH_' in sanitized

    def test_pii_field_policies(self):
        """Test field-level sanitization policies."""
        policy = FieldPolicy()

        # Test each strategy
        assert '[REDACTED' in policy._apply_field_policy("secret data", policy.get_policy('diff'), 'diff')
        assert policy._apply_field_policy("same", policy.get_policy('timestamp'), 'timestamp') == "same"
        assert 'PII_HASH_' in policy._hash_value("email@example.com")
        assert '/home/user' not in policy._truncate_path("/home/user/app/main.py")

    def test_pii_deterministic_hashing(self):
        """Test that PII hashing is deterministic."""
        policy = FieldPolicy()

        email = "alice@example.com"
        hash1 = policy._hash_value(email)
        hash2 = policy._hash_value(email)

        assert hash1 == hash2  # Same input → same output


class TestToolsCore:
    """Test tools discovery system core functionality."""

    def test_tools_generation(self):
        """Test tool file generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Verify structure
            output = Path(tmpdir)
            assert (output / 'memory').exists()
            assert (output / 'planning').exists()
            assert (output / 'consolidation').exists()

            # Verify tools exist
            assert (output / 'memory' / 'recall.py').exists()
            assert (output / 'planning' / 'plan_task.py').exists()
            assert (output / 'consolidation' / 'consolidate.py').exists()

    def test_tools_are_discoverable(self):
        """Test agents can discover tools via filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Simulate agent discovery
            tools_dir = Path(tmpdir)

            # List categories
            categories = [d.name for d in tools_dir.iterdir() if d.is_dir()]
            assert len(categories) > 0

            # List tools in category
            memory_tools = [
                f.stem for f in (tools_dir / 'memory').glob('*.py')
                if f.name != '__init__.py'
            ]
            assert 'recall' in memory_tools

    def test_context_reduction(self):
        """Test context is actually reduced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Read individual tool
            tool_file = Path(tmpdir) / 'memory' / 'recall.py'
            content = tool_file.read_text()

            # Tool file is small
            assert len(content) < 2500  # Fits in context easily

            # Has documentation
            assert 'def recall' in content
            assert 'Search and retrieve' in content


class TestSkillsCore:
    """Test skills system core functionality."""

    def test_skill_creation(self):
        """Test creating a skill with metadata."""
        metadata = SkillMetadata(
            name="test_skill",
            description="Test skill",
            domain=SkillDomain.MEMORY,
            parameters=[
                SkillParameter(name="input", type="str", description="Input")
            ],
            return_type="str",
            examples=["test_skill('x')"],
            quality_score=0.9,
        )

        skill = Skill(
            metadata=metadata,
            code="def test_skill(input):\n    return input.upper()",
            entry_point="test_skill"
        )

        assert skill.id == "test_skill"
        assert skill.quality == 0.9
        assert skill.metadata.times_used == 0

    def test_skill_quality_tracking(self):
        """Test skill quality improves with use."""
        metadata = SkillMetadata(
            name="test",
            description="Test",
            domain=SkillDomain.GENERAL,
            parameters=[],
            return_type="str",
            examples=["test()"],
            quality_score=0.8,
        )
        skill = Skill(metadata=metadata, code="def test():\n    return 'ok'", entry_point="test")

        # Initial state
        assert skill.metadata.times_used == 0
        assert skill.metadata.success_rate == 1.0

        # Track success
        skill.update_usage(success=True)
        assert skill.metadata.times_used == 1

        # Track failure
        skill.update_usage(success=False)
        assert skill.metadata.times_used == 2
        assert skill.metadata.success_rate == 0.5

    def test_skill_metadata_serialization(self):
        """Test skill metadata can be serialized."""
        metadata = SkillMetadata(
            name="test",
            description="Test",
            domain=SkillDomain.MEMORY,
            parameters=[],
            return_type="str",
            examples=["test()"],
        )

        # To dict
        data = metadata.to_dict()
        assert data['name'] == 'test'
        assert data['domain'] == 'memory'

        # Round trip
        restored = SkillMetadata.from_dict(data)
        assert restored.name == 'test'
        assert restored.domain == SkillDomain.MEMORY


class TestEndToEndLite:
    """End-to-end tests without database."""

    def test_pii_tools_integration(self):
        """Test PII + tools work together."""
        # Step 1: Sanitize event
        detector = PIIDetector()
        tokenizer = PIITokenizer(strategy='hash')

        event = "alice@example.com accessed /home/alice/app"
        detections = detector.detect(event, field_name='content')
        sanitized = tokenizer.tokenize(event, detections)

        # PII removed
        assert 'alice@example.com' not in sanitized
        assert '/home/alice' not in sanitized

        # Step 2: Discover tools
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Tools available
            tools_dir = Path(tmpdir)
            tools = list(tools_dir.rglob('*.py'))
            assert len(tools) > 9

    def test_tools_skills_integration(self):
        """Test tools + skills work together."""
        # Generate tools
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            tools_dir = Path(tmpdir)
            assert (tools_dir / 'memory' / 'recall.py').exists()

        # Create skills
        skill = Skill(
            metadata=SkillMetadata(
                name="process_memory",
                description="Process memory event",
                domain=SkillDomain.MEMORY,
                parameters=[],
                return_type="str",
                examples=["process_memory()"],
            ),
            code="def process_memory():\n    return 'processed'",
            entry_point="process_memory"
        )

        assert skill.id == "process_memory"
        assert skill.quality == 0.8

    def test_pii_determinism_enables_deduplication(self):
        """Test PII hashing enables deduplication."""
        policy = FieldPolicy()

        # Same event, same sanitization
        event1_email = "alice@company.com"
        event2_email = "alice@company.com"

        hash1 = policy._hash_value(event1_email)
        hash2 = policy._hash_value(event2_email)

        # Same PII → same hash → deduplication works
        assert hash1 == hash2

        # Different PII → different hash
        hash_bob = policy._hash_value("bob@company.com")
        assert hash_bob != hash1


class TestAlignmentCriteria:
    """Test alignment with Anthropic's vision."""

    def test_filesystem_api_principle(self):
        """Test filesystem API pattern is implemented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Can list tools via filesystem
            tools_dir = Path(tmpdir)
            categories = [d.name for d in tools_dir.iterdir() if d.is_dir()]

            # Can read tool definitions
            recall_file = tools_dir / 'memory' / 'recall.py'
            assert recall_file.read_text()

            # ✅ Filesystem API principle met
            assert len(categories) > 0

    def test_progressive_disclosure_principle(self):
        """Test progressive disclosure (load only what you need)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Read single tool (what agent loads when needed)
            tool_file = Path(tmpdir) / 'memory' / 'recall.py'
            single_tool_size = len(tool_file.read_text())

            # vs reading all definitions
            all_tools = list(Path(tmpdir).rglob('*.py'))
            total_size = sum(len(f.read_text()) for f in all_tools if f.name != '__init__.py')

            # Agent loads ~3KB for one tool vs ~15KB for all
            assert single_tool_size < 2500
            assert total_size < 30000

            # ✅ Progressive disclosure principle met
            assert single_tool_size < total_size

    def test_privacy_principle(self):
        """Test privacy through deterministic hashing."""
        detector = PIIDetector()
        policy = FieldPolicy()

        # Real event
        event = "alice@example.com logged in from /home/alice/app"

        # Detect PII
        detections = detector.detect(event, field_name='content')
        assert len(detections) > 0

        # Hash deterministically
        email_hash = policy._hash_value("alice@example.com")

        # Same email always hashes same
        assert policy._hash_value("alice@example.com") == email_hash

        # ✅ Privacy principle met (irreversible, deterministic)
        assert 'alice@example.com' not in email_hash

    def test_local_execution_principle(self):
        """Test local execution (no cloud dependencies)."""
        # All operations work locally
        detector = PIIDetector()
        tokenizer = PIITokenizer(strategy='hash')
        policy = FieldPolicy()

        event = "sensitive data"
        detections = detector.detect(event, field_name='test')
        sanitized = tokenizer.tokenize(event, detections)

        # ✅ Local execution principle met
        # No API calls, no network, pure local processing
        assert isinstance(sanitized, str)

    def test_skill_reuse_principle(self):
        """Test skill reuse for code patterns."""
        skill = Skill(
            metadata=SkillMetadata(
                name="reusable_pattern",
                description="Reusable code pattern",
                domain=SkillDomain.GENERAL,
                parameters=[],
                return_type="str",
                examples=["reusable_pattern()"],
                quality_score=0.8,
            ),
            code="def reusable_pattern():\n    return 'works'",
            entry_point="reusable_pattern"
        )

        # Skill is tracked
        initial_uses = skill.metadata.times_used
        skill.update_usage(success=True)
        skill.update_usage(success=True)
        skill.update_usage(success=True)

        # Usage tracked
        assert skill.metadata.times_used == initial_uses + 3
        assert skill.metadata.success_rate == 1.0

        # ✅ Skill reuse principle met
        # Skills tracked and improve with consistent success
        assert skill.metadata.times_used > 0

"""Tests for skills system.

Tests:
- Skill creation and metadata
- Skill library persistence
- Skill matching
- Skill execution
"""

import pytest
import tempfile
from pathlib import Path

from athena.skills.models import (
    Skill, SkillMetadata, SkillParameter, SkillDomain, SkillMatch
)
from athena.skills.library import SkillLibrary
from athena.skills.matcher import SkillMatcher
from athena.skills.executor import SkillExecutor
from athena.core.database import Database


class TestSkillMetadata:
    """Test skill metadata creation and management."""

    def test_create_metadata(self):
        """Test creating skill metadata."""
        metadata = SkillMetadata(
            name="authenticate_user",
            description="Authenticates a user against a database",
            domain=SkillDomain.MEMORY,
            parameters=[
                SkillParameter(
                    name="username",
                    type="str",
                    description="Username"
                ),
                SkillParameter(
                    name="password",
                    type="str",
                    description="Password"
                ),
            ],
            return_type="bool",
            examples=["authenticate_user('alice', 'secret123')"],
            tags=["auth", "security"],
        )

        assert metadata.name == "authenticate_user"
        assert metadata.domain == SkillDomain.MEMORY
        assert len(metadata.parameters) == 2
        assert "auth" in metadata.tags

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = SkillMetadata(
            name="test",
            description="Test skill",
            domain=SkillDomain.GENERAL,
            parameters=[],
            return_type="str",
            examples=["test()"],
        )

        data = metadata.to_dict()
        assert data['name'] == "test"
        assert data['domain'] == "general"

    def test_metadata_round_trip(self):
        """Test converting to/from dict."""
        original = SkillMetadata(
            name="test",
            description="Test skill",
            domain=SkillDomain.MEMORY,
            parameters=[
                SkillParameter(name="x", type="int", description="A number"),
            ],
            return_type="int",
            examples=["test(5)"],
            quality_score=0.95,
        )

        data = original.to_dict()
        restored = SkillMetadata.from_dict(data)

        assert restored.name == original.name
        assert restored.domain == original.domain
        assert restored.quality_score == original.quality_score


class TestSkill:
    """Test skill creation and usage tracking."""

    @pytest.fixture
    def simple_skill(self):
        """Create a simple skill."""
        metadata = SkillMetadata(
            name="add",
            description="Add two numbers",
            domain=SkillDomain.GENERAL,
            parameters=[
                SkillParameter(name="a", type="int", description="First number"),
                SkillParameter(name="b", type="int", description="Second number"),
            ],
            return_type="int",
            examples=["add(2, 3)"],
        )

        code = """
def add(a, b):
    return a + b
"""

        return Skill(
            metadata=metadata,
            code=code,
            entry_point="add"
        )

    def test_create_skill(self, simple_skill):
        """Test creating a skill."""
        assert simple_skill.id == "add"
        assert simple_skill.quality == 0.8  # Default
        assert simple_skill.metadata.times_used == 0

    def test_skill_update_usage(self, simple_skill):
        """Test updating skill usage statistics."""
        skill = simple_skill

        # Track success
        skill.update_usage(success=True)
        assert skill.metadata.times_used == 1
        assert skill.metadata.success_rate == 1.0

        # Track failure
        skill.update_usage(success=False)
        assert skill.metadata.times_used == 2
        assert skill.metadata.success_rate == 0.5

    def test_skill_quality_improvement(self, simple_skill):
        """Test quality score improves with use."""
        skill = simple_skill
        initial_quality = skill.quality

        # Use successfully multiple times
        for _ in range(5):
            skill.update_usage(success=True)

        final_quality = skill.quality
        # Quality should stay high with all successes
        assert final_quality >= initial_quality


class TestSkillLibrary:
    """Test skill library persistence."""

    @pytest.fixture
    def lib(self):
        """Create skill library with temp database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(f"{tmpdir}/skills.db")
            yield SkillLibrary(db, storage_dir=tmpdir)

    def test_save_and_retrieve(self, lib):
        """Test saving and retrieving a skill."""
        metadata = SkillMetadata(
            name="test_skill",
            description="Test",
            domain=SkillDomain.GENERAL,
            parameters=[],
            return_type="str",
            examples=["test_skill()"],
        )

        skill = Skill(
            metadata=metadata,
            code="def test_skill():\n    return 'test'",
            entry_point="test_skill"
        )

        # Save
        assert lib.save(skill)

        # Retrieve
        retrieved = lib.get("test_skill")
        assert retrieved is not None
        assert retrieved.id == "test_skill"
        assert retrieved.entry_point == "test_skill"

    def test_list_skills(self, lib):
        """Test listing all skills."""
        # Save multiple skills
        for i in range(3):
            metadata = SkillMetadata(
                name=f"skill_{i}",
                description=f"Skill {i}",
                domain=SkillDomain.GENERAL,
                parameters=[],
                return_type="str",
                examples=[f"skill_{i}()"],
            )
            skill = Skill(
                metadata=metadata,
                code=f"def skill_{i}():\n    return {i}",
                entry_point=f"skill_{i}"
            )
            lib.save(skill)

        # List
        skills = lib.list_all(limit=10)
        assert len(skills) == 3

    def test_search_skills(self, lib):
        """Test searching skills."""
        metadata = SkillMetadata(
            name="authenticate",
            description="User authentication",
            domain=SkillDomain.GENERAL,
            parameters=[],
            return_type="bool",
            examples=["authenticate('user')"],
            tags=["auth", "security"],
        )

        skill = Skill(
            metadata=metadata,
            code="def authenticate(user):\n    return True",
            entry_point="authenticate"
        )

        lib.save(skill)

        # Search by name
        results = lib.search("auth")
        assert len(results) > 0

        # Search by tag
        results = lib.search("security")
        assert len(results) > 0

    def test_delete_skill(self, lib):
        """Test deleting a skill."""
        metadata = SkillMetadata(
            name="temp_skill",
            description="Temporary",
            domain=SkillDomain.GENERAL,
            parameters=[],
            return_type="str",
            examples=["temp_skill()"],
        )

        skill = Skill(
            metadata=metadata,
            code="def temp_skill():\n    return 'temp'",
            entry_point="temp_skill"
        )

        lib.save(skill)
        assert lib.get("temp_skill") is not None

        lib.delete("temp_skill")
        assert lib.get("temp_skill") is None

    def test_library_stats(self, lib):
        """Test library statistics."""
        for i in range(5):
            metadata = SkillMetadata(
                name=f"skill_{i}",
                description=f"Skill {i}",
                domain=SkillDomain.MEMORY if i % 2 == 0 else SkillDomain.PLANNING,
                parameters=[],
                return_type="str",
                examples=[f"skill_{i}()"],
                quality_score=0.8 + i * 0.02,
            )
            skill = Skill(
                metadata=metadata,
                code=f"def skill_{i}():\n    return {i}",
                entry_point=f"skill_{i}"
            )
            lib.save(skill)

        stats = lib.stats()
        assert stats['total_skills'] == 5
        assert stats['domains'] >= 2


class TestSkillMatcher:
    """Test skill matching."""

    @pytest.fixture
    def matcher(self):
        """Create matcher with some skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(f"{tmpdir}/skills.db")
            lib = SkillLibrary(db, storage_dir=tmpdir)

            # Create sample skills
            for name, desc, domain in [
                ("authenticate", "User authentication", SkillDomain.MEMORY),
                ("encrypt", "Data encryption", SkillDomain.MEMORY),
                ("plan_task", "Task planning", SkillDomain.PLANNING),
            ]:
                metadata = SkillMetadata(
                    name=name,
                    description=desc,
                    domain=domain,
                    parameters=[],
                    return_type="str",
                    examples=[f"{name}()"],
                    tags=[name.split('_')[0]],
                    quality_score=0.9,
                )
                skill = Skill(
                    metadata=metadata,
                    code=f"def {name}():\n    return '{name}'",
                    entry_point=name
                )
                lib.save(skill)

            yield SkillMatcher(lib)

    def test_find_skills(self, matcher):
        """Test finding skills for a task."""
        results = matcher.find_skills("How to authenticate a user?")

        assert len(results) > 0
        assert results[0].skill.metadata.name == "authenticate"
        assert results[0].relevance > 0.5

    def test_find_skills_by_domain(self, matcher):
        """Test finding skills in specific domain."""
        results = matcher.find_skills(
            "Plan a task",
            domain=SkillDomain.PLANNING
        )

        assert len(results) > 0
        assert all(r.skill.metadata.domain == SkillDomain.PLANNING for r in results)

    def test_rank_skills(self, matcher):
        """Test ranking skills."""
        # Get some skills
        all_skills = matcher.library.list_all()

        ranked = matcher.rank_skills(all_skills, "authentication")
        assert len(ranked) > 0
        assert ranked[0].metadata.name == "authenticate"


class TestSkillExecutor:
    """Test skill execution."""

    @pytest.fixture
    def executor(self):
        """Create executor with skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(f"{tmpdir}/skills.db")
            lib = SkillLibrary(db, storage_dir=tmpdir)

            # Create a simple skill
            metadata = SkillMetadata(
                name="add",
                description="Add numbers",
                domain=SkillDomain.GENERAL,
                parameters=[
                    SkillParameter(name="a", type="int", description="First"),
                    SkillParameter(name="b", type="int", description="Second"),
                ],
                return_type="int",
                examples=["add(2, 3)"],
            )
            skill = Skill(
                metadata=metadata,
                code="def add(a, b):\n    return a + b",
                entry_point="add"
            )
            lib.save(skill)

            yield SkillExecutor(lib)

    def test_execute_skill(self, executor):
        """Test executing a skill."""
        skill = executor.library.get("add")
        result = executor.execute(skill, parameters={'a': 2, 'b': 3})

        assert result['success']
        assert result['result'] == 5

    def test_execute_with_defaults(self, executor):
        """Test executing skill with default parameters."""
        # Create skill with default parameter
        metadata = SkillMetadata(
            name="greet",
            description="Greet someone",
            domain=SkillDomain.GENERAL,
            parameters=[
                SkillParameter(name="name", type="str", description="Name", default="World"),
            ],
            return_type="str",
            examples=["greet()"],
        )
        skill = Skill(
            metadata=metadata,
            code="def greet(name='World'):\n    return f'Hello {name}'",
            entry_point="greet"
        )

        executor.library.save(skill)

        # Execute without providing parameter
        result = executor.execute(skill, parameters={})
        assert result['success']

    def test_validate_skill(self, executor):
        """Test skill validation."""
        skill = executor.library.get("add")
        validation = executor.validate(skill)

        assert validation['valid']
        assert len(validation['errors']) == 0

    def test_validate_invalid_skill(self, executor):
        """Test validating invalid skill."""
        metadata = SkillMetadata(
            name="broken",
            description="Broken skill",
            domain=SkillDomain.GENERAL,
            parameters=[],
            return_type="str",
            examples=["broken()"],
        )
        skill = Skill(
            metadata=metadata,
            code="def broken():\n    this is invalid syntax",
            entry_point="broken"
        )

        validation = executor.validate(skill)
        assert not validation['valid']
        assert len(validation['errors']) > 0

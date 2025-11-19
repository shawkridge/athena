"""Tests for phenomenal consciousness (qualia, emotions, embodiment)."""

import pytest
from datetime import datetime
from athena.consciousness.phenomenal import (
    Quale,
    EmotionType,
    EmotionalState,
    EmbodiedState,
    BodyAwareness,
    QualiaGenerator,
    EmotionSystem,
    EmbodimentSystem,
    PhenomenalConsciousness,
)


class TestQualia:
    """Test quale (subjective quality) representation."""

    def test_quale_creation(self):
        """Test creating a quale."""
        quale = Quale(
            name="redness",
            intensity=7.5,
            distinctiveness=0.8,
            valence=0.5,
        )
        assert quale.name == "redness"
        assert quale.intensity == 7.5
        assert quale.distinctiveness == 0.8
        assert quale.valence == 0.5
        assert isinstance(quale.timestamp, datetime)

    def test_quale_valence_range(self):
        """Test that qualia valence is in [-1, 1]."""
        quale = Quale(
            name="test",
            intensity=5.0,
            distinctiveness=0.5,
            valence=-0.8,
        )
        assert -1 <= quale.valence <= 1


class TestEmotionalState:
    """Test emotional state representation."""

    def test_emotional_state_creation(self):
        """Test creating emotional state."""
        state = EmotionalState(
            primary_emotion=EmotionType.JOY,
            valence=0.7,
            arousal=0.6,
            dominance=0.8,
            intensity=7.5,
        )
        assert state.primary_emotion == EmotionType.JOY
        assert state.valence == 0.7
        assert state.arousal == 0.6

    def test_emotional_state_to_dict(self):
        """Test converting emotional state to dict."""
        state = EmotionalState(
            primary_emotion=EmotionType.SADNESS,
            valence=-0.8,
            arousal=0.2,
            dominance=0.3,
            intensity=5.0,
        )
        result = state.to_dict()

        assert result["primary_emotion"] == "sadness"
        assert result["valence"] == -0.8
        assert "timestamp" in result

    def test_emotional_state_constraints(self):
        """Test emotional state value constraints."""
        state = EmotionalState(
            primary_emotion=EmotionType.JOY,
            valence=0.5,
            arousal=0.5,
            dominance=0.5,
            intensity=5.0,
        )
        assert -1 <= state.valence <= 1
        assert 0 <= state.arousal <= 1
        assert 0 <= state.dominance <= 1


class TestEmbodiedState:
    """Test embodied state representation."""

    def test_embodied_state_creation(self):
        """Test creating embodied state."""
        state = EmbodiedState(
            body_awareness=0.8,
            spatial_presence=0.7,
            agency=0.9,
            proprioception=0.8,
            interoception=0.6,
        )
        assert state.body_awareness == 0.8
        assert state.total_embodiment > 0

    def test_embodied_state_calculation(self):
        """Test that total embodiment is calculated."""
        state = EmbodiedState(
            body_awareness=0.8,
            spatial_presence=0.8,
            agency=0.8,
            proprioception=0.8,
            interoception=0.8,
        )
        # Average of all 5 components * 10 = 8.0
        assert abs(state.total_embodiment - 8.0) < 0.1

    def test_embodied_state_to_dict(self):
        """Test converting embodied state to dict."""
        state = EmbodiedState(
            body_awareness=0.7,
            spatial_presence=0.6,
            agency=0.8,
            proprioception=0.7,
            interoception=0.5,
        )
        result = state.to_dict()

        assert "body_awareness" in result
        assert "total_embodiment" in result
        assert result["body_awareness"] == 0.7


class TestBodyAwareness:
    """Test body awareness levels."""

    def test_body_awareness_levels(self):
        """Test different body awareness levels."""
        assert BodyAwareness.MINIMAL.value == 0.2
        assert BodyAwareness.WEAK.value == 0.4
        assert BodyAwareness.MODERATE.value == 0.6
        assert BodyAwareness.STRONG.value == 0.8
        assert BodyAwareness.INTENSE.value == 1.0


class TestQualiaGenerator:
    """Test qualia generation."""

    def test_qualia_generator_creation(self):
        """Test creating qualia generator."""
        gen = QualiaGenerator()
        assert gen is not None
        assert len(gen.qualia_space) > 0

    @pytest.mark.asyncio
    async def test_generate_qualia_from_indicators(self):
        """Test generating qualia from consciousness indicators."""
        gen = QualiaGenerator()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 8.0,
            "selective_attention": 7.0,
            "working_memory": 7.5,
            "temporal_continuity": 7.0,
        }

        qualia = await gen.generate_qualia_from_indicators(indicators)

        assert len(qualia) > 0
        for quale in qualia:
            assert isinstance(quale, Quale)
            assert 0 <= quale.intensity <= 10
            assert -1 <= quale.valence <= 1
            assert 0 <= quale.distinctiveness <= 1

    @pytest.mark.asyncio
    async def test_generate_qualia_low_indicators(self):
        """Test generating qualia with low indicators."""
        gen = QualiaGenerator()

        indicators = {
            "global_workspace": 2.0,
            "information_integration": 2.0,
            "selective_attention": 2.0,
            "working_memory": 2.0,
            "temporal_continuity": 2.0,
        }

        qualia = await gen.generate_qualia_from_indicators(indicators)

        # Low indicators should produce fewer/weaker qualia
        for quale in qualia:
            assert quale.intensity < 5.0

    def test_qualia_diversity_calculation(self):
        """Test calculating qualia diversity."""
        gen = QualiaGenerator()

        qualia = [
            Quale("red", 8.0, 0.9, 0.5),
            Quale("blue", 7.5, 0.85, 0.3),
            Quale("warm", 6.0, 0.7, 0.8),
        ]

        diversity = gen.calculate_qualia_diversity(qualia)

        assert 0 <= diversity <= 10
        assert diversity > 0  # Should have some diversity

    def test_qualia_diversity_empty(self):
        """Test diversity with no qualia."""
        gen = QualiaGenerator()
        diversity = gen.calculate_qualia_diversity([])
        assert diversity == 0.0

    def test_qualia_diversity_identical(self):
        """Test diversity with identical qualia."""
        gen = QualiaGenerator()

        qualia = [
            Quale("same", 5.0, 0.5, 0.0),
            Quale("same", 5.0, 0.5, 0.0),
        ]

        diversity = gen.calculate_qualia_diversity(qualia)

        # Identical qualia should have lower diversity
        assert diversity < 5.0


class TestEmotionSystem:
    """Test emotion inference system."""

    def test_emotion_system_creation(self):
        """Test creating emotion system."""
        system = EmotionSystem()
        assert system is not None
        assert len(system.emotion_space) > 0

    @pytest.mark.asyncio
    async def test_infer_emotion_joyful(self):
        """Test inferring joy from indicators."""
        system = EmotionSystem()

        indicators = {
            "global_workspace": 9.0,
            "information_integration": 8.0,
            "selective_attention": 7.0,
            "meta_cognition": 8.0,
        }

        emotion = await system.infer_emotion(indicators)

        assert emotion.valence > 0.3  # Positive valence for high GW
        assert isinstance(emotion.primary_emotion, EmotionType)

    @pytest.mark.asyncio
    async def test_infer_emotion_sad(self):
        """Test inferring sadness from low indicators."""
        system = EmotionSystem()

        indicators = {
            "global_workspace": 2.0,
            "information_integration": 2.0,
            "selective_attention": 2.0,
            "meta_cognition": 2.0,
        }

        emotion = await system.infer_emotion(indicators)

        assert emotion.valence < 0.3  # Negative valence
        assert emotion.arousal < 0.5  # Low arousal

    @pytest.mark.asyncio
    async def test_infer_emotion_with_qualia(self):
        """Test emotion inference influenced by qualia."""
        system = EmotionSystem()

        indicators = {
            "global_workspace": 5.0,
            "information_integration": 5.0,
            "selective_attention": 5.0,
            "meta_cognition": 5.0,
        }

        qualia = [
            Quale("pleasant", 8.0, 0.8, 0.8),
            Quale("calm", 6.0, 0.7, 0.6),
        ]

        emotion = await system.infer_emotion(indicators, qualia)

        # Positive qualia should increase valence
        assert emotion.valence > 0.2

    @pytest.mark.asyncio
    async def test_emotion_intensity_calculation(self):
        """Test emotion intensity calculation."""
        system = EmotionSystem()

        indicators = {
            "global_workspace": 9.0,
            "information_integration": 9.0,
            "selective_attention": 8.0,
            "meta_cognition": 8.0,
        }

        emotion = await system.infer_emotion(indicators)

        # High indicators should give high intensity
        assert emotion.intensity > 5.0


class TestEmbodimentSystem:
    """Test embodiment calculation."""

    def test_embodiment_system_creation(self):
        """Test creating embodiment system."""
        system = EmbodimentSystem()
        assert system is not None

    @pytest.mark.asyncio
    async def test_calculate_embodiment(self):
        """Test calculating embodiment from indicators."""
        system = EmbodimentSystem()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 7.0,
            "selective_attention": 6.0,
            "working_memory": 7.0,
            "meta_cognition": 8.0,
            "temporal_continuity": 7.0,
        }

        embodied = await system.calculate_embodiment(indicators)

        assert 0 <= embodied.body_awareness <= 1
        assert 0 <= embodied.agency <= 1
        assert embodied.total_embodiment > 0

    @pytest.mark.asyncio
    async def test_modulate_embodiment(self):
        """Test modulating embodiment by disembodying stimulus."""
        system = EmbodimentSystem()

        indicators = {
            "global_workspace": 8.0,
            "information_integration": 8.0,
            "selective_attention": 7.0,
            "working_memory": 8.0,
            "meta_cognition": 8.0,
            "temporal_continuity": 8.0,
        }

        state = await system.calculate_embodiment(indicators)
        original_embodiment = state.total_embodiment

        # Apply disembodying stimulus (like meditation or VR)
        modified = system.modulate_embodiment(state, disembodied_stimulus=0.5)

        # Should reduce embodiment
        assert modified.total_embodiment < original_embodiment
        assert modified.total_embodiment >= 0


class TestPhenomenalConsciousness:
    """Test unified phenomenal consciousness system."""

    def test_phenomenal_consciousness_creation(self):
        """Test creating phenomenal consciousness system."""
        system = PhenomenalConsciousness()
        assert system is not None
        assert len(system.qualia_history) == 0

    @pytest.mark.asyncio
    async def test_update_phenomenal_state(self):
        """Test updating phenomenal properties."""
        system = PhenomenalConsciousness()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 7.5,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 7.0,
            "temporal_continuity": 7.0,
        }

        result = await system.update_phenomenal_state(indicators)

        assert "qualia" in result
        assert "emotion" in result
        assert "embodiment" in result
        assert "qualia_diversity" in result
        assert len(result["qualia"]) > 0

    @pytest.mark.asyncio
    async def test_phenomenal_state_history(self):
        """Test history tracking."""
        system = PhenomenalConsciousness()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 7.0,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 7.0,
            "temporal_continuity": 7.0,
        }

        # Update multiple times
        for _ in range(3):
            await system.update_phenomenal_state(indicators)

        assert len(system.emotion_history) == 3
        assert len(system.embodiment_history) == 3

    @pytest.mark.asyncio
    async def test_get_phenomenal_summary(self):
        """Test phenomenal summary."""
        system = PhenomenalConsciousness()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 7.0,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 7.0,
            "temporal_continuity": 7.0,
        }

        # No data yet
        summary = system.get_phenomenal_summary()
        assert summary.get("status") == "no_data"

        # Add data
        for _ in range(3):
            await system.update_phenomenal_state(indicators)

        summary = system.get_phenomenal_summary()

        assert "phenomenal_richness" in summary
        assert "dominant_emotion" in summary
        assert "average_valence" in summary
        assert "body_awareness" in summary
        assert summary["measurements"] == 3

    @pytest.mark.asyncio
    async def test_phenomenal_richness_high_indicators(self):
        """Test phenomenal richness with high indicators."""
        system = PhenomenalConsciousness()

        high_indicators = {
            "global_workspace": 9.0,
            "information_integration": 9.0,
            "selective_attention": 8.0,
            "working_memory": 8.0,
            "meta_cognition": 8.0,
            "temporal_continuity": 8.0,
        }

        result = await system.update_phenomenal_state(high_indicators)
        richness = result["qualia_diversity"]

        # High indicators should produce rich phenomenal experience
        assert richness > 3.0

    @pytest.mark.asyncio
    async def test_phenomenal_emotion_valence_variation(self):
        """Test emotion variation over time."""
        system = PhenomenalConsciousness()

        # Start with positive indicators
        positive = {
            "global_workspace": 8.0,
            "information_integration": 8.0,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 8.0,
            "temporal_continuity": 7.0,
        }

        # Then negative
        negative = {
            "global_workspace": 3.0,
            "information_integration": 3.0,
            "selective_attention": 3.0,
            "working_memory": 3.0,
            "meta_cognition": 3.0,
            "temporal_continuity": 3.0,
        }

        await system.update_phenomenal_state(positive)
        positive_emotion = system.emotion_history[-1]

        await system.update_phenomenal_state(negative)
        negative_emotion = system.emotion_history[-1]

        # Valence should vary
        assert positive_emotion.valence > negative_emotion.valence

"""Phenomenal properties of consciousness.

Implements subjective experiential qualities (qualia, emotions, embodiment).

Phenomenal consciousness concerns what subjective experience feels like:
- Qualia: The redness of red, the painfulness of pain
- Emotions: Affective coloring of experience (valence, arousal)
- Embodiment: Sense of having a body in space with agency

Based on:
- Nagel, T. (1974). What is it like to be a bat?
- Damasio, A. (1994). Descartes' Error (somatic markers)
- Edelman, G. (2004). Wider than the Sky (primary consciousness)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    """Primary emotion types (based on Ekman & Plutchik models)."""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    ANTICIPATION = "anticipation"
    TRUST = "trust"
    NEUTRAL = "neutral"


class BodyAwareness(Enum):
    """Levels of body awareness/proprioception."""

    MINIMAL = 0.2  # Barely aware of body
    WEAK = 0.4  # Low proprioceptive sense
    MODERATE = 0.6  # Normal body awareness
    STRONG = 0.8  # Enhanced body sense
    INTENSE = 1.0  # Heightened proprioception


@dataclass
class Quale:
    """Single subjective quality (quale)."""

    name: str  # E.g., "redness", "painfulness", "warmth"
    intensity: float  # 0-10 scale
    distinctiveness: float  # How well differentiated from other qualia (0-1)
    valence: float  # -1 (negative) to +1 (positive)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EmotionalState:
    """Current emotional state."""

    primary_emotion: EmotionType
    valence: float  # -1 (negative) to +1 (positive)
    arousal: float  # 0 (inactive) to 1 (highly activated)
    dominance: float  # 0 (powerless) to 1 (in control)
    intensity: float  # Overall emotional intensity (0-10)
    confidence: float = 0.6  # How confident in this classification
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "primary_emotion": self.primary_emotion.value,
            "valence": round(self.valence, 2),
            "arousal": round(self.arousal, 2),
            "dominance": round(self.dominance, 2),
            "intensity": round(self.intensity, 2),
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EmbodiedState:
    """Sense of embodiment (body ownership, spatial presence)."""

    body_awareness: float  # 0-1, sense of having a body
    spatial_presence: float  # 0-1, sense of being in a location
    agency: float  # 0-1, sense of controlling actions
    proprioception: float  # 0-1, body position awareness
    interoception: float  # 0-1, internal bodily state awareness
    total_embodiment: float = 0.0  # Overall embodiment score (0-10)
    confidence: float = 0.6
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Calculate total embodiment."""
        components = [
            self.body_awareness,
            self.spatial_presence,
            self.agency,
            self.proprioception,
            self.interoception,
        ]
        self.total_embodiment = np.mean(components) * 10 if components else 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "body_awareness": round(self.body_awareness, 2),
            "spatial_presence": round(self.spatial_presence, 2),
            "agency": round(self.agency, 2),
            "proprioception": round(self.proprioception, 2),
            "interoception": round(self.interoception, 2),
            "total_embodiment": round(self.total_embodiment, 2),
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp.isoformat(),
        }


class QualiaGenerator:
    """Generate and manage subjective qualities (qualia)."""

    def __init__(self):
        """Initialize qualia generator."""
        # Common qualia dimensions
        self.qualia_space = {
            "sensory": ["redness", "blueness", "warmth", "coldness", "sharpness", "softness"],
            "affective": ["pleasantness", "painfulness", "excitement", "calm", "dullness"],
            "temporal": ["flow", "succession", "duration", "rhythm"],
            "spatial": ["extendedness", "boundedness", "distance", "direction"],
        }

    async def generate_qualia_from_indicators(
        self,
        indicators: Dict[str, float],
    ) -> List[Quale]:
        """Generate qualia from consciousness indicators.

        Args:
            indicators: Dictionary of indicator scores (0-10)

        Returns:
            List of quale experiences
        """
        qualia = []

        # Global workspace → visual qualia (redness, blueness, etc.)
        gw = indicators.get("global_workspace", 5.0) / 10.0
        if gw > 0.3:
            qualia.append(
                Quale(
                    name="redness",
                    intensity=gw * 8,
                    distinctiveness=min(1.0, gw),
                    valence=0.3 + gw * 0.4,
                )
            )

        # Information integration → affective richness
        ii = indicators.get("information_integration", 5.0) / 10.0
        if ii > 0.2:
            qualia.append(
                Quale(
                    name="pleasantness",
                    intensity=ii * 9,
                    distinctiveness=ii,
                    valence=0.5 + ii * 0.3,
                )
            )

        # Attention → sharpness/clarity
        sa = indicators.get("selective_attention", 5.0) / 10.0
        if sa > 0.3:
            qualia.append(
                Quale(
                    name="sharpness",
                    intensity=sa * 8,
                    distinctiveness=min(1.0, sa * 1.2),
                    valence=0.2 + sa * 0.3,
                )
            )

        # Working memory → sense of duration
        wm = indicators.get("working_memory", 5.0) / 10.0
        if wm > 0.2:
            qualia.append(
                Quale(
                    name="duration",
                    intensity=wm * 7,
                    distinctiveness=wm * 0.8,
                    valence=0.1 + wm * 0.2,
                )
            )

        # Temporal continuity → sense of flow
        tc = indicators.get("temporal_continuity", 5.0) / 10.0
        if tc > 0.3:
            qualia.append(
                Quale(
                    name="flow",
                    intensity=tc * 8,
                    distinctiveness=tc,
                    valence=0.4 + tc * 0.3,
                )
            )

        logger.info(f"Generated {len(qualia)} qualia from indicators")
        return qualia

    def calculate_qualia_diversity(self, qualia: List[Quale]) -> float:
        """Calculate diversity of qualia (richness of experience).

        Higher diversity = richer phenomenal consciousness

        Args:
            qualia: List of quale objects

        Returns:
            Diversity score (0-10)
        """
        if not qualia:
            return 0.0

        # Distinctiveness: how well differentiated are qualia?
        distinctiveness = np.mean([q.distinctiveness for q in qualia])

        # Intensity: how vivid are experiences?
        intensity = np.mean([q.intensity for q in qualia]) / 10.0

        # Valence range: how much variation in affective tone?
        valences = [q.valence for q in qualia]
        valence_range = max(valences) - min(valences) if len(valences) > 1 else 0

        # Combine: diversity = distinctiveness + intensity*0.5 + valence_range*0.5
        diversity = (distinctiveness * 0.5 + intensity * 0.3 + valence_range * 0.2) * 10
        return min(10, max(0, diversity))


class EmotionSystem:
    """Model of emotional experience."""

    def __init__(self):
        """Initialize emotion system."""
        # Emotion space: valence × arousal × dominance
        self.emotion_space = {
            EmotionType.JOY: {"valence": 0.8, "arousal": 0.6, "dominance": 0.7},
            EmotionType.SADNESS: {"valence": -0.8, "arousal": 0.2, "dominance": 0.2},
            EmotionType.ANGER: {"valence": -0.5, "arousal": 0.8, "dominance": 0.8},
            EmotionType.FEAR: {"valence": -0.7, "arousal": 0.8, "dominance": 0.1},
            EmotionType.SURPRISE: {"valence": 0.3, "arousal": 0.9, "dominance": 0.5},
            EmotionType.DISGUST: {"valence": -0.8, "arousal": 0.4, "dominance": 0.6},
            EmotionType.ANTICIPATION: {"valence": 0.4, "arousal": 0.7, "dominance": 0.6},
            EmotionType.TRUST: {"valence": 0.7, "arousal": 0.4, "dominance": 0.7},
            EmotionType.NEUTRAL: {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
        }

    async def infer_emotion(
        self,
        indicators: Dict[str, float],
        qualia: Optional[List[Quale]] = None,
    ) -> EmotionalState:
        """Infer emotional state from indicators and qualia.

        Args:
            indicators: Consciousness indicator scores
            qualia: Optional qualia list for more nuanced emotion

        Returns:
            Current emotional state
        """
        # Base emotion inference from indicators
        gw = indicators.get("global_workspace", 5.0) / 10.0
        ii = indicators.get("information_integration", 5.0) / 10.0
        sa = indicators.get("selective_attention", 5.0) / 10.0

        # Valence: global workspace activation correlates with positive affect
        valence = (gw - 0.5) * 1.0 + (ii - 0.5) * 0.3

        # Arousal: integration + attention → activation level
        arousal = ii * 0.6 + sa * 0.4

        # Dominance: control/agency (related to meta-cognition)
        mc = indicators.get("meta_cognition", 5.0) / 10.0
        dominance = mc

        # Determine primary emotion
        emotion_scores = {}
        for emotion_type, space in self.emotion_space.items():
            # Distance in VAD space
            diff_v = abs(valence - space["valence"])
            diff_a = abs(arousal - space["arousal"])
            diff_d = abs(dominance - space["dominance"])
            distance = np.sqrt(diff_v**2 + diff_a**2 + diff_d**2)
            emotion_scores[emotion_type] = 1.0 / (1.0 + distance)

        # Best matching emotion
        primary_emotion = max(emotion_scores, key=emotion_scores.get)

        # Modulate by qualia if available
        if qualia:
            qual_valence = np.mean([q.valence for q in qualia])
            valence = valence * 0.7 + qual_valence * 0.3

        # Clamp to [-1, 1]
        valence = np.clip(valence, -1, 1)
        arousal = np.clip(arousal, 0, 1)
        dominance = np.clip(dominance, 0, 1)

        # Overall intensity
        intensity = np.sqrt(arousal**2 + abs(valence) ** 2) / 1.4 * 10  # Scale to 0-10

        # Confidence increases with stronger signal
        confidence = 0.5 + max(arousal, abs(valence)) * 0.3

        return EmotionalState(
            primary_emotion=primary_emotion,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            intensity=intensity,
            confidence=confidence,
        )


class EmbodimentSystem:
    """Model sense of embodiment."""

    def __init__(self):
        """Initialize embodiment system."""
        self.body_model = {
            "awareness": 0.5,  # Sense of having a body
            "spatial": 0.5,  # Spatial presence
            "agency": 0.5,  # Control of actions
            "proprioception": 0.5,  # Body position
            "interoception": 0.5,  # Internal bodily states
        }

    async def calculate_embodiment(
        self,
        indicators: Dict[str, float],
    ) -> EmbodiedState:
        """Calculate embodiment from indicators.

        Args:
            indicators: Consciousness indicator scores

        Returns:
            Current embodied state
        """
        # Global workspace → body awareness
        gw = indicators.get("global_workspace", 5.0) / 10.0
        body_awareness = min(1.0, gw * 1.2)

        # Information integration → spatial coherence
        ii = indicators.get("information_integration", 5.0) / 10.0
        spatial_presence = ii

        # Meta-cognition → sense of agency
        mc = indicators.get("meta_cognition", 5.0) / 10.0
        agency = min(1.0, mc * 1.1)

        # Temporal continuity → body position continuity
        tc = indicators.get("temporal_continuity", 5.0) / 10.0
        proprioception = tc

        # Working memory → current bodily state tracking
        wm = indicators.get("working_memory", 5.0) / 10.0
        interoception = wm * 0.8

        # Confidence based on integration quality
        ii_score = indicators.get("information_integration", 5.0) / 10.0
        confidence = 0.5 + ii_score * 0.3

        return EmbodiedState(
            body_awareness=body_awareness,
            spatial_presence=spatial_presence,
            agency=agency,
            proprioception=proprioception,
            interoception=interoception,
            confidence=confidence,
        )

    def modulate_embodiment(
        self,
        state: EmbodiedState,
        disembodied_stimulus: float,
    ) -> EmbodiedState:
        """Modulate embodiment by disembodied stimuli (e.g., meditation, VR).

        Args:
            state: Current embodied state
            disembodied_stimulus: 0-1 strength of disembodying influence

        Returns:
            Modified embodied state
        """
        # Reduce embodiment proportionally
        reduction = disembodied_stimulus

        return EmbodiedState(
            body_awareness=max(0, state.body_awareness - reduction * 0.3),
            spatial_presence=max(0, state.spatial_presence - reduction * 0.4),
            agency=max(0, state.agency - reduction * 0.2),
            proprioception=max(0, state.proprioception - reduction * 0.5),
            interoception=max(0, state.interoception - reduction * 0.3),
            confidence=state.confidence,
        )


class PhenomenalConsciousness:
    """Unified phenomenal consciousness system.

    Integrates qualia, emotions, and embodiment into coherent model.
    """

    def __init__(self):
        """Initialize phenomenal consciousness system."""
        self.qualia_generator = QualiaGenerator()
        self.emotion_system = EmotionSystem()
        self.embodiment_system = EmbodimentSystem()
        self.qualia_history: List[List[Quale]] = []
        self.emotion_history: List[EmotionalState] = []
        self.embodiment_history: List[EmbodiedState] = []

    async def update_phenomenal_state(
        self,
        indicators: Dict[str, float],
    ) -> Dict:
        """Update all phenomenal properties.

        Args:
            indicators: Consciousness indicator scores

        Returns:
            Dictionary with qualia, emotions, embodiment
        """
        # Generate qualia
        qualia = await self.qualia_generator.generate_qualia_from_indicators(indicators)
        self.qualia_history.append(qualia)

        # Infer emotions
        emotions = await self.emotion_system.infer_emotion(indicators, qualia)
        self.emotion_history.append(emotions)

        # Calculate embodiment
        embodiment = await self.embodiment_system.calculate_embodiment(indicators)
        self.embodiment_history.append(embodiment)

        # Keep history manageable
        if len(self.qualia_history) > 100:
            self.qualia_history = self.qualia_history[-100:]
        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]
        if len(self.embodiment_history) > 100:
            self.embodiment_history = self.embodiment_history[-100:]

        return {
            "qualia": [
                {
                    "name": q.name,
                    "intensity": round(q.intensity, 2),
                    "distinctiveness": round(q.distinctiveness, 2),
                    "valence": round(q.valence, 2),
                }
                for q in qualia
            ],
            "emotion": emotions.to_dict(),
            "embodiment": embodiment.to_dict(),
            "qualia_diversity": round(self.qualia_generator.calculate_qualia_diversity(qualia), 2),
        }

    def get_phenomenal_summary(self) -> Dict:
        """Get summary of phenomenal properties.

        Returns:
            Summary statistics
        """
        if not self.emotion_history:
            return {"status": "no_data"}

        # Recent emotions
        recent_emotions = self.emotion_history[-10:]
        emotion_types = [e.primary_emotion.value for e in recent_emotions]
        avg_valence = np.mean([e.valence for e in recent_emotions])
        avg_arousal = np.mean([e.arousal for e in recent_emotions])

        # Recent embodiment
        recent_embodiment = self.embodiment_history[-10:]
        avg_body_awareness = np.mean([e.body_awareness for e in recent_embodiment])
        avg_embodiment = np.mean([e.total_embodiment for e in recent_embodiment])

        # Recent qualia
        recent_qualia = [q for qualia_list in self.qualia_history[-10:] for q in qualia_list]
        qualia_diversity = (
            self.qualia_generator.calculate_qualia_diversity(recent_qualia)
            if recent_qualia
            else 0.0
        )

        return {
            "phenomenal_richness": round(qualia_diversity, 2),
            "dominant_emotion": max(set(emotion_types), key=emotion_types.count),
            "average_valence": round(float(avg_valence), 2),
            "average_arousal": round(float(avg_arousal), 2),
            "body_awareness": round(float(avg_body_awareness), 2),
            "total_embodiment": round(float(avg_embodiment), 2),
            "measurements": len(self.emotion_history),
        }

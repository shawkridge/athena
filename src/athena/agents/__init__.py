"""
Tier 2: Autonomous Agent Intelligence System

This module provides 5 specialized agents that collaborate to:
- Plan tasks intelligently (Planner)
- Execute plans with error handling (Executor)
- Monitor execution health (Monitor)
- Predict future needs (Predictor)
- Learn from outcomes (Learner)
"""

from .base import BaseAgent, AgentType, AgentStatus, AgentMetrics
from .message_bus import Message, MessageBus, MessageType
from .orchestrator import AgentOrchestrator
from .planner import PlannerAgent, ExecutionPlan, PlanStep
from .executor import ExecutorAgent, ExecutionRecord, ExecutionResult
from .monitor import MonitorAgent, Anomaly, ExecutionMetric
from .learner import LearnerAgent, ExecutionPattern, Improvement, LearningOutcome
from .predictor import PredictorAgent
from .predictor_models import (
    PredictionResult,
    ConfidenceInterval,
    TemporalPattern,
    DurationPrediction,
    ResourceForecast,
    BottleneckAlert,
    PredictionAccuracy,
    RiskLevel,
    PatternType,
    ResourceType,
)
from .temporal_reasoner import TemporalReasoner
from .bottleneck_detector import BottleneckDetector
from .timeseries import ARIMAModel, ExponentialSmoothingModel, HybridEnsembleModel

__all__ = [
    # Base and Communication
    "BaseAgent",
    "AgentType",
    "AgentStatus",
    "AgentMetrics",
    "Message",
    "MessageBus",
    "MessageType",
    "AgentOrchestrator",
    # Planner Agent
    "PlannerAgent",
    "ExecutionPlan",
    "PlanStep",
    # Executor Agent
    "ExecutorAgent",
    "ExecutionRecord",
    "ExecutionResult",
    # Monitor Agent
    "MonitorAgent",
    "Anomaly",
    "ExecutionMetric",
    # Learner Agent
    "LearnerAgent",
    "ExecutionPattern",
    "Improvement",
    "LearningOutcome",
    # Predictor Agent (NEW)
    "PredictorAgent",
    "PredictionResult",
    "ConfidenceInterval",
    "TemporalPattern",
    "DurationPrediction",
    "ResourceForecast",
    "BottleneckAlert",
    "PredictionAccuracy",
    "RiskLevel",
    "PatternType",
    "ResourceType",
    # Time Series Models (NEW)
    "ARIMAModel",
    "ExponentialSmoothingModel",
    "HybridEnsembleModel",
    # Temporal Reasoning (NEW)
    "TemporalReasoner",
    # Bottleneck Detection (NEW)
    "BottleneckDetector",
]

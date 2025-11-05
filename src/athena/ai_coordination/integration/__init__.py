"""Integration module: Phase 7 (AI Coordination ↔ Memory-MCP)

Bridges AI Coordination system (Phases 1-6) with Memory-MCP (8 layers).

Phase 7 sub-phases:
- Phase 7.1: Event Forwarding - Convert coordination events to episodic events
- Phase 7.2: Spatial-Temporal Grounding - Link to file hierarchy and time sequences
- Phase 7.3: Consolidation Triggers - Extract patterns and create procedures
- Phase 7.4: Recall & Reuse - Use learned knowledge in planning

Current Status: Phase 7.4 (Recall & Reuse) in development
"""

# Phase 7.1: Event Forwarding
from athena.ai_coordination.integration.event_forwarder import (
    EventForwarder,
    ForwardingLogEntry,
    ForwardingStatus,
)
from athena.ai_coordination.integration.event_forwarder_store import (
    EventForwarderStore,
)

# Phase 7.2: Spatial-Temporal Grounding
from athena.ai_coordination.integration.spatial_grounding import SpatialGrounder
from athena.ai_coordination.integration.temporal_chaining import TemporalChainer
from athena.ai_coordination.integration.graph_linking import (
    GraphLinker,
    EntityType,
    RelationType,
)
from athena.ai_coordination.integration.phase7_2_mcp_tools import Phase72MCPTools

# Phase 7.3: Consolidation Triggers
from athena.ai_coordination.integration.consolidation_trigger import (
    ConsolidationTrigger,
    ConsolidationTriggerType,
    ConsolidationStatus,
)
from athena.ai_coordination.integration.learning_pathway import LearningPathway
from athena.ai_coordination.integration.procedure_auto_creator import (
    ProcedureAutoCreator,
    ProcedureCandidate,
)
from athena.ai_coordination.integration.phase7_3_mcp_tools import Phase73MCPTools

# Phase 7.4: Recall & Reuse
from athena.ai_coordination.integration.smart_recall import SmartRecall, RecallContext
from athena.ai_coordination.integration.action_cycle_enhancer import (
    ActionCycleEnhancer,
    PlanEnhancement,
)
from athena.ai_coordination.integration.prospective_integration import (
    ProspectiveIntegration,
    ProspectiveTask,
)
from athena.ai_coordination.integration.phase7_4_mcp_tools import Phase74MCPTools

__all__ = [
    # Phase 7.1
    "EventForwarder",
    "ForwardingLogEntry",
    "ForwardingStatus",
    "EventForwarderStore",
    # Phase 7.2
    "SpatialGrounder",
    "TemporalChainer",
    "GraphLinker",
    "EntityType",
    "RelationType",
    "Phase72MCPTools",
    # Phase 7.3
    "ConsolidationTrigger",
    "ConsolidationTriggerType",
    "ConsolidationStatus",
    "LearningPathway",
    "ProcedureAutoCreator",
    "ProcedureCandidate",
    "Phase73MCPTools",
    # Phase 7.4
    "SmartRecall",
    "RecallContext",
    "ActionCycleEnhancer",
    "PlanEnhancement",
    "ProspectiveIntegration",
    "ProspectiveTask",
    "Phase74MCPTools",
]

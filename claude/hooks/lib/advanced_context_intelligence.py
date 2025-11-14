"""Phase 4: Advanced Context Intelligence.

Implements:
1. Proactive entity detection (pre-load related context)
2. Progressive disclosure (drill-down via /recall)
3. Cross-session continuity (smart resumption)
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Detected entity in user prompt."""

    entity_text: str
    entity_type: str  # function, table, class, file, concept, etc.
    confidence: float  # 0.0-1.0
    context_before: str
    context_after: str
    position: int

    @property
    def id(self) -> str:
        """Generate unique ID for entity."""
        return hashlib.md5(
            f"{self.entity_type}_{self.entity_text}".encode()
        ).hexdigest()[:8]


class EntityDetector:
    """Proactively detect entities in user prompts for context pre-loading."""

    # Entity patterns for different languages/frameworks
    ENTITY_PATTERNS = {
        "function": {
            "python": r"\b([a-z_][a-z0-9_]*)\s*\(",
            "javascript": r"\b([a-z_$][a-z0-9_$]*)\s*\(",
            "general": r"\b([a-z_][a-z0-9_]*)\s*\(",
        },
        "class": {
            "python": r"\bclass\s+([A-Z][a-zA-Z0-9_]*)",
            "javascript": r"\bclass\s+([A-Z][a-zA-Z0-9_]*)",
            "general": r"\bclass\s+([A-Z][a-zA-Z0-9_]*)",
        },
        "table": {
            "sql": r"\b(users|posts|comments|auth|tokens|sessions)\b",
            "database": r"\b(users|posts|comments|auth|tokens|sessions)\b",
        },
        "file": {
            "general": r"([a-zA-Z0-9_\-]+\.(?:py|js|ts|jsx|tsx|go|rs|java|cpp))",
        },
        "concept": {
            "general": r"\b(JWT|OAuth|REST|GraphQL|middleware|schema|migration|index)\b",
        },
    }

    def __init__(self):
        """Initialize entity detector."""
        self.detected_entities: List[Entity] = []

    def detect_entities(self, prompt: str) -> List[Entity]:
        """Detect entities in user prompt.

        Args:
            prompt: User's question or request

        Returns:
            List of detected entities (sorted by position)
        """
        self.detected_entities = []
        prompt_lower = prompt.lower()

        # Check each entity type
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern_name, pattern in patterns.items():
                matches = list(re.finditer(pattern, prompt_lower, re.IGNORECASE))

                for match in matches:
                    entity_text = match.group(1) if match.groups() else match.group(0)
                    position = match.start()

                    # Get context (20 chars before/after)
                    start = max(0, position - 20)
                    end = min(len(prompt), position + len(entity_text) + 20)
                    context_before = prompt[start:position].strip()
                    context_after = prompt[position + len(entity_text):end].strip()

                    entity = Entity(
                        entity_text=entity_text,
                        entity_type=entity_type,
                        confidence=0.85,  # Pattern-based detection is fairly confident
                        context_before=context_before,
                        context_after=context_after,
                        position=position,
                    )

                    # Avoid duplicates
                    if not any(
                        e.entity_text == entity_text and e.entity_type == entity_type
                        for e in self.detected_entities
                    ):
                        self.detected_entities.append(entity)

        # Sort by position (left to right in prompt)
        self.detected_entities.sort(key=lambda e: e.position)

        logger.debug(f"Detected {len(self.detected_entities)} entities")
        return self.detected_entities

    def get_high_confidence_entities(
        self, min_confidence: float = 0.80
    ) -> List[Entity]:
        """Get entities above confidence threshold.

        Args:
            min_confidence: Minimum confidence (0.0-1.0)

        Returns:
            Filtered entities
        """
        return [e for e in self.detected_entities if e.confidence >= min_confidence]

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get entities of specific type.

        Args:
            entity_type: Type filter (function, class, table, etc.)

        Returns:
            Entities matching type
        """
        return [e for e in self.detected_entities if e.entity_type == entity_type]


class ProactiveContextLoader:
    """Pre-load context for detected entities before user needs it."""

    # Strategies for different entity types
    ENTITY_STRATEGIES = {
        "function": {
            "description": "Load function implementation, signature, tests",
            "search_queries": ["definition", "implementation", "usage", "tests"],
            "graph_traversal": ["calls", "called_by", "similar_functions"],
        },
        "class": {
            "description": "Load class definition, methods, inheritance",
            "search_queries": ["definition", "methods", "inheritance", "tests"],
            "graph_traversal": ["extends", "implements", "uses", "used_by"],
        },
        "table": {
            "description": "Load schema, indexes, relations",
            "search_queries": ["schema", "columns", "indexes", "migration"],
            "graph_traversal": ["foreign_keys", "referenced_by", "indexes"],
        },
        "file": {
            "description": "Load file structure, imports, dependencies",
            "search_queries": ["imports", "exports", "structure", "dependencies"],
            "graph_traversal": ["imports", "imported_by", "related_files"],
        },
        "concept": {
            "description": "Load patterns, best practices, examples",
            "search_queries": ["definition", "best_practices", "examples", "patterns"],
            "graph_traversal": ["related_concepts", "implementations", "antipatterns"],
        },
    }

    def __init__(self):
        """Initialize proactive loader."""
        self.loading_plan: Dict[str, Dict] = {}

    def plan_context_loading(self, entities: List[Entity]) -> Dict[str, Dict]:
        """Plan what context to pre-load for entities.

        Args:
            entities: Detected entities

        Returns:
            Loading plan: {entity_id: {type, queries, graph_traversals}}
        """
        self.loading_plan = {}

        for entity in entities[:5]:  # Top 5 entities only
            strategy = self.ENTITY_STRATEGIES.get(
                entity.entity_type, self.ENTITY_STRATEGIES["concept"]
            )

            self.loading_plan[entity.id] = {
                "entity": asdict(entity),
                "strategy": entity.entity_type,
                "description": strategy["description"],
                "search_queries": [
                    f"{entity.entity_text} {q}" for q in strategy["search_queries"]
                ],
                "graph_traversals": strategy["graph_traversal"],
                "priority": len(entities) - entities.index(entity),  # First entity = highest
            }

        logger.debug(f"Planned loading for {len(self.loading_plan)} entities")
        return self.loading_plan

    def format_loading_plan(self, max_tokens: int = 200) -> str:
        """Format loading plan for injection (user-visible hint).

        Args:
            max_tokens: Maximum tokens to use

        Returns:
            Formatted hint text
        """
        if not self.loading_plan:
            return ""

        lines = ["## Pre-loaded Context"]
        char_count = 0
        max_chars = max_tokens * 4  # Rough token estimation

        for entity_id, plan in sorted(
            self.loading_plan.items(), key=lambda x: x[1]["priority"], reverse=True
        ):
            entity_text = plan["entity"]["entity_text"]
            entity_type = plan["entity"]["entity_type"]

            line = f"- Loading {entity_type}: **{entity_text}**\n"
            char_count += len(line)

            if char_count > max_chars:
                break

            lines.append(line)

        return "".join(lines) if len(lines) > 1 else ""


class ProgressiveDisclosureManager:
    """Enable progressive disclosure: start with summaries, drill down on request."""

    # Format for memory references that can be drilled down
    MEMORY_REFERENCE_FORMAT = "[{type}] {title} (ID: {id})"

    def __init__(self):
        """Initialize progressive disclosure manager."""
        self.referenced_memories: Dict[str, Dict] = {}
        self.drill_down_history: List[str] = []

    def create_memory_reference(
        self, memory_id: str, title: str, memory_type: str, full_content: str
    ) -> str:
        """Create reference to memory that can be drilled down.

        Args:
            memory_id: Unique memory ID
            title: Memory title (shown in reference)
            memory_type: Type of memory (implementation, procedure, etc.)
            full_content: Full content (stored for drill-down)

        Returns:
            Formatted reference string
        """
        # Store full content for later drill-down
        self.referenced_memories[memory_id] = {
            "title": title,
            "type": memory_type,
            "content": full_content,
            "created_at": datetime.utcnow().isoformat(),
            "accessed_count": 0,
            "drill_down_requested": False,
        }

        return self.MEMORY_REFERENCE_FORMAT.format(
            type=memory_type, title=title[:60], id=memory_id
        )

    def recall_memory(self, memory_id: str) -> Optional[Dict]:
        """Drill down to full memory content.

        Args:
            memory_id: Memory ID to recall

        Returns:
            Full memory data, or None if not found
        """
        if memory_id not in self.referenced_memories:
            logger.warning(f"Memory {memory_id} not found in drill-down cache")
            return None

        mem = self.referenced_memories[memory_id]
        mem["accessed_count"] += 1
        mem["drill_down_requested"] = True
        mem["last_accessed"] = datetime.utcnow().isoformat()
        self.drill_down_history.append(memory_id)

        return mem

    def get_drill_down_stats(self) -> Dict:
        """Get statistics about drill-down usage.

        Returns:
            Stats dictionary
        """
        total_refs = len(self.referenced_memories)
        accessed = sum(
            1 for m in self.referenced_memories.values() if m["accessed_count"] > 0
        )
        total_accesses = sum(
            m["accessed_count"] for m in self.referenced_memories.values()
        )

        return {
            "total_references": total_refs,
            "accessed_memories": accessed,
            "total_drill_downs": total_accesses,
            "drill_down_ratio": accessed / total_refs if total_refs > 0 else 0,
            "history_length": len(self.drill_down_history),
        }


class CrossSessionContinuity:
    """Track and resume work across sessions with smart summaries."""

    def __init__(self, session_id: str, project_id: Optional[str] = None):
        """Initialize cross-session manager.

        Args:
            session_id: Current session ID
            project_id: Project ID for scope
        """
        self.session_id = session_id
        self.project_id = project_id
        self.previous_session_summary: Optional[Dict] = None
        self.time_gap: Optional[timedelta] = None

    def analyze_session_gap(
        self, current_time: datetime, last_session_time: Optional[datetime]
    ) -> Dict:
        """Analyze time gap since last session.

        Args:
            current_time: Current session start time
            last_session_time: Previous session end time

        Returns:
            Gap analysis dictionary
        """
        if not last_session_time:
            return {"gap_type": "first_session", "gap_duration": None}

        gap = current_time - last_session_time
        self.time_gap = gap

        # Categorize gap
        if gap < timedelta(minutes=30):
            gap_type = "brief_interruption"
        elif gap < timedelta(hours=1):
            gap_type = "short_break"
        elif gap < timedelta(hours=4):
            gap_type = "work_session_break"
        elif gap < timedelta(hours=24):
            gap_type = "same_day_return"
        elif gap < timedelta(days=7):
            gap_type = "few_days_away"
        else:
            gap_type = "long_break"

        return {
            "gap_type": gap_type,
            "gap_duration": gap,
            "hours_since": gap.total_seconds() / 3600,
            "days_since": gap.days,
            "human_readable": self._humanize_gap(gap),
        }

    @staticmethod
    def _humanize_gap(gap: timedelta) -> str:
        """Convert timedelta to human-readable string.

        Args:
            gap: Time gap

        Returns:
            Human-readable string (e.g., "2 days, 3 hours ago")
        """
        total_seconds = int(gap.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds} seconds ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = total_seconds // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"

    def create_session_summary(
        self,
        completed_tasks: List[str],
        discovered_insights: List[str],
        next_steps: List[str],
        accomplishments: str = "",
    ) -> Dict:
        """Create summary of completed session for next session reference.

        Args:
            completed_tasks: What was finished
            discovered_insights: Key learnings
            next_steps: What to do next
            accomplishments: Overall summary

        Returns:
            Session summary dictionary
        """
        summary = {
            "session_id": self.session_id,
            "created_at": datetime.utcnow().isoformat(),
            "completed_tasks": completed_tasks,
            "discovered_insights": discovered_insights,
            "next_steps": next_steps,
            "accomplishments": accomplishments,
            "impact": len(completed_tasks) + len(discovered_insights),
        }

        self.previous_session_summary = summary
        return summary

    def format_session_resume(self, gap_analysis: Dict) -> str:
        """Format context for resuming work after gap.

        Args:
            gap_analysis: Gap analysis from analyze_session_gap()

        Returns:
            Formatted resume context
        """
        if not self.previous_session_summary:
            return ""

        summary = self.previous_session_summary
        gap_type = gap_analysis.get("gap_type")
        human_gap = gap_analysis.get("human_readable", "some time")

        lines = [f"## Session Resume ({human_gap})"]

        # Add context based on gap type
        if gap_type == "brief_interruption":
            lines.append("You were just working on:")
        elif gap_type == "short_break":
            lines.append("You took a quick break from:")
        elif gap_type in ["work_session_break", "same_day_return"]:
            lines.append("Earlier today you were working on:")
        elif gap_type == "few_days_away":
            lines.append(f"You were working on this {gap_analysis.get('days_since')} days ago:")
        else:
            lines.append("In your last session you were working on:")

        # Add accomplishments summary
        if summary.get("accomplishments"):
            lines.append(f"\n**Last session**: {summary['accomplishments']}")

        # Add completed tasks
        if summary.get("completed_tasks"):
            lines.append("\n**Completed**:")
            for task in summary["completed_tasks"][:3]:  # Top 3
                lines.append(f"- {task}")

        # Add insights
        if summary.get("discovered_insights"):
            lines.append("\n**Key insights**:")
            for insight in summary["discovered_insights"][:2]:  # Top 2
                lines.append(f"- {insight}")

        # Add next steps (main resumption point)
        if summary.get("next_steps"):
            lines.append("\n**Next steps**:")
            for step in summary["next_steps"][:2]:  # Top 2
                lines.append(f"1. {step}")

        return "\n".join(lines)


class AdvancedContextIntelligence:
    """High-level interface for Phase 4 advanced features."""

    def __init__(self, session_id: str, project_id: Optional[str] = None):
        """Initialize advanced intelligence system.

        Args:
            session_id: Current session ID
            project_id: Project scope (optional)
        """
        self.session_id = session_id
        self.project_id = project_id
        self.entity_detector = EntityDetector()
        self.proactive_loader = ProactiveContextLoader()
        self.disclosure_manager = ProgressiveDisclosureManager()
        self.continuity_manager = CrossSessionContinuity(session_id, project_id)

    def analyze_prompt_for_intelligence(
        self, prompt: str
    ) -> Dict:
        """Comprehensive analysis of prompt for advanced intelligence.

        Args:
            prompt: User prompt

        Returns:
            Intelligence analysis with entities, proactive plans, etc.
        """
        # Detect entities
        entities = self.entity_detector.detect_entities(prompt)

        # Plan proactive loading
        loading_plan = self.proactive_loader.plan_context_loading(entities)

        return {
            "detected_entities": [asdict(e) for e in entities],
            "entity_count": len(entities),
            "proactive_plan": loading_plan,
            "num_to_preload": len(loading_plan),
        }

    def format_advanced_context(self, prompt: str, max_tokens: int = 400) -> str:
        """Format all advanced context for injection into prompt.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to use

        Returns:
            Formatted context string
        """
        lines = []
        tokens_used = 0
        max_chars = max_tokens * 4

        # Add proactive loading hints
        proactive_text = self.proactive_loader.format_loading_plan(max_tokens=100)
        if proactive_text:
            lines.append(proactive_text)
            tokens_used += len(proactive_text) // 4

        # Add session resume context (if applicable)
        # This would be called from session-start hook
        # For now just return what we have

        return "".join(lines) if lines else ""

    def get_intelligence_stats(self) -> Dict:
        """Get statistics about Phase 4 intelligence features.

        Returns:
            Stats dictionary
        """
        return {
            "session_id": self.session_id,
            "entities_detected": len(self.entity_detector.detected_entities),
            "proactive_plans": len(self.proactive_loader.loading_plan),
            "drill_down_stats": self.disclosure_manager.get_drill_down_stats(),
            "session_summary": bool(self.continuity_manager.previous_session_summary),
        }

"""Metacognition Handlers - Extracted Domain Module

This module contains all metacognition handler methods extracted from handlers.py
as part of Phase 8 of the handler refactoring.

Handler Methods (8 total, ~1180 lines):
- _handle_analyze_coverage: Analyze memory coverage by domain
- _handle_get_expertise: Get expertise levels and domain knowledge
- _handle_get_learning_rates: Get learning rate metrics
- _handle_detect_knowledge_gaps: Detect knowledge gaps
- _handle_get_self_reflection: Get self-reflection insights
- _handle_check_cognitive_load: Check cognitive load status
- _handle_get_metacognition_insights: Get comprehensive metacognition insights
- _handle_optimize_gap_detector: Optimize gap detection

Dependencies:
- Imports: TextContent, json, logging
- Attributes: self.quality_monitor, self.gap_detector, self.reflection_system, self.load_monitor

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(MetacognitionHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import List

from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata, create_paginated_result, paginate_results
logger = logging.getLogger(__name__)


class MetacognitionHandlersMixin:
    """Mixin class containing all metacognition handler methods.
    
    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all metacognition operations without modifying the main handler structure.
    """

    async def _handle_analyze_coverage(self, args: dict) -> list[TextContent]:
        """Handle analyze_coverage tool call.

        Includes Gap 3 integration: Also checks attention/memory health when analyzing coverage.
        """
        domain = args.get("domain")
        if not domain:
            # If no domain specified, analyze all domains
            all_coverage = self.meta_store.list_domains(limit=5)
            if not all_coverage:
                return [TextContent(type="text", text="No domain coverage data available.")]

            response = "Coverage Analysis: All Domains\n\n"
            for coverage in all_coverage:
                expertise_str = coverage.expertise_level.value if hasattr(coverage.expertise_level, 'value') else str(coverage.expertise_level)
                response += f"**{coverage.domain}**: {expertise_str} ({coverage.memory_count} memories, avg usefulness {coverage.avg_usefulness:.2f})\n"

            return [TextContent(type="text", text=response)]
        project = self.project_manager.get_or_create_project()
        coverage = self.meta_store.get_domain(domain)

        if not coverage:
            return [TextContent(type="text", text=f"No coverage data for domain '{domain}'.")]

        expertise_str = coverage.expertise_level.value if hasattr(coverage.expertise_level, 'value') else str(coverage.expertise_level)
        response = f"Coverage Analysis: {domain}\n\n"
        response += f"Memory Count: {coverage.memory_count}\n"
        response += f"Expertise Level: {expertise_str}\n"
        response += f"Avg Usefulness: {coverage.avg_usefulness:.2f}\n"
        if coverage.last_updated:
            response += f"Last Updated: {coverage.last_updated}"

        # ===== GAP 3 INTEGRATION: CHECK ATTENTION HEALTH =====
        health = self.check_attention_memory_health(project.id)
        if health.get("warnings") or health.get("status") != "healthy":
            response += "\n\n📊 Attention & Memory Health:\n"
            response += f"Status: {health.get('status', 'unknown').upper()}\n"

            if health.get("warnings"):
                response += "\nWarnings:\n"
                for warning in health.get("warnings", []):
                    response += f"  {warning}\n"

            if health.get("recommendations"):
                response += "\nRecommendations:\n"
                for rec in health.get("recommendations", []):
                    response += f"  • {rec}\n"

        return [TextContent(type="text", text=response)]

    async def _handle_get_expertise(self, args: dict) -> list[TextContent]:
        """Handle get_expertise tool call."""
        try:
            limit = min(args.get("limit", 10), 100)
            all_coverage = self.meta_store.list_domains(limit=limit)

            if not all_coverage:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "get_expertise",
                        "schema": "meta",
                    }
                )
            else:
                formatted_domains = []
                for coverage in all_coverage:
                    expertise_str = coverage.expertise_level.value if hasattr(coverage.expertise_level, 'value') else str(coverage.expertise_level)
                    formatted_domains.append({
                        "domain": coverage.domain,
                        "expertise_level": expertise_str,
                        "memory_count": coverage.memory_count,
                        "avg_usefulness": round(coverage.avg_usefulness, 2),
                    })

                result = StructuredResult.success(
                    data=formatted_domains,
                    metadata={
                        "operation": "get_expertise",
                        "schema": "meta",
                        "domain_count": len(formatted_domains),
                    },
                    pagination=PaginationMetadata(
                        returned=len(formatted_domains),
                        limit=limit,
                    )
                )
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "get_expertise"})

        return [result.as_optimized_content(schema_name="meta")]

    # ===== COMMAND DISCOVERABILITY (Gap 5) =====
    def suggest_commands(self, project_id: int, context_type: str = "auto") -> list[dict]:
        """Suggest relevant commands based on current system state.

        Analyzes memory state, cognitive load, and patterns to recommend
        next actions to the user.

        Args:
            project_id: Project ID
            context_type: "auto" (detect) or specific: "focus", "memory", "task", "research"

        Returns:
            List of command suggestions with rationale
        """
        suggestions = []

        try:
            # Get system state
            phono_count = len(self.phonological_loop.get_items(project_id))
            spatial_count = len(self.visuospatial_sketchpad.get_items(project_id))
            buffer_count = len(self.episodic_buffer.get_items(project_id))
            total_wm = phono_count + spatial_count + buffer_count

            # Get recent tasks
            recent_tasks = self.prospective_store.find_recent_completed_tasks(
                project_id=project_id,
                limit=10,
                hours_back=24
            )

            # Get recent episodic events
            cursor = self.store.db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM episodic_events
                WHERE project_id = ? AND timestamp > ?
            """, (project_id, datetime.now() - timedelta(hours=1)))
            recent_events = cursor.fetchone()[0]

            # Detect state and suggest accordingly
            if total_wm >= 6:  # Near capacity
                suggestions.append({
                    "command": "/focus consolidate all true",
                    "reason": f"Working memory at {total_wm}/7 capacity",
                    "category": "memory",
                    "priority": "high"
                })
                suggestions.append({
                    "command": "/memory-health",
                    "reason": "Check cognitive load and health",
                    "category": "monitoring",
                    "priority": "high"
                })

            if len(recent_tasks) >= 3:  # Multiple tasks completed
                patterns = self.prospective_store.detect_task_patterns(
                    project_id=project_id,
                    min_occurrences=2,
                    time_window_hours=24
                )
                if patterns:
                    suggestions.append({
                        "command": "/consolidate",
                        "reason": f"Task patterns detected: {len(patterns)} possible workflows",
                        "category": "workflow",
                        "priority": "medium"
                    })

            if recent_events > 5:  # Many recent events
                suggestions.append({
                    "command": "/timeline",
                    "reason": f"Browse {recent_events} recent events",
                    "category": "review",
                    "priority": "low"
                })

            # Memory coverage check
            coverages = self.meta_store.list_domains(limit=5)
            low_coverage_domains = [c for c in coverages if c.memory_count < 5]
            if low_coverage_domains:
                suggestions.append({
                    "command": "/memory-health",
                    "reason": f"Low coverage in {len(low_coverage_domains)} domain(s)",
                    "category": "learning",
                    "priority": "low"
                })

            # Suggest research if gaps detected
            gaps = self.gap_detector.get_unresolved_gaps(project_id)
            if gaps:
                suggestions.append({
                    "command": "/research",
                    "reason": f"Knowledge gaps detected ({len(gaps)} areas)",
                    "category": "learning",
                    "priority": "low"
                })

            # Sort by priority
            priority_map = {"high": 0, "medium": 1, "low": 2}
            suggestions.sort(key=lambda x: priority_map.get(x["priority"], 99))

            return suggestions

        except Exception as e:
            logger.warning(f"Error suggesting commands: {e}")
            # Return default helpful suggestions on error
            return [
                {
                    "command": "/memory-query",
                    "reason": "Search your memory",
                    "category": "core",
                    "priority": "high"
                },
                {
                    "command": "/consolidate",
                    "reason": "Extract patterns from events",
                    "category": "workflow",
                    "priority": "medium"
                },
            ]

    # ===== WORKING MEMORY SEMANTIC TAGGING (Gap 4) =====
    def extract_semantic_tags(self, content: str) -> dict:
        """Extract semantic information from working memory content.

        Analyzes content to determine domain, context, and type for better
        consolidation routing.

        Args:
            content: Working memory item content

        Returns:
            Dict with 'domain', 'context', 'type', and 'tags' keys
        """
        import re

        tags = []
        domain = "general"
        item_type = "fact"

        content_lower = content.lower()

        # Detect domain from keywords
        domain_keywords = {
            "authentication": ["auth", "jwt", "oauth", "login", "password", "credential"],
            "database": ["db", "database", "sql", "query", "table", "schema", "migration"],
            "api": ["api", "endpoint", "route", "request", "response", "http", "rest", "graphql"],
            "ui": ["component", "react", "vue", "button", "form", "dialog", "layout", "css"],
            "performance": ["optimize", "cache", "latency", "throughput", "memory", "cpu"],
            "testing": ["test", "unit", "integration", "e2e", "jest", "pytest", "mock"],
            "deployment": ["deploy", "docker", "k8s", "ci/cd", "gitlab", "github"],
            "ml": ["model", "llm", "transformer", "embedding", "training", "inference"],
            "security": ["encrypt", "tls", "https", "token", "signature", "audit"],
        }

        for domain_name, keywords in domain_keywords.items():
            if any(kw in content_lower for kw in keywords):
                domain = domain_name
                tags.append(f"domain:{domain}")
                break

        # Detect item type from context
        if any(marker in content_lower for marker in ["how to", "workflow", "procedure", "steps", "process"]):
            item_type = "procedure"
            tags.append("type:procedure")
        elif any(marker in content_lower for marker in ["task", "todo", "fix", "implement", "add", "remove"]):
            item_type = "task"
            tags.append("type:task")
        elif any(marker in content_lower for marker in ["decision", "decided", "choose", "selected", "architecture"]):
            item_type = "decision"
            tags.append("type:decision")
        else:
            tags.append("type:fact")

        # Detect temporal references
        if any(marker in content_lower for marker in ["today", "tomorrow", "soon", "later", "next"]):
            tags.append("temporal:future")
        elif any(marker in content_lower for marker in ["yesterday", "before", "previously", "past"]):
            tags.append("temporal:past")

        # Detect code references
        if re.search(r'src/|\.py|\.js|\.rs|function|class|method', content):
            tags.append("reference:code")
        if re.search(r'\.json|\.yaml|\.toml|config', content):
            tags.append("reference:config")
        if re.search(r'http|api|endpoint', content):
            tags.append("reference:api")

        # Detect urgency
        if any(marker in content_lower for marker in ["critical", "urgent", "asap", "immediately", "broken", "bug"]):
            tags.append("priority:high")
        elif any(marker in content_lower for marker in ["low priority", "nice to have", "future", "optional"]):
            tags.append("priority:low")

        return {
            "domain": domain,
            "type": item_type,
            "tags": tags,
            "context": {
                "has_code_refs": "reference:code" in tags,
                "has_api_refs": "reference:api" in tags,
                "is_temporal": any(t.startswith("temporal:") for t in tags),
                "priority": next((t.split(":")[1] for t in tags if t.startswith("priority:")), "medium"),
            }
        }

    # ===== ATTENTION & MEMORY HEALTH INTEGRATION (Gap 3) =====
    def check_attention_memory_health(self, project_id: int) -> dict:
        """Check attention status and cognitive load, generate recommendations.

        Integrates attention management with memory health monitoring.
        Used for proactive alerts and auto-remediation suggestions.

        Args:
            project_id: Project ID

        Returns:
            Dict with health status and recommendations
        """
        recommendations = []
        warnings = []
        status = "healthy"

        try:
            # Get current attention state
            focus = self.attention_focus.get_focus(project_id)
            if focus:
                focus_duration = (datetime.now() - focus.started_at).total_seconds() / 3600
                if focus_duration > 4:  # More than 4 hours on same focus
                    warnings.append(
                        f"⚠️ Extended focus: {focus_duration:.1f}h on {focus.focus_type} attention"
                    )
                    recommendations.append(
                        "Consider `/focus clear {focus_type}` or `/attention set-secondary` to diversify"
                    )

            # Count active secondary focuses (divided attention)
            cursor = self.store.db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM attention_state
                WHERE project_id = ? AND focus_type = 'secondary' AND ended_at IS NULL
            """, (project_id,))
            secondary_count = cursor.fetchone()[0]

            if secondary_count > 4:  # Beyond 7±2 magical number
                status = "overloaded"
                warnings.append(
                    f"⚠️ Excessive divided attention: {secondary_count} secondary focuses"
                )
                recommendations.append(
                    "Too many secondary focuses. Run `/focus consolidate all true` to consolidate to LTM"
                )

            # Check cognitive load from load monitor
            try:
                load_report = self.load_monitor.get_current_load(project_id)
                if load_report and hasattr(load_report, 'saturation_level'):
                    saturation_str = load_report.saturation_level.value \
                        if hasattr(load_report.saturation_level, 'value') \
                        else str(load_report.saturation_level)

                    if saturation_str in ["saturated", "overloaded"]:
                        if status == "healthy":
                            status = "saturated"
                        warnings.append(
                            f"⚠️ Cognitive load {saturation_str}: {load_report.utilization_percent:.0f}% capacity"
                        )
                        recommendations.append(
                            "High cognitive load detected. `/consolidate` to extract patterns and free memory"
                        )
            except Exception as e:
                logger.warning(f"Could not check cognitive load: {e}")

            # Check for inhibition spreading (excessive memory suppression)
            cursor.execute("""
                SELECT COUNT(*) FROM attention_inhibition
                WHERE project_id = ? AND inhibited_at > ? AND expires_at > ?
            """, (project_id, datetime.now() - timedelta(hours=1), datetime.now()))
            active_inhibitions = cursor.fetchone()[0]

            if active_inhibitions > 5:
                warnings.append(f"⚠️ Excessive memory suppression: {active_inhibitions} inhibitions active")
                recommendations.append(
                    "Many memories are suppressed. Run `/attention clear-inhibition selective` to review"
                )

            # Generate summary
            summary = {
                "status": status,
                "primary_focus": focus.focus_type if focus else None,
                "secondary_focuses": secondary_count,
                "active_inhibitions": active_inhibitions,
                "warnings": warnings,
                "recommendations": recommendations,
            }

            return summary

        except Exception as e:
            logger.error(f"Error checking attention/health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recommendations": [],
            }

    # ===== RESEARCH FINDINGS INTEGRATION (Gap 2) =====
    async def store_research_findings(
        self,
        findings: list[dict],
        research_topic: str,
        source_agent: str,
        project_id: int,
        credibility: float = 0.8,
    ) -> int:
        """Store research findings in semantic memory with source attribution.

        Used to integrate research agent outputs into memory system.

        Args:
            findings: List of finding dicts with 'content', 'type', 'source'
            research_topic: Research topic or query
            source_agent: Name of agent that found this (arxiv-researcher, etc.)
            project_id: Project ID
            credibility: Credibility score (0.0-1.0) based on source

        Returns:
            Number of findings stored
        """
        findings_stored = 0

        for finding in findings:
            finding_content = finding.get("content", "")
            finding_type = finding.get("type", "fact")  # fact, pattern, decision
            finding_source = finding.get("source", "")

            if not finding_content:
                continue

            # Store finding in semantic memory with source metadata
            try:
                memory_id = await self.store.remember(
                    content=finding_content,
                    memory_type=finding_type,
                    project_id=project_id,
                    tags=[
                        f"research:{research_topic}",
                        f"source:{source_agent}",
                        f"credibility:{credibility:.2f}",
                        "research-finding",
                    ],
                )

                # Also store link to episodic event for research tracking
                finding_event = EpisodicEvent(
                    project_id=project_id,
                    session_id="research",
                    event_type=EventType.ACTION if finding_type == "fact" else EventType.DECISION,
                    content=f"[{source_agent}] {finding_content[:100]}",
                    outcome=EventOutcome.SUCCESS,
                    context=EventContext(
                        task=f"Research: {research_topic}",
                        phase="research-integration",
                    ),
                )
                self.episodic_store.record_event(finding_event)

                findings_stored += 1
            except Exception as e:
                logger.warning(f"Failed to store finding from {source_agent}: {e}")
                continue

        return findings_stored

    # Consolidation handler

    # Unified smart retrieval handler
    async def _handle_smart_retrieve(self, args: dict) -> list[TextContent]:
        """Handle smart_retrieve using UnifiedMemoryManager with advanced RAG support."""
        # Extract conversation history if provided
        conversation_history = args.get("conversation_history")

        # Pagination parameters (limit per layer)
        limit = min(args.get("limit", 10), 100)
        offset = args.get("offset", 0)

        # Ensure unified_manager is initialized (with fallback if no project context)
        try:
            manager = self.unified_manager
        except (AttributeError, RuntimeError):
            # If unified_manager not available, try to initialize it
            from memory_mcp.integration.unified_manager import UnifiedMemoryManager
            manager = UnifiedMemoryManager(self.store.db)
            manager.initialize()

        results = manager.retrieve(
            query=args["query"],
            context=args.get("context"),
            k=min(args.get("k", 5), limit),  # Respect limit
            conversation_history=conversation_history
        )

        if not results:
            return [TextContent(type="text", text="No results found.")]

        response = f"Smart Retrieval Results for: '{args['query']}'\n\n"

        # Add RAG info if available
        if self.unified_manager.rag_manager:
            rag_stats = self.unified_manager.rag_manager.get_stats()
            if rag_stats.get("hyde_enabled") or rag_stats.get("reranking_enabled"):
                response += "🔍 Advanced RAG: "
                enabled_features = []
                if rag_stats.get("hyde_enabled"):
                    enabled_features.append("HyDE")
                if rag_stats.get("reranking_enabled"):
                    enabled_features.append("LLM-reranking")
                if rag_stats.get("query_transform_enabled"):
                    enabled_features.append("Query-transform")
                if rag_stats.get("reflective_enabled"):
                    enabled_features.append("Reflective")
                response += ", ".join(enabled_features) + "\n\n"

        for layer, items in results.items():
            if not items:
                continue

            # Apply pagination to layer results
            layer_items = items[offset:offset+limit]
            response += f"## {layer.title()} Layer ({len(layer_items)} of {len(items)} results)\n\n"

            for item in layer_items:
                if isinstance(item, dict):
                    if "content" in item:
                        response += f"- {item['content'][:100]}{'...' if len(item.get('content', '')) > 100 else ''}\n"
                        if "similarity" in item:
                            response += f"  (similarity: {item['similarity']:.2f})\n"
                    elif "entity" in item:
                        response += f"- Entity: {item['entity']} ({item.get('type', 'unknown')})\n"
                    elif "name" in item:
                        response += f"- {item['name']}\n"
                else:
                    response += f"- {str(item)[:100]}\n"
                response += "\n"

        return [TextContent(type="text", text=response)]

    # Working Memory handlers
    async def _handle_get_working_memory(self, args: dict) -> list[TextContent]:
        """Handle get_working_memory tool call."""
        try:
            project = self.project_manager.get_or_create_project()
            component_filter = args.get("component", "all")

            items = []

            if component_filter in ["phonological", "all"]:
                phono_items = self.phonological_loop.get_items(project.id)
                for item in phono_items:
                    items.append({
                        "component": "phonological",
                        "id": item.id,
                        "content": item.content,
                        "activation": round(getattr(item, "current_activation", getattr(item, "activation_level", 0)), 2),
                        "importance": round(getattr(item, "importance_score", 0), 2),
                    })

            if component_filter in ["visuospatial", "all"]:
                spatial_items = self.visuospatial_sketchpad.get_items(project.id)
                for item in spatial_items:
                    items.append({
                        "component": "visuospatial",
                        "id": item.id,
                        "content": item.content,
                        "activation": round(getattr(item, "current_activation", getattr(item, "activation_level", 0)), 2),
                        "file_path": getattr(item, "file_path", ""),
                    })

            if component_filter in ["episodic_buffer", "all"]:
                buffer_items = self.episodic_buffer.get_items(project.id)
                for item in buffer_items:
                    items.append({
                        "component": "episodic_buffer",
                        "id": item.id,
                        "content": item.content,
                        "activation": round(getattr(item, "current_activation", getattr(item, "activation_level", 0)), 2),
                        "chunk_size": getattr(item, "chunk_size", 0),
                    })

            # Sort by activation
            items_sorted = sorted(items, key=lambda x: x["activation"], reverse=True)

            result = StructuredResult.success(
                data=items_sorted,
                metadata={
                    "operation": "get_working_memory",
                    "schema": "episodic",
                    "component_filter": component_filter,
                    "capacity": f"{len(items)}/7",
                    "status": "full" if len(items) >= 7 else "available",
                },
                pagination=PaginationMetadata(
                    returned=len(items),
                )
            )
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "get_working_memory"})

        return [result.as_optimized_content(schema_name="episodic")]

    async def _handle_update_working_memory(self, args: dict) -> list[TextContent]:
        """Handle update_working_memory tool call.

        Includes Gap 4 integration: Automatically extracts semantic tags from content
        for better consolidation routing (domain, type, references, priority).
        """
        project = self.project_manager.get_or_create_project()
        content = args.get("content")

        if not content:
            # If no content provided, return usage message
            return [TextContent(type="text", text="Error: 'content' parameter required. Example: update_working_memory(content='Important information to remember')")]

        content_type = args.get("content_type", "verbal")
        importance = args.get("importance", 0.5)
        # Clamp importance to 0-1 range (database constraint)
        importance = max(0.0, min(1.0, importance))

        # ===== GAP 4 INTEGRATION: EXTRACT SEMANTIC TAGS =====
        semantic_info = self.extract_semantic_tags(content)

        if content_type == "verbal":
            item_id = self.phonological_loop.add_item(project.id, content, importance)
            component = "phonological"
        else:  # spatial
            # For spatial content, try to extract file path
            file_path = None
            if "/" in content or "\\" in content:
                # Extract file path from content
                parts = content.split()
                for part in parts:
                    if "/" in part or "\\" in part:
                        file_path = part
                        break

            item_id = self.visuospatial_sketchpad.add_item(project.id, content, file_path)
            component = "visuospatial"

        # Store semantic tags in item metadata
        try:
            cursor = self.store.db.conn.cursor()
            metadata = {
                "semantic_domain": semantic_info["domain"],
                "semantic_type": semantic_info["type"],
                "semantic_tags": semantic_info["tags"],
                "semantic_context": semantic_info["context"],
            }
            cursor.execute("""
                UPDATE working_memory SET metadata = ? WHERE id = ?
            """, (json.dumps(metadata), item_id))
            self.store.db.conn.commit()
        except Exception as e:
            logger.warning(f"Could not store semantic tags for WM item {item_id}: {e}")

        # Check capacity
        phono_count = len(self.phonological_loop.get_items(project.id))
        spatial_count = len(self.visuospatial_sketchpad.get_items(project.id))
        buffer_count = len(self.episodic_buffer.get_items(project.id))
        total_count = phono_count + spatial_count + buffer_count

        capacity_status = "full" if total_count >= 7 else "available"

        response = f"✓ Added to {component} loop (ID: {item_id})\n"
        response += f"Working Memory: {total_count}/7 items ({capacity_status})\n"

        # ===== GAP 4: SHOW SEMANTIC TAGS IN RESPONSE =====
        if semantic_info["tags"]:
            response += f"\nSemantic Tags: {', '.join(semantic_info['tags'][:3])}"
            if len(semantic_info["tags"]) > 3:
                response += f" +{len(semantic_info['tags']) - 3} more"
            response += "\n"
            response += f"Domain: {semantic_info['domain']} | Type: {semantic_info['type']}\n"

        if total_count >= 7:
            response += "\n⚠️ At capacity - least active items will be auto-consolidated"
            response += "\n💡 Tip: Use `/focus consolidate all true` to consolidate to LTM"

        return [TextContent(type="text", text=response)]

    async def _handle_clear_working_memory(self, args: dict) -> list[TextContent]:
        """Handle clear_working_memory tool call."""
        project = self.project_manager.get_or_create_project()
        component_filter = args.get("component", "all")
        consolidate = args.get("consolidate", True)

        consolidated_count = 0
        cleared_count = 0

        if consolidate:
            # Consolidate items before clearing (consolidation disabled due to complex routing)
            # Simply track count and clear
            if component_filter in ["phonological", "all"]:
                items = self.phonological_loop.get_items(project.id)
                cleared_count += len(items)
                self.phonological_loop.clear(project.id)

            if component_filter in ["visuospatial", "all"]:
                items = self.visuospatial_sketchpad.get_items(project.id)
                cleared_count += len(items)
                self.visuospatial_sketchpad.clear(project.id)

            if component_filter in ["episodic_buffer", "all"]:
                items = self.episodic_buffer.get_items(project.id)
                cleared_count += len(items)
                self.episodic_buffer.clear(project.id)

            response = f"✓ Cleared working memory ({component_filter})\n"
            response += f"Items cleared: {cleared_count}"
        else:
            # Just clear without consolidation
            if component_filter in ["phonological", "all"]:
                items = self.phonological_loop.get_items(project.id)
                self.phonological_loop.clear(project.id)
                cleared_count += len(items)

            if component_filter in ["visuospatial", "all"]:
                items = self.visuospatial_sketchpad.get_items(project.id)
                self.visuospatial_sketchpad.clear(project.id)
                cleared_count += len(items)

            if component_filter in ["episodic_buffer", "all"]:
                items = self.episodic_buffer.get_items(project.id)
                self.episodic_buffer.clear(project.id)
                cleared_count += len(items)

            response = f"✓ Cleared working memory ({component_filter})\n"
            response += f"Items removed: {cleared_count} (not consolidated)"

        return [TextContent(type="text", text=response)]


    async def _handle_get_associations(self, args: dict) -> list[TextContent]:
        """Handle get_associations tool call."""
        memory_id = args["memory_id"]
        layer = args.get("layer", "semantic")  # Default to semantic layer
        project_id = args.get("project_id", 1)  # Provide default project_id
        max_results = min(args.get("max_results", 20), 100)

        try:
            neighbors = self.association_network.get_neighbors(
                memory_id=memory_id,
                layer=layer,
                project_id=project_id,
                min_strength=0.1,
                max_results=max_results
            )

            if not neighbors:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "get_associations",
                        "schema": "semantic",
                        "memory_id": memory_id,
                        "layer": layer,
                    }
                )
            else:
                formatted_links = []
                for link in neighbors:
                    direction = "→" if link.from_memory_id == memory_id else "←"
                    other_id = link.to_memory_id if link.from_memory_id == memory_id else link.from_memory_id
                    formatted_links.append({
                        "from_id": link.from_memory_id,
                        "to_id": link.to_memory_id,
                        "strength": round(link.link_strength, 2),
                        "direction": direction,
                    })

                result = StructuredResult.success(
                    data=formatted_links,
                    metadata={
                        "operation": "get_associations",
                        "schema": "semantic",
                        "memory_id": memory_id,
                        "layer": layer,
                        "count": len(formatted_links),
                    },
                    pagination=PaginationMetadata(
                        returned=len(formatted_links),
                        limit=max_results,
                    )
                )

        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "get_associations"})

        return [result.as_optimized_content(schema_name="semantic")]

    async def _handle_strengthen_association(self, args: dict) -> list[TextContent]:
        """Handle strengthen_association tool call."""
        link_id = args["link_id"]
        amount = args["amount"]

        try:
            new_strength = self.association_network.strengthen_link(link_id, amount)
            response = f"✓ Strengthened link {link_id}\n"
            response += f"New strength: {new_strength:.3f}"
            return [TextContent(type="text", text=response)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_find_memory_path(self, args: dict) -> list[TextContent]:
        """Handle find_memory_path tool call."""
        try:
            from_memory_id = args["from_memory_id"]
            from_layer = args["from_layer"]
            to_memory_id = args["to_memory_id"]
            to_layer = args["to_layer"]
            project_id = args.get("project_id", 1)  # Default to project 1

            path = self.association_network.find_path(
                from_memory_id=from_memory_id,
                from_layer=from_layer,
                to_memory_id=to_memory_id,
                to_layer=to_layer,
                project_id=project_id
            )

            if not path:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "find_memory_path",
                        "schema": "memory",
                        "from_id": from_memory_id,
                        "to_id": to_memory_id,
                    }
                )
            else:
                # Format path for structured response
                formatted_path = []
                for i, link in enumerate(path):
                    formatted_path.append({
                        "hop": i + 1,
                        "from_id": link.from_memory_id,
                        "to_id": link.to_memory_id,
                        "strength": round(link.link_strength, 2),
                    })

                result = StructuredResult.success(
                    data=formatted_path,
                    metadata={
                        "operation": "find_memory_path",
                        "schema": "memory",
                        "from_id": from_memory_id,
                        "from_layer": from_layer,
                        "to_id": to_memory_id,
                        "to_layer": to_layer,
                        "hops": len(formatted_path),
                    },
                    pagination=PaginationMetadata(
                        returned=len(formatted_path),
                    )
                )

        except KeyError as e:
            result = StructuredResult.error(f"Missing required parameter: {str(e)}", metadata={"operation": "find_memory_path"})
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "find_memory_path"})

        return [result.as_optimized_content(schema_name="memory")]

    # Phase 2: Attention System handlers
    async def _handle_get_attention_state(self, args: dict) -> list[TextContent]:
        """Handle get_attention_state tool call."""
        try:
            project_id = args["project_id"]
            focus = self.attention_focus.get_focus(project_id)

            if focus:
                structured_data = {
                    "focus_type": focus.focus_type,
                    "memory_id": focus.memory_id,
                    "memory_layer": focus.memory_layer,
                    "focused_at": focus.focused_at.isoformat() if focus.focused_at else None
                }
            else:
                structured_data = {
                    "focus_type": None,
                    "memory_id": None,
                    "memory_layer": None,
                    "focused_at": None,
                    "status": "No current focus"
                }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_attention_state", "schema": "meta"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="meta")]
        except Exception as e:
            logger.error(f"Error in get_attention_state [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_attention_state"})
            return [result.as_optimized_content(schema_name="meta")]

    async def _handle_set_attention_focus(self, args: dict) -> list[TextContent]:
        """Handle set_attention_focus tool call."""
        memory_id = args["memory_id"]
        layer = args["layer"]
        project_id = args["project_id"]
        focus_type = args["focus_type"]

        try:
            focus = self.attention_focus.set_focus(
                project_id=project_id,
                memory_id=memory_id,
                memory_layer=layer,
                focus_type=focus_type
            )

            response = f"✓ Set attention focus to {focus_type}\n"
            response += f"  Memory: {memory_id} ({layer})\n"
            response += f"  Focused at: {focus.focused_at}"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inhibit_memory(self, args: dict) -> list[TextContent]:
        """Handle inhibit_memory tool call."""
        memory_id = args["memory_id"]
        layer = args["layer"]
        project_id = args["project_id"]
        inhibition_type = args["inhibition_type"]
        duration_seconds = args.get("duration_seconds", 1800)

        try:
            inhibition_id = self.attention_inhibition.inhibit(
                project_id=project_id,
                memory_id=memory_id,
                memory_layer=layer,
                inhibition_type=inhibition_type,
                strength=1.0,
                duration_seconds=duration_seconds
            )

            response = f"✓ Inhibited memory {memory_id}\n"
            response += f"  Type: {inhibition_type}\n"
            response += f"  Duration: {duration_seconds}s\n"
            response += f"  Inhibition ID: {inhibition_id}"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Phase 4: Metacognition tool handlers

    async def _handle_evaluate_memory_quality(self, args: dict) -> list[TextContent]:
        """Handle evaluate_memory_quality tool call."""
        project_id = args.get("project_id")
        if not project_id:
            project = self.project_manager.get_or_create_project()
            project_id = project.id

        report = self.quality_monitor.get_quality_report(project_id)

        response = f"✓ Memory Quality Report - Project {project_id}\n\n"
        response += f"Overall Accuracy: {report.get('overall_avg_accuracy', 0.0):.2%}\n"
        response += f"False Positive Rate: {report.get('overall_avg_false_positive_rate', 0.0):.2%}\n\n"

        if report.get('quality_by_layer'):
            response += "Quality by Layer:\n"
            for layer, metrics in report['quality_by_layer'].items():
                if isinstance(metrics, dict):
                    accuracy = metrics.get('avg_accuracy', 0.0)
                    response += f"  - {layer}: {accuracy:.2%} accuracy\n"

        if report.get('poor_performers'):
            response += f"\nPoor Performers: {len(report['poor_performers'])} memories need attention\n"

        return [TextContent(type="text", text=response)]

    async def _handle_get_learning_rates(self, args: dict) -> list[TextContent]:
        """Handle get_learning_rates tool call."""
        try:
            project_id = args.get("project_id")
            if not project_id:
                project = self.project_manager.get_or_create_project()
                project_id = project.id

            report = self.learning_adjuster.get_learning_rate_report(project_id)

            strategies = report.get('strategy_rankings', [])
            formatted_strategies = [
                {
                    "rank": i,
                    "strategy": s['strategy'],
                    "success_rate": round(s.get('success_rate', 0) * 100, 1)
                }
                for i, s in enumerate(strategies, 1)
            ]

            recommendations = report.get('recommended_changes', [])
            formatted_recommendations = [
                {"action": r['action'], "reason": r['reason']}
                for r in recommendations[:3]
            ]

            structured_data = {
                "project_id": project_id,
                "summary": report.get('summary', 'No learning rate data available'),
                "strategy_rankings": formatted_strategies,
                "recommended_changes": formatted_recommendations
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_learning_rates", "schema": "meta"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="meta")]
        except Exception as e:
            logger.error(f"Error in get_learning_rates [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_learning_rates"})
            return [result.as_optimized_content(schema_name="meta")]

    async def _handle_detect_knowledge_gaps(self, args: dict) -> list[TextContent]:
        """Handle detect_knowledge_gaps tool call."""
        project_id = args.get("project_id")
        gap_type = args.get("gap_type")

        if not project_id:
            project = self.project_manager.get_or_create_project()
            project_id = project.id

        report = self.gap_detector.get_gap_report(project_id)

        response = f"✓ Knowledge Gap Report - Project {project_id}\n\n"
        response += f"Total Gaps: {report.get('total_gaps', 0)}\n"
        response += f"Unresolved: {report.get('unresolved_gaps', 0)}\n"
        response += f"Resolved: {report.get('resolved_gaps', 0)}\n\n"

        if report.get('by_type'):
            response += "Gaps by Type:\n"
            for gtype, count in report['by_type'].items():
                response += f"  - {gtype}: {count}\n"

        if report.get('resolutions_needed'):
            response += "\nResolutions Needed:\n"
            for item in report['resolutions_needed']:
                response += f"  - {item}\n"

        return [TextContent(type="text", text=response)]

    async def _handle_get_self_reflection(self, args: dict) -> list[TextContent]:
        """Handle get_self_reflection tool call."""
        try:
            project_id = args.get("project_id")
            if not project_id:
                project = self.project_manager.get_or_create_project()
                project_id = project.id

            report = self.reflection_system.generate_self_report(project_id)

            calibration = report.get('calibration', {})
            quality = report.get('reasoning_quality', {})

            structured_data = {
                "project_id": project_id,
                "summary": report.get('summary', f'Self-Assessment Report - Project {project_id}'),
                "calibration": {
                    "status": calibration.get('calibration_status', 'unknown'),
                    "reported_confidence": round(calibration.get('mean_reported', 0.0) * 100, 1),
                    "actual_accuracy": round(calibration.get('mean_actual', 0.0) * 100, 1)
                },
                "reasoning_quality": {
                    "assessment": quality.get('assessment', 'unknown'),
                    "quality_score": round(quality.get('quality_score', 0.0) * 100, 1),
                    "accuracy": round(quality.get('accuracy', 0.0) * 100, 1)
                }
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_self_reflection", "schema": "meta"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="meta")]
        except Exception as e:
            logger.error(f"Error in get_self_reflection [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_self_reflection"})
            return [result.as_optimized_content(schema_name="meta")]

    async def _handle_check_cognitive_load(self, args: dict) -> list[TextContent]:
        """Handle check_cognitive_load tool call."""
        project_id = args.get("project_id")
        if not project_id:
            project = self.project_manager.get_or_create_project()
            project_id = project.id

        report = self.load_monitor.get_cognitive_load_report(project_id)

        response = f"✓ Cognitive Load Report - Project {project_id}\n\n"

        current = report.get('current_load')
        if current:
            response += f"Current Utilization: {current.get('utilization_percent', 0.0):.1f}%\n"
            response += f"Query Latency: {current.get('query_latency_ms', 0.0):.1f}ms\n"
            response += f"Saturation Level: {current.get('saturation_level', 'unknown').upper()}\n\n"

        saturation_risk = report.get('saturation_risk', 'UNKNOWN')
        response += f"Risk Level: {saturation_risk}\n\n"

        recommendations = report.get('recommendations', [])
        if recommendations:
            response += "Recommendations:\n"
            for rec in recommendations[:3]:
                response += f"  - {rec.get('action')}: {rec.get('reason')}\n"

        return [TextContent(type="text", text=response)]

    async def _handle_get_metacognition_insights(self, args: dict) -> list[TextContent]:
        """Handle get_metacognition_insights tool call."""
        try:
            project_id = args.get("project_id")
            if not project_id:
                project = self.project_manager.get_or_create_project()
                project_id = project.id

            # Collect insights from all metacognition components
            quality_report = self.quality_monitor.get_quality_report(project_id)
            learning_report = self.learning_adjuster.get_learning_rate_report(project_id)
            gap_report = self.gap_detector.get_gap_report(project_id)
            reflection = self.reflection_system.generate_self_report(project_id)
            load_report = self.load_monitor.get_cognitive_load_report(project_id)

            top_strategy = learning_report.get('top_performer', {})
            quality = reflection.get('reasoning_quality', {})

            structured_data = {
                "project_id": project_id,
                "memory_quality": round(quality_report.get('overall_quality_score', 0.0) * 100, 1),
                "best_strategy": {
                    "name": top_strategy.get('strategy') if top_strategy else None,
                    "effectiveness": round(top_strategy.get('effectiveness_score', 0.0) * 100, 1) if top_strategy else None
                },
                "knowledge_gaps": {
                    "unresolved": gap_report.get('unresolved_gaps', 0),
                    "total": gap_report.get('total_gaps', 0)
                },
                "reasoning_quality": quality.get('assessment', 'unknown'),
                "cognitive_load": load_report.get('saturation_risk', 'UNKNOWN')
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_metacognition_insights", "schema": "meta"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="meta")]
        except Exception as e:
            logger.error(f"Error in get_metacognition_insights [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_metacognition_insights"})
            return [result.as_optimized_content(schema_name="meta")]

    # Phase 3.4: Advanced Planning Tool Handlers

    async def _handle_optimize_goal_orchestrator(self, args: dict) -> list[TextContent]:
        """Forward to Agent Optimization handler: optimize_goal_orchestrator."""
        from . import handlers_agent_optimization
        return await handlers_agent_optimization.handle_optimize_goal_orchestrator(self, args)


    async def _handle_optimize_strategy_orchestrator(self, args: dict) -> list[TextContent]:
        """Forward to Agent Optimization handler: optimize_strategy_orchestrator."""
        from . import handlers_agent_optimization
        return await handlers_agent_optimization.handle_optimize_strategy_orchestrator(self, args)

    async def _handle_optimize_attention_optimizer(self, args: dict) -> list[TextContent]:
        """Forward to Agent Optimization handler: optimize_attention_optimizer."""
        from . import handlers_agent_optimization
        return await handlers_agent_optimization.handle_optimize_attention_optimizer(self, args)

    async def _handle_optimize_learning_tracker(self, args: dict) -> list[TextContent]:
        """Forward to Skill Optimization handler: optimize_learning_tracker."""
        from . import handlers_skill_optimization
        return await handlers_skill_optimization.handle_optimize_learning_tracker(self, args)

    async def _handle_optimize_gap_detector(self, args: dict) -> list[TextContent]:
        """Forward to Skill Optimization handler: optimize_gap_detector."""
        from . import handlers_skill_optimization
        return await handlers_skill_optimization.handle_optimize_gap_detector(self, args)

    # ===== ATTENTION BUDGET & WORKING MEMORY (Layer 6 Enhancement) =====

    async def _handle_add_to_attention(self, args: dict) -> list[TextContent]:
        """Add an item to attention (working memory).

        Args:
            item_type: Type (goal|task|entity|memory|observation)
            item_id: ID in respective layer
            importance: Importance score (0-1)
            relevance: Relevance score (0-1)
            context: Optional context string

        Returns:
            Confirmation with item details
        """
        try:
            from ..meta.attention import AttentionManager

            project = self.project_manager.get_or_create_project()
            attention_mgr = AttentionManager(self.db)

            item_type = args.get("item_type", "task")
            item_id = args.get("item_id")
            importance = float(args.get("importance", 0.5))
            relevance = float(args.get("relevance", 0.5))
            context = args.get("context", "")

            if not item_id:
                return [TextContent(type="text", text="Error: item_id is required")]

            added_id = attention_mgr.add_attention_item(
                project_id=project.id,
                item_type=item_type,
                item_id=item_id,
                importance=importance,
                relevance=relevance,
                context=context,
            )

            # Enforce working memory constraint
            items = attention_mgr.get_attention_items(project.id, limit=10)

            response = f"✅ Added '{item_type}' (ID: {item_id}) to attention\n\n"
            response += f"Salience: {items[0].salience_score:.2f}\n"
            response += f"Importance: {importance:.2f}\n"
            response += f"Relevance: {relevance:.2f}\n"
            response += f"\nCurrent focus items: {len(items)}/9\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error adding to attention: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_attention(self, args: dict) -> list[TextContent]:
        """List all items in current attention (working memory).

        Args:
            limit: Maximum items to return (default: 10)
            min_salience: Minimum salience threshold (default: 0.0)

        Returns:
            Formatted list of attention items
        """
        try:
            from ..meta.attention import AttentionManager

            project = self.project_manager.get_or_create_project()
            attention_mgr = AttentionManager(self.db)

            limit = min(int(args.get("limit", 10)), 50)
            min_salience = float(args.get("min_salience", 0.0))

            items = attention_mgr.get_attention_items(project.id, limit=limit, min_salience=min_salience)

            if not items:
                return [TextContent(type="text", text="No items in attention (working memory is empty)")]

            response = f"📌 Attention Items ({len(items)} in focus):\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. [{item.item_type}] ID:{item.item_id}\n"
                response += f"   Salience: {item.salience_score:.2f} | Importance: {item.importance:.2f}\n"
                response += f"   Relevance: {item.relevance:.2f} | Activation: {item.activation_level:.2f}\n"
                if item.context:
                    response += f"   Context: {item.context}\n"
                response += "\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error listing attention items: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_apply_importance_decay(self, args: dict) -> list[TextContent]:
        """Apply exponential decay to importance of old, unused items.

        This implements spaced repetition: items not accessed recently have their
        importance gradually reduced, helping the system focus on current knowledge.

        Args:
            decay_rate: Exponential decay rate (default 0.05 = 5% per day)
            days_threshold: Only decay items older than this (default 30 days)

        Returns:
            Decay statistics and summary
        """
        try:
            from ..meta.attention import AttentionManager

            project = self.project_manager.get_or_create_project()
            attention_mgr = AttentionManager(self.db)

            decay_rate = float(args.get("decay_rate", 0.05))
            days_threshold = int(args.get("days_threshold", 30))

            result = attention_mgr.apply_importance_decay(
                project.id, decay_rate=decay_rate, days_threshold=days_threshold
            )

            if result["items_decayed"] == 0:
                response = "✅ No items needed decay (all items are recent/actively used)\n"
            else:
                response = f"📉 Importance Decay Applied:\n\n"
                response += f"Items Affected: {result['items_decayed']}\n"
                response += f"Average Decay: {result['avg_decay_amount']:.4f} importance units\n"
                response += f"Items Reaching Zero: {result['items_with_zero_importance']}\n"
                response += f"Applied At: {result['timestamp']}\n\n"
                response += f"💡 This helps the system focus on active, relevant knowledge\n"
                response += f"   Items not accessed in {days_threshold}+ days were decayed by ~{decay_rate*100:.1f}% per day\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error applying importance decay: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_working_memory(self, args: dict) -> list[TextContent]:
        """Get working memory state (7±2 constraint status).

        Returns:
            Working memory metrics and capacity status
        """
        try:
            from ..meta.attention import AttentionManager

            project = self.project_manager.get_or_create_project()
            attention_mgr = AttentionManager(self.db)

            wm = attention_mgr.get_working_memory(project.id)
            if not wm:
                wm = attention_mgr.create_working_memory(project.id)

            items = attention_mgr.get_attention_items(project.id, limit=20)

            response = "🧠 Working Memory Status (Baddeley's Model):\n\n"
            response += f"Capacity: {wm.capacity} ± {wm.capacity_variance} items\n"
            response += f"Current Load: {len(items)}/{wm.capacity + wm.capacity_variance} items\n"
            response += f"Cognitive Load: {wm.cognitive_load * 100:.1f}%\n"

            if wm.cognitive_load >= wm.overflow_threshold:
                response += f"\n⚠️ ATTENTION SATURATION ({wm.cognitive_load * 100:.1f}% >= {wm.overflow_threshold * 100:.1f}%)\n"
                response += "Recommendation: Consolidate or remove lower-priority items\n"

            response += f"\nDecay Rate: {wm.item_decay_rate * 100:.0f}% per hour\n"
            response += f"Refresh Threshold: {wm.refresh_threshold:.2f}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error getting working memory: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_set_focus(self, args: dict) -> list[TextContent]:
        """Set current focus area and allocate attention budget.

        Args:
            focus_area: Focus area (coding|debugging|learning|planning|reviewing)
            focus_level: Focus intensity (0-1)

        Returns:
            Confirmation with attention metrics
        """
        try:
            from ..meta.attention import AttentionManager

            project = self.project_manager.get_or_create_project()
            attention_mgr = AttentionManager(self.db)

            focus_area = args.get("focus_area", "coding")
            focus_level = float(args.get("focus_level", 0.8))

            attention_mgr.set_focus(project.id, focus_area, focus_level)

            budget = attention_mgr.get_attention_budget(project.id)
            if not budget:
                budget = attention_mgr.create_attention_budget(project.id, focus_area)

            response = f"🎯 Focus Set: {focus_area.upper()}\n\n"
            response += f"Focus Level: {focus_level * 100:.0f}%\n"
            response += f"Mental Energy: {budget.mental_energy * 100:.0f}%\n"
            response += f"Fatigue Level: {budget.fatigue_level * 100:.0f}%\n"
            response += f"Context Switches: {budget.context_switches}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error setting focus: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_attention_budget(self, args: dict) -> list[TextContent]:
        """Get current attention budget allocation.

        Returns:
            Focus allocation and current metrics
        """
        try:
            from ..meta.attention import AttentionManager

            project = self.project_manager.get_or_create_project()
            attention_mgr = AttentionManager(self.db)

            budget = attention_mgr.get_attention_budget(project.id)
            if not budget:
                budget = attention_mgr.create_attention_budget(project.id)

            response = "💡 Attention Budget Allocation:\n\n"
            response += f"Current Focus: {budget.current_focus}\n"
            response += f"Focus Level: {budget.current_focus_level * 100:.0f}%\n\n"

            response += "Budget Distribution:\n"
            for focus_type, allocation in budget.focus_allocation.items():
                response += f"  {focus_type.capitalize()}: {allocation * 100:.0f}%\n"

            response += f"\nMental Energy: {budget.mental_energy * 100:.0f}%\n"
            response += f"Fatigue: {budget.fatigue_level * 100:.0f}%\n"
            response += f"Context Switches: {budget.context_switches}\n"
            response += f"Optimal Session: {budget.optimal_session_length_minutes} min\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error getting attention budget: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]


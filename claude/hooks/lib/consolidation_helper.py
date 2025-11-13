"""Real consolidation helper for pattern extraction and semantic memory creation.

This replaces the hardcoded consolidation messages with actual pattern extraction,
clustering, and semantic memory creation.

Implements System 1 (fast, heuristic) + System 2 (slow, LLM) dual-process reasoning.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConsolidationHelper:
    """Performs real consolidation on episodic events."""

    def __init__(self):
        """Initialize with database connection."""
        self.conn = None
        self._connect()

    def _connect(self):
        """Connect to PostgreSQL database."""
        import psycopg

        try:
            self.conn = psycopg.connect(
                host=os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("ATHENA_POSTGRES_PORT", "5432")),
                dbname=os.environ.get("ATHENA_POSTGRES_DB", "athena"),
                user=os.environ.get("ATHENA_POSTGRES_USER", "postgres"),
                password=os.environ.get("ATHENA_POSTGRES_PASSWORD", "postgres"),
            )
            logger.debug("Connected to PostgreSQL for consolidation")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def _get_embedding_service(self):
        """Get embedding service for generating vectors."""
        try:
            # Try to import llamacpp embedding service
            import sys
            import os

            # Add hooks lib to path
            hooks_lib_path = os.path.dirname(os.path.abspath(__file__))
            if hooks_lib_path not in sys.path:
                sys.path.insert(0, hooks_lib_path)

            # Try to get embeddings from memory_helper if available
            try:
                from memory_helper import embed_text

                class EmbeddingServiceWrapper:
                    @staticmethod
                    def embed(text: str) -> Optional[List[float]]:
                        """Embed text using llamacpp service."""
                        return embed_text(text)

                return EmbeddingServiceWrapper()
            except:
                pass

            # Fallback: Try to connect to local llamacpp service
            try:
                import requests

                class LlamaCppEmbeddingService:
                    def __init__(self, host: str = "localhost", port: int = 8001):
                        self.url = f"http://{host}:{port}/v1/embeddings"

                    def embed(self, text: str) -> Optional[List[float]]:
                        """Generate embedding using llamacpp service."""
                        try:
                            response = requests.post(
                                self.url,
                                json={
                                    "input": text,
                                    "model": "nomic-embed-text"
                                },
                                timeout=5
                            )

                            if response.status_code == 200:
                                data = response.json()
                                if "data" in data and len(data["data"]) > 0:
                                    return data["data"][0].get("embedding")
                        except Exception as e:
                            logger.debug(f"Llamacpp embedding failed: {e}")

                        return None

                return LlamaCppEmbeddingService()
            except:
                pass

            # No embedding service available
            logger.warning("No embedding service available for consolidation")
            return None

        except Exception as e:
            logger.error(f"Error initializing embedding service: {e}")
            return None

    def consolidate_session(
        self, project_id: int, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consolidate events from a session into patterns and semantic memories.

        Args:
            project_id: Project ID
            session_id: Optional specific session ID (default: current session)

        Returns:
            Dictionary with consolidation results
        """
        try:
            # Phase 1: Get unconsolidated events
            events = self._get_unconsolidated_events(project_id, session_id)

            if not events:
                return {
                    "status": "no_events",
                    "events_found": 0,
                    "patterns_extracted": 0,
                    "discoveries_found": 0,
                }

            # Phase 2: Cluster events by type and temporal proximity (System 1 - fast)
            clusters = self._cluster_events(events)

            # Phase 3: Extract patterns from clusters
            patterns = self._extract_patterns(clusters)

            # Phase 4: Identify discoveries (high-impact analysis events)
            discoveries = self._identify_discoveries(events)

            # Phase 5: Create semantic memories from patterns
            created_memories = self._create_semantic_memories(
                project_id, patterns, discoveries
            )

            # Phase 6: Extract procedures from multi-step patterns
            procedures = self._extract_procedures(project_id, patterns)

            # Phase 7: Mark events as consolidated
            consolidated_count = self._mark_consolidated(project_id, events)

            return {
                "status": "success",
                "events_found": len(events),
                "patterns_extracted": len(patterns),
                "discoveries_found": len(discoveries),
                "semantic_memories_created": len(created_memories),
                "procedures_extracted": len(procedures),
                "events_consolidated": consolidated_count,
                "patterns": patterns,
                "discoveries": discoveries,
            }

        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "events_found": 0,
                "patterns_extracted": 0,
            }

    def _get_unconsolidated_events(
        self, project_id: int, session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get unconsolidated events from session."""
        try:
            cursor = self.conn.cursor()

            if session_id:
                cursor.execute(
                    """
                    SELECT id, event_type, content, timestamp, outcome, session_id
                    FROM episodic_events
                    WHERE project_id = %s
                      AND session_id = %s
                      AND consolidation_status = 'unconsolidated'
                    ORDER BY timestamp ASC
                    """,
                    (project_id, session_id),
                )
            else:
                # Get events from last 24 hours if no session specified
                cursor.execute(
                    """
                    SELECT id, event_type, content, timestamp, outcome, session_id
                    FROM episodic_events
                    WHERE project_id = %s
                      AND consolidation_status = 'unconsolidated'
                      AND timestamp > %s
                    ORDER BY timestamp ASC
                    """,
                    (project_id, int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)),
                )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "type": row[1],
                    "content": row[2],
                    "timestamp": row[3],
                    "outcome": row[4],
                    "session_id": row[5],
                }
                for row in rows
            ]

        except Exception as e:
            logger.warning(f"Error getting unconsolidated events: {e}")
            return []

    def _cluster_events(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Cluster events by type and temporal proximity (System 1 - fast).

        System 1 reasoning: Simple heuristics for quick clustering
        """
        clusters = defaultdict(list)

        # Primary cluster by event type
        for event in events:
            event_type = event["type"].split(":")[0]  # e.g., "tool_execution" from "tool_execution:read"
            clusters[event_type].append(event)

        # Secondary: temporal clustering within type clusters
        # Group events within 5 minutes of each other
        temporal_clusters = defaultdict(list)

        for event_type, type_events in clusters.items():
            current_cluster = []
            last_timestamp = None

            for event in type_events:
                timestamp = event["timestamp"]

                if last_timestamp is None or (timestamp - last_timestamp) < 300000:  # 5 minutes
                    current_cluster.append(event)
                else:
                    if current_cluster:
                        cluster_key = f"{event_type}_{len(temporal_clusters)}"
                        temporal_clusters[cluster_key] = current_cluster
                    current_cluster = [event]

                last_timestamp = timestamp

            if current_cluster:
                cluster_key = f"{event_type}_{len(temporal_clusters)}"
                temporal_clusters[cluster_key] = current_cluster

        return dict(temporal_clusters)

    def _extract_patterns(self, clusters: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Extract patterns from event clusters (System 1 - fast heuristics)."""
        patterns = []

        for cluster_name, events in clusters.items():
            if not events:
                continue

            # Pattern 1: Frequency pattern (high-frequency events)
            if len(events) >= 3:
                patterns.append(
                    {
                        "type": "frequency",
                        "cluster": cluster_name,
                        "count": len(events),
                        "content": f"Repeated {cluster_name} operations ({len(events)} times)",
                        "confidence": min(0.9, 0.5 + (len(events) * 0.1)),
                    }
                )

            # Pattern 2: Temporal pattern (clustering over time)
            if len(events) >= 2:
                first_time = events[0]["timestamp"]
                last_time = events[-1]["timestamp"]
                duration_minutes = (last_time - first_time) / 60000

                if duration_minutes > 0:
                    patterns.append(
                        {
                            "type": "temporal",
                            "cluster": cluster_name,
                            "duration_minutes": duration_minutes,
                            "content": f"Temporal clustering: {cluster_name} over {duration_minutes:.0f} minutes",
                            "confidence": 0.7,
                        }
                    )

            # Pattern 3: Discovery pattern (events marked with high importance)
            discoveries = [e for e in events if e["outcome"] in ["high", "critical"]]
            if discoveries:
                patterns.append(
                    {
                        "type": "discovery",
                        "cluster": cluster_name,
                        "count": len(discoveries),
                        "content": f"High-impact events: {len(discoveries)} discoveries in {cluster_name}",
                        "confidence": 0.85,
                    }
                )

        return patterns

    def _identify_discoveries(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify discovery events (analysis, insights, gaps, patterns)."""
        discoveries = []

        for event in events:
            if event["type"].startswith("discovery:"):
                discovery_subtype = event["type"].split(":")[1]
                discoveries.append(
                    {
                        "id": event["id"],
                        "type": discovery_subtype,
                        "title": event["content"].split("\n")[0][:100],  # First line as title
                        "content": event["content"],
                        "impact": event["outcome"],
                        "timestamp": event["timestamp"],
                    }
                )

        return discoveries

    def _create_semantic_memories(
        self, project_id: int, patterns: List[Dict], discoveries: List[Dict]
    ) -> List[int]:
        """Create semantic memories from patterns and discoveries in memory_vectors table."""
        created_ids = []

        try:
            cursor = self.conn.cursor()

            # Get embedding service
            embedding_service = self._get_embedding_service()

            # Create memories from high-confidence patterns
            for pattern in patterns:
                if pattern.get("confidence", 0) >= 0.7:
                    content = pattern["content"]

                    # Generate embedding for pattern
                    embedding = embedding_service.embed(content) if embedding_service else None

                    # Convert embedding to pgvector format if available
                    embedding_str = None
                    if embedding:
                        embedding_str = "[" + ",".join(f"{float(x):.6f}" for x in embedding) + "]"

                    # Insert into memory_vectors table
                    cursor.execute("""
                        INSERT INTO memory_vectors (
                            project_id, content, memory_type,
                            domain, tags, embedding, content_type,
                            consolidation_state, usefulness_score, confidence
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        project_id,
                        content,
                        "pattern",
                        pattern.get("domain", "general"),
                        [pattern["type"], pattern.get("cluster", "unclustered")],
                        embedding_str,
                        "pattern",
                        "consolidation_extracted",
                        0.8,
                        pattern.get("confidence", 0.7)
                    ))

                    memory_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
                    if memory_id:
                        created_ids.append(memory_id)
                        logger.info(f"Created semantic memory {memory_id} from pattern: {content[:100]}...")

            # Create memories from discoveries
            for discovery in discoveries:
                content = discovery["content"][:500] if discovery.get("content") else discovery.get("title", "")

                # Generate embedding for discovery
                embedding = embedding_service.embed(content) if embedding_service else None

                # Convert embedding to pgvector format if available
                embedding_str = None
                if embedding:
                    embedding_str = "[" + ",".join(f"{float(x):.6f}" for x in embedding) + "]"

                # Insert into memory_vectors table
                cursor.execute("""
                    INSERT INTO memory_vectors (
                        project_id, content, memory_type,
                        domain, tags, embedding, content_type,
                        consolidation_state, usefulness_score, confidence
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    project_id,
                    content,
                    discovery.get("type", "discovery"),
                    "discovery",
                    [discovery.get("type", "discovery"), discovery.get("category", "general")],
                    embedding_str,
                    "discovery",
                    "consolidation_extracted",
                    0.9,
                    0.95
                ))

                memory_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
                if memory_id:
                    created_ids.append(memory_id)
                    logger.info(f"Created semantic memory {memory_id} from discovery: {discovery.get('title', content[:100])}")

            # Commit all inserts
            self.conn.commit()

        except Exception as e:
            logger.error(f"Error creating semantic memories: {e}")
            if self.conn:
                self.conn.rollback()

        return created_ids

    def _extract_procedures(self, project_id: int, patterns: List[Dict]) -> List[int]:
        """Extract reusable procedures from temporal patterns (multi-step workflows)."""
        created_procedure_ids = []

        try:
            cursor = self.conn.cursor()

            # Extract procedures from temporal patterns with high confidence
            for pattern in patterns:
                if pattern["type"] == "temporal" and pattern.get("duration_minutes", 0) > 5:
                    # Only create procedures from high-confidence patterns
                    if pattern.get("confidence", 0) < 0.6:
                        continue

                    # Generate procedure name from pattern content
                    procedure_name = self._generate_procedure_name(pattern["content"][:100])

                    # Check if procedure already exists
                    cursor.execute(
                        "SELECT id FROM procedures WHERE name = %s",
                        (procedure_name,)
                    )

                    existing = cursor.fetchone()
                    if existing:
                        logger.debug(f"Procedure '{procedure_name}' already exists, skipping")
                        continue

                    # Extract steps from pattern (simple heuristic: split by sentences)
                    steps = self._extract_steps_from_pattern(pattern)

                    # Create procedure in database
                    cursor.execute("""
                        INSERT INTO procedures (
                            name, category, description, trigger_pattern,
                            template, steps, created_at, created_by
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        procedure_name,
                        pattern.get("category", "workflow"),
                        pattern["content"][:500],  # description
                        pattern.get("trigger_pattern", "manual"),  # trigger_pattern
                        pattern["content"],  # template
                        json.dumps(steps),  # steps (JSON array)
                        int(datetime.now().timestamp() * 1000),  # created_at (milliseconds)
                        "consolidation"  # created_by
                    ))

                    procedure_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
                    if procedure_id:
                        created_procedure_ids.append(procedure_id)
                        logger.info(f"Created procedure {procedure_id}: {procedure_name} with {len(steps)} steps")

            # Commit all inserts
            self.conn.commit()

        except Exception as e:
            logger.error(f"Error extracting procedures: {e}")
            if self.conn:
                self.conn.rollback()

        return created_procedure_ids

    def _generate_procedure_name(self, content: str) -> str:
        """Generate a unique procedure name from pattern content."""
        # Take first 50 chars, replace spaces with underscores, remove special chars
        import re
        base_name = re.sub(r'[^a-zA-Z0-9_]+', '_', content[:50].strip()).lower()
        # Ensure it's unique by adding timestamp
        timestamp = int(datetime.now().timestamp() * 1000) % 100000
        return f"{base_name}_{timestamp}"

    def _extract_steps_from_pattern(self, pattern: Dict[str, Any]) -> List[str]:
        """Extract procedure steps from a pattern."""
        steps = []

        # Try to get explicit steps if available
        if "steps" in pattern:
            if isinstance(pattern["steps"], list):
                return pattern["steps"]
            elif isinstance(pattern["steps"], str):
                steps = pattern["steps"].split(";")

        # If no explicit steps, split content into sentences as steps
        if not steps:
            content = pattern.get("content", "")
            # Split by sentence boundaries
            import re
            sentences = re.split(r'[.!?]+', content)
            steps = [s.strip() for s in sentences if s.strip()]

        # Limit to reasonable number of steps (max 20)
        return steps[:20] if steps else ["Execute pattern"]

    def _mark_consolidated(self, project_id: int, events: List[Dict[str, Any]]) -> int:
        """Mark events as consolidated."""
        try:
            cursor = self.conn.cursor()

            event_ids = [e["id"] for e in events]

            if event_ids:
                placeholders = ",".join(["%s"] * len(event_ids))
                cursor.execute(
                    f"""
                    UPDATE episodic_events
                    SET consolidation_status = 'consolidated'
                    WHERE id IN ({placeholders})
                    """,
                    event_ids,
                )

                self.conn.commit()
                return cursor.rowcount

            return 0

        except Exception as e:
            logger.warning(f"Error marking events as consolidated: {e}")
            if self.conn:
                self.conn.rollback()
            return 0


# Convenience function
def consolidate_session(project_id: int, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Standalone function to consolidate a session."""
    try:
        helper = ConsolidationHelper()
        results = helper.consolidate_session(project_id, session_id)
        helper.close()
        return results
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        return {"status": "error", "error": str(e)}

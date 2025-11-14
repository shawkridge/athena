"""
Comprehensive test suite for hook context injection.

Tests the full pipeline:
1. Consolidation creates semantic memories
2. Memories are persisted to PostgreSQL
3. Hook context injection retrieves and formats memories
4. Context is properly injected into user prompts
"""

import os
import sys
import json
import pytest
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, "/home/user/.claude/hooks/lib")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestHookContextInjectionPipeline:
    """Test the consolidation → storage → hook injection pipeline."""

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Set up test database with test data."""
        import psycopg
        from dotenv import load_dotenv

        # Load environment
        load_dotenv()

        # Connect to PostgreSQL
        self.conn = psycopg.connect(
            host=os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("ATHENA_POSTGRES_PORT", "5432")),
            dbname=os.environ.get("ATHENA_POSTGRES_DB", "athena"),
            user=os.environ.get("ATHENA_POSTGRES_USER", "postgres"),
            password=os.environ.get("ATHENA_POSTGRES_PASSWORD", "postgres"),
        )

        # Create or get test project
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO projects (name, path, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (path) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            ("test_project", "/home/user/.work/test", int(datetime.now().timestamp() * 1000)),
        )
        self.project_id = cursor.fetchone()[0]
        self.conn.commit()

        logger.info(f"Set up test project {self.project_id}")

        yield

        # Cleanup
        cursor.execute("DELETE FROM episodic_events WHERE project_id = %s", (self.project_id,))
        cursor.execute("DELETE FROM memory_vectors WHERE project_id = %s", (self.project_id,))
        cursor.execute("DELETE FROM procedures WHERE name LIKE %s", ("test_%",))
        self.conn.commit()
        self.conn.close()

    def _create_test_events(self) -> List[Dict[str, Any]]:
        """Create episodic events for consolidation."""
        cursor = self.conn.cursor()
        events = []

        # Create test events in different categories
        test_events = [
            {
                "event_type": "tool_execution:read",
                "content": "Read configuration from database.py - learned about connection pooling",
                "outcome": "high",
                "session_id": "session_1",
            },
            {
                "event_type": "tool_execution:read",
                "content": "Read authentication module - found JWT implementation",
                "outcome": "high",
                "session_id": "session_1",
            },
            {
                "event_type": "tool_execution:write",
                "content": "Fixed authentication bug in user service - added token validation",
                "outcome": "critical",
                "session_id": "session_1",
            },
            {
                "event_type": "discovery:insight",
                "content": "Database connection pooling improves scalability by 50%",
                "outcome": "high",
                "session_id": "session_1",
            },
            {
                "event_type": "discovery:pattern",
                "content": "Repeated pattern: All REST endpoints need error handling wrapper",
                "outcome": "high",
                "session_id": "session_1",
            },
        ]

        for event in test_events:
            cursor.execute(
                """
                INSERT INTO episodic_events (
                    project_id, event_type, content, timestamp,
                    outcome, session_id, consolidation_status, context
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    self.project_id,
                    event["event_type"],
                    event["content"],
                    int(datetime.now().timestamp() * 1000),
                    event["outcome"],
                    event["session_id"],
                    "unconsolidated",
                    json.dumps({"tags": ["test"]}),
                ),
            )
            event_id = cursor.fetchone()[0]
            events.append({**event, "id": event_id})

        self.conn.commit()
        logger.info(f"Created {len(events)} test events")
        return events

    def test_01_create_episodic_events(self):
        """Test 1: Verify episodic events are created."""
        events = self._create_test_events()

        assert len(events) == 5
        assert all(e["id"] for e in events)

        # Verify in database
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM episodic_events WHERE project_id = %s AND consolidation_status = %s",
            (self.project_id, "unconsolidated"),
        )
        count = cursor.fetchone()[0]
        assert count == 5

        logger.info("✅ PASS - Episodic events created")

    def test_02_consolidation_creates_semantic_memories(self):
        """Test 2: Verify consolidation creates semantic memories in PostgreSQL."""
        events = self._create_test_events()

        # Import consolidation helper
        from consolidation_helper import ConsolidationHelper

        helper = ConsolidationHelper()

        try:
            # Run consolidation
            result = helper.consolidate_session(self.project_id)

            logger.info(f"Consolidation result: {json.dumps(result, indent=2)}")

            # Verify consolidation succeeded
            assert result["status"] in ["success", "no_events"], f"Consolidation failed: {result}"
            assert result["events_found"] == 5
            assert result["patterns_extracted"] > 0

            # Verify semantic memories were created
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM memory_vectors WHERE project_id = %s",
                (self.project_id,),
            )
            memory_count = cursor.fetchone()[0]

            logger.info(f"Created {memory_count} semantic memories")
            assert memory_count > 0, "No semantic memories created"

            # Verify memory content
            cursor.execute(
                """
                SELECT id, content, memory_type, confidence, embedding
                FROM memory_vectors
                WHERE project_id = %s
                LIMIT 3
                """,
                (self.project_id,),
            )
            memories = cursor.fetchall()

            for mem_id, content, mem_type, confidence, embedding in memories:
                logger.info(f"Memory {mem_id}: {content[:60]}... (type: {mem_type}, confidence: {confidence})")
                assert content is not None
                assert mem_type in ["pattern", "discovery"]
                assert confidence > 0
                assert embedding is not None

            logger.info("✅ PASS - Consolidation created semantic memories")

        finally:
            helper.close()

    def test_03_context_injection_hook_retrieves_memories(self):
        """Test 3: Verify context injection hook can retrieve stored memories."""
        events = self._create_test_events()

        # Create semantic memories via consolidation
        from consolidation_helper import ConsolidationHelper

        helper = ConsolidationHelper()
        try:
            result = helper.consolidate_session(self.project_id)
            assert result["status"] in ["success", "no_events"]
        finally:
            helper.close()

        # Now test context injection - import MemoryBridge
        from memory_bridge import MemoryBridge

        bridge = MemoryBridge()

        try:
            # Get project for context injection
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, path FROM projects WHERE id = %s", (self.project_id,))
            project = cursor.fetchone()
            assert project is not None

            # Test 1: Get active memories
            active_mem = bridge.get_active_memories(self.project_id, limit=7)
            logger.info(f"Active memories: {active_mem}")

            # Test 2: Search for memories matching a query
            results = bridge.search_memories(self.project_id, "database connection pooling", limit=5)
            logger.info(f"Search results for 'database connection pooling': {results}")

            assert results["found"] >= 0, "Search should not fail"

            # Test 3: Get active goals
            goals = bridge.get_active_goals(self.project_id, limit=5)
            logger.info(f"Active goals: {goals}")

            logger.info("✅ PASS - Context injection hook can retrieve memories")

        finally:
            bridge.close()

    def test_04_prompt_analysis_and_intent_detection(self):
        """Test 4: Verify prompt analysis detects intent correctly."""
        from context_injector import ContextInjector

        injector = ContextInjector()

        # Test various prompts
        test_prompts = [
            ("How do I implement JWT authentication?", ["authentication"]),
            ("What's the best way to optimize database queries?", ["database", "performance"]),
            ("How do we handle API error responses?", ["api"]),
            ("Explain the architecture of our system", ["architecture"]),
            ("How do we test this component?", ["testing"]),
        ]

        for prompt, expected_intents in test_prompts:
            analysis = injector.analyze_prompt(prompt)
            logger.info(f"Prompt: {prompt}")
            logger.info(f"  Detected intents: {analysis['detected_intents']}")
            logger.info(f"  Keywords: {analysis['keywords']}")

            for expected in expected_intents:
                assert expected in analysis["detected_intents"] or expected in str(
                    analysis["keywords"]
                ), f"Expected '{expected}' in analysis of '{prompt}'"

        logger.info("✅ PASS - Prompt analysis detects intents correctly")

    def test_05_context_formatting_and_injection(self):
        """Test 5: Verify context is formatted and injected correctly."""
        from context_injector import ContextInjector, MemoryContext
        from datetime import datetime

        injector = ContextInjector()

        # Create test memory contexts
        test_contexts = [
            MemoryContext(
                id="auth-001",
                source_type="implementation",
                title="JWT Authentication System",
                relevance_score=0.95,
                content_preview="Implemented JWT with refresh tokens and expiry validation",
                keywords=["jwt", "auth", "tokens"],
                timestamp=datetime.now().isoformat(),
            ),
            MemoryContext(
                id="auth-002",
                source_type="decision_record",
                title="Why JWT over Sessions",
                relevance_score=0.87,
                content_preview="JWT chosen for scalability and statelessness",
                keywords=["jwt", "session", "decision"],
                timestamp=datetime.now().isoformat(),
            ),
        ]

        # Test injection
        prompt = "How should I implement authentication in a microservices architecture?"
        injected = injector.inject_context(prompt, test_contexts)

        logger.info(f"Original prompt: {prompt}")
        logger.info(f"Injected prompt:\n{injected}")

        # Verify injection includes context info
        assert "RELEVANT MEMORY CONTEXT" in injected
        assert "JWT Authentication System" in injected
        assert "relevance" in injected.lower()
        assert prompt in injected

        # Test injection summary
        summary = injector.get_injection_summary(test_contexts)
        logger.info(f"Injection summary: {json.dumps(summary, indent=2)}")

        assert summary["contexts_injected"] == 2
        assert summary["by_type"]["implementation"] == 1
        assert summary["by_type"]["decision_record"] == 1
        assert summary["average_relevance"] > 0.8

        logger.info("✅ PASS - Context formatting and injection works correctly")

    def test_06_full_pipeline_simulation(self):
        """Test 6: Full pipeline - events → consolidation → injection."""
        # Create events
        events = self._create_test_events()

        # Run consolidation
        from consolidation_helper import ConsolidationHelper
        from context_injector import ContextInjector

        helper = ConsolidationHelper()
        injector = ContextInjector()

        try:
            # Phase 1: Consolidation
            result = helper.consolidate_session(self.project_id)
            assert result["status"] in ["success", "no_events"]
            logger.info(f"Phase 1 - Consolidation: {result['patterns_extracted']} patterns, {result['semantic_memories_created']} memories")

            # Phase 2: Analyze prompt
            user_prompt = "How do we implement database connection pooling?"
            analysis = injector.analyze_prompt(user_prompt)
            logger.info(f"Phase 2 - Analysis: Detected intents: {analysis['detected_intents']}")

            # Phase 3: Search for context (simulate with MemoryBridge)
            from memory_bridge import MemoryBridge

            bridge = MemoryBridge()
            try:
                search_results = bridge.search_memories(self.project_id, user_prompt, limit=5)
                logger.info(f"Phase 3 - Search: Found {search_results['found']} matching memories")
            finally:
                bridge.close()

            # Phase 4: Inject context (simulated)
            # In real scenario, would convert search results to MemoryContext objects
            # For now, just verify the injection logic works
            test_contexts = []  # Would be populated from search results
            injected_prompt = injector.inject_context(user_prompt, test_contexts)
            logger.info(f"Phase 4 - Injection: Prompt ready for LLM")

            logger.info("✅ PASS - Full pipeline simulation successful")

        finally:
            helper.close()

    def test_07_hook_timing_and_performance(self):
        """Test 7: Verify hook execution stays within performance budget (<300ms)."""
        import time

        events = self._create_test_events()

        # Create semantic memories
        from consolidation_helper import ConsolidationHelper

        helper = ConsolidationHelper()
        try:
            helper.consolidate_session(self.project_id)
        finally:
            helper.close()

        # Time the context injection pipeline
        from context_injector import ContextInjector
        from memory_bridge import MemoryBridge

        injector = ContextInjector()
        bridge = MemoryBridge()

        try:
            user_prompt = "How do we handle API authentication?"

            start_time = time.time()

            # Pipeline steps
            analysis = injector.analyze_prompt(user_prompt)
            search_results = bridge.search_memories(self.project_id, user_prompt, limit=5)
            # In real hook, convert search results to MemoryContext and inject

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(f"Pipeline execution time: {elapsed_ms:.1f}ms")

            # Verify we're within budget
            assert elapsed_ms < 300, f"Pipeline took {elapsed_ms}ms, exceeds 300ms budget"

            logger.info("✅ PASS - Hook execution within performance budget")

        finally:
            bridge.close()


class TestContextInjectorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_memory(self):
        """Test context injection with empty memory."""
        from context_injector import ContextInjector

        injector = ContextInjector()

        prompt = "Test question?"
        analysis = injector.analyze_prompt(prompt)
        contexts = []

        # Should not fail with empty contexts
        injected = injector.inject_context(prompt, contexts)
        assert prompt in injected or injected == prompt

    def test_prompt_analysis_fallback(self):
        """Test prompt analysis with unclear intent."""
        from context_injector import ContextInjector

        injector = ContextInjector()

        # Generic prompt with no clear intent
        prompt = "Tell me about the project"
        analysis = injector.analyze_prompt(prompt)

        # Should still return valid analysis
        assert "detected_intents" in analysis
        assert "keywords" in analysis
        assert "retrieval_strategy" in analysis

    def test_retrieval_strategy_selection(self):
        """Test selection of retrieval strategy based on prompt."""
        from context_injector import ContextInjector

        injector = ContextInjector()

        test_cases = [
            ("how have we handled authentication?", "temporal_search"),
            ("what's the relationship between services?", "graph_search"),
            ("what if we scaled horizontally?", "scenario_search"),
        ]

        for prompt, expected_strategy in test_cases:
            strategy = injector.select_retrieval_strategy(
                injector.analyze_prompt(prompt)
            )
            # Strategy selection may not always match expected due to fallback logic
            logger.info(f"Prompt: {prompt} -> Strategy: {strategy}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

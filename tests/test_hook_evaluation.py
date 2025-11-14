#!/usr/bin/env python3
"""
Hook Evaluation Test - Validates hooks work end-to-end with real memories

Tests:
1. Create episodic events
2. Run consolidation → create semantic memories
3. Hook prompt analysis and context retrieval
4. Context injection quality and formatting
5. Performance metrics
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, "/home/user/.claude/hooks/lib")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HookEvaluator:
    """Evaluate hook functionality with real memories."""

    def __init__(self):
        """Initialize hook evaluator."""
        self.results = {}
        self.memories_created = []
        self.project_id = None

    def setup(self):
        """Set up test environment."""
        import psycopg
        from dotenv import load_dotenv

        load_dotenv()

        self.conn = psycopg.connect(
            host=os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("ATHENA_POSTGRES_PORT", "5432")),
            dbname=os.environ.get("ATHENA_POSTGRES_DB", "athena"),
            user=os.environ.get("ATHENA_POSTGRES_USER", "postgres"),
            password=os.environ.get("ATHENA_POSTGRES_PASSWORD", "postgres"),
        )

        # Create test project
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO projects (name, path, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (path) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            ("hook_evaluation", "/home/user/.work/hook_eval", datetime.now()),
        )
        self.project_id = cursor.fetchone()[0]
        self.conn.commit()

    def cleanup(self):
        """Clean up test data."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM episodic_events WHERE project_id = %s", (self.project_id,))
        cursor.execute("DELETE FROM memory_vectors WHERE project_id = %s", (self.project_id,))
        self.conn.commit()
        self.conn.close()

    def test_01_create_realistic_events(self) -> bool:
        """Test 1: Create realistic episodic events."""
        print("\n" + "=" * 70)
        print("TEST 1: Creating Realistic Episodic Events")
        print("=" * 70)

        events = [
            {
                "type": "tool_execution:read",
                "content": "Read user authentication module - found JWT implementation with refresh tokens",
                "outcome": "high",
            },
            {
                "type": "tool_execution:write",
                "content": "Fixed authentication bug - added token expiry validation and rate limiting",
                "outcome": "critical",
            },
            {
                "type": "discovery:insight",
                "content": "JWT tokens should have short expiry (15min) with refresh tokens (7 days)",
                "outcome": "high",
            },
            {
                "type": "tool_execution:read",
                "content": "Reviewed database schema for user sessions table",
                "outcome": "high",
            },
            {
                "type": "discovery:pattern",
                "content": "Pattern: All API endpoints need error handling middleware",
                "outcome": "high",
            },
            {
                "type": "discovery:insight",
                "content": "Error handling middleware should return consistent JSON format",
                "outcome": "high",
            },
        ]

        cursor = self.conn.cursor()
        for event in events:
            cursor.execute(
                """
                INSERT INTO episodic_events (
                    project_id, event_type, content, timestamp,
                    outcome, session_id, consolidation_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.project_id,
                    event["type"],
                    event["content"],
                    int(datetime.now().timestamp() * 1000),
                    event["outcome"],
                    "hook_eval_session",
                    "unconsolidated",
                ),
            )

        self.conn.commit()

        print(f"✅ Created {len(events)} realistic episodic events")
        print(f"   Events include:")
        print(f"   • Tool executions (read/write)")
        print(f"   • Insights (JWT token strategy)")
        print(f"   • Patterns (middleware architecture)")

        return True

    def test_02_consolidate_to_semantic_memories(self) -> bool:
        """Test 2: Consolidate events into semantic memories."""
        print("\n" + "=" * 70)
        print("TEST 2: Consolidating Events to Semantic Memories")
        print("=" * 70)

        from consolidation_helper import ConsolidationHelper

        helper = ConsolidationHelper()

        try:
            start_time = time.time()
            result = helper.consolidate_session(self.project_id)
            elapsed_ms = (time.time() - start_time) * 1000

            print(f"✅ Consolidation completed in {elapsed_ms:.1f}ms")
            print(f"   Status: {result['status']}")
            print(f"   Events processed: {result.get('events_found', 0)}")
            print(f"   Patterns extracted: {result.get('patterns_extracted', 0)}")
            print(f"   Memories created: {result.get('semantic_memories_created', 0)}")

            # Verify memories in database
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, content, memory_type, confidence
                FROM memory_vectors
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (self.project_id,),
            )

            memories = cursor.fetchall()
            self.memories_created = memories

            print(f"\n✅ Stored {len(memories)} semantic memories in PostgreSQL:")
            for mem_id, content, mem_type, confidence in memories:
                preview = content[:60] + "..." if len(content) > 60 else content
                print(f"   • [{mem_type}] {preview} (confidence: {confidence:.2f})")

            return len(memories) > 0

        finally:
            helper.close()

    def test_03_hook_context_analysis(self) -> bool:
        """Test 3: Hook context analysis - detect user intent."""
        print("\n" + "=" * 70)
        print("TEST 3: Hook Context Analysis")
        print("=" * 70)

        from context_injector import ContextInjector

        injector = ContextInjector()

        # Test prompts related to our created memories
        test_prompts = [
            "How should I implement JWT authentication?",
            "What's the best approach for token expiry?",
            "How do I add error handling to API endpoints?",
            "What authentication strategies are recommended?",
        ]

        print(f"✅ Analyzing {len(test_prompts)} prompts:")

        all_intents = set()
        for prompt in test_prompts:
            analysis = injector.analyze_prompt(prompt)
            intents = analysis.get("detected_intents", [])
            all_intents.update(intents)

            print(f"\n   Prompt: {prompt}")
            print(f"   → Intents: {', '.join(intents) if intents else 'none'}")
            print(f"   → Keywords: {', '.join(analysis.get('keywords', [])[:3])}")
            print(f"   → Strategy: {analysis.get('retrieval_strategy', 'hybrid')}")

        print(f"\n✅ Detected {len(all_intents)} distinct intents across prompts")
        print(f"   Intents: {', '.join(sorted(all_intents))}")

        return len(all_intents) > 0

    def test_04_hook_memory_retrieval(self) -> bool:
        """Test 4: Hook memory retrieval - search for relevant memories."""
        print("\n" + "=" * 70)
        print("TEST 4: Hook Memory Retrieval")
        print("=" * 70)

        from memory_bridge import MemoryBridge

        bridge = MemoryBridge()

        try:
            # Test search for authentication-related memories
            print(f"✅ Searching for memories related to authentication...")

            start_time = time.time()
            results = bridge.search_memories(
                self.project_id, "JWT authentication tokens", limit=5
            )
            search_time_ms = (time.time() - start_time) * 1000

            print(f"   Search completed in {search_time_ms:.1f}ms")
            print(f"   Found: {results.get('found', 0)} matching memories")

            if results.get("found", 0) > 0:
                print(f"\n   Top Results:")
                for i, result in enumerate(results.get("results", [])[:3], 1):
                    content = result.get("content", "")[:60]
                    print(f"   {i}. {content}...")

            # Test active memories
            print(f"\n✅ Retrieving active working memory...")
            active = bridge.get_active_memories(self.project_id, limit=7)
            print(f"   Found {active.get('count', 0)} active memories")

            return search_time_ms < 1000  # Should be fast

        finally:
            bridge.close()

    def test_05_hook_context_injection(self) -> bool:
        """Test 5: Hook context injection - format and inject context."""
        print("\n" + "=" * 70)
        print("TEST 5: Hook Context Injection")
        print("=" * 70)

        from context_injector import ContextInjector, MemoryContext

        injector = ContextInjector()

        # Create mock MemoryContext from our stored memories
        if not self.memories_created:
            print("⚠️  No memories to inject (consolidation may have failed)")
            return False

        # Convert database memories to MemoryContext objects
        contexts = []
        for mem_id, content, mem_type, confidence in self.memories_created[:3]:
            context = MemoryContext(
                id=str(mem_id),
                source_type=mem_type,
                title=content[:50],
                relevance_score=float(confidence),
                content_preview=content[:100],
                keywords=mem_type.split("_"),
                timestamp=datetime.now().isoformat(),
            )
            contexts.append(context)

        # Test injection with real user prompts
        user_prompt = "How should I implement JWT authentication in a microservices architecture?"

        print(f"✅ Injecting context into user prompt:")
        print(f"   Prompt: {user_prompt}")
        print(f"   Context items: {len(contexts)}")

        start_time = time.time()
        enhanced_prompt = injector.inject_context(user_prompt, contexts)
        injection_time_ms = (time.time() - start_time) * 1000

        print(f"\n✅ Context injection completed in {injection_time_ms:.1f}ms")
        print(f"   Original prompt length: {len(user_prompt)} chars")
        print(f"   Enhanced prompt length: {len(enhanced_prompt)} chars")
        print(f"   Expansion factor: {len(enhanced_prompt) / len(user_prompt):.1f}x")

        # Show sample of enhanced prompt
        print(f"\n📝 Enhanced Prompt Sample:")
        print("   " + "=" * 66)
        lines = enhanced_prompt.split("\n")
        for line in lines[:10]:
            print(f"   {line}")
        if len(lines) > 10:
            print(f"   ... ({len(lines) - 10} more lines)")
        print("   " + "=" * 66)

        # Verify context is in enhanced prompt
        has_context = "RELEVANT MEMORY CONTEXT" in enhanced_prompt
        has_original = user_prompt in enhanced_prompt or "microservices" in enhanced_prompt

        if has_context and has_original:
            print(f"\n✅ Context properly injected:")
            print(f"   • Contains memory context header: {has_context}")
            print(f"   • Contains original prompt: {has_original}")
            return True
        else:
            print(f"\n❌ Context injection issues:")
            print(f"   • Memory context header: {has_context}")
            print(f"   • Original prompt preserved: {has_original}")
            return False

    def test_06_hook_performance(self) -> bool:
        """Test 6: Hook performance - measure full pipeline."""
        print("\n" + "=" * 70)
        print("TEST 6: Hook Performance Analysis")
        print("=" * 70)

        from context_injector import ContextInjector
        from memory_bridge import MemoryBridge

        injector = ContextInjector()
        bridge = MemoryBridge()

        try:
            test_prompts = [
                "How do we handle authentication in distributed systems?",
                "What's the best way to structure API error responses?",
                "How do I implement rate limiting?",
                "What are security best practices?",
                "How should tokens be validated?",
            ]

            print(f"✅ Running performance test with {len(test_prompts)} prompts:")

            times = {"analysis": [], "search": [], "injection": [], "total": []}

            for prompt in test_prompts:
                start_total = time.time()

                # Stage 1: Analysis
                start = time.time()
                analysis = injector.analyze_prompt(prompt)
                times["analysis"].append((time.time() - start) * 1000)

                # Stage 2: Search
                start = time.time()
                results = bridge.search_memories(self.project_id, prompt, limit=5)
                times["search"].append((time.time() - start) * 1000)

                # Stage 3: Injection
                start = time.time()
                _ = injector.inject_context(prompt, [])
                times["injection"].append((time.time() - start) * 1000)

                times["total"].append((time.time() - start_total) * 1000)

            # Calculate statistics
            print(f"\n   Pipeline Performance (milliseconds):")
            print(f"   {'Stage':<20} {'Min':<8} {'Avg':<8} {'Max':<8} {'Target':<10}")
            print(f"   {'-' * 60}")

            targets = {
                "analysis": 50,
                "search": 100,
                "injection": 50,
                "total": 300,
            }

            for stage in ["analysis", "search", "injection", "total"]:
                stage_times = times[stage]
                min_t = min(stage_times)
                avg_t = sum(stage_times) / len(stage_times)
                max_t = max(stage_times)
                target = targets[stage]
                status = "✅" if avg_t < target else "⚠️"

                print(
                    f"   {stage:<20} {min_t:<8.1f} {avg_t:<8.1f} {max_t:<8.1f} {target:<10}ms {status}"
                )

            avg_total = sum(times["total"]) / len(times["total"])
            print(f"\n✅ Average total pipeline time: {avg_total:.1f}ms (target: <300ms)")

            return avg_total < 300

        finally:
            bridge.close()

    def test_07_hook_integration_quality(self) -> bool:
        """Test 7: Hook integration quality - end-to-end scenario."""
        print("\n" + "=" * 70)
        print("TEST 7: Hook Integration Quality")
        print("=" * 70)

        from context_injector import ContextInjector, MemoryContext
        from memory_bridge import MemoryBridge

        injector = ContextInjector()
        bridge = MemoryBridge()

        try:
            # Realistic scenario: Developer asking about authentication
            developer_prompt = (
                "I'm implementing authentication for a new microservice. "
                "What should I consider? We're using JWT tokens and need "
                "to handle token expiry."
            )

            print(f"📝 Developer Scenario:")
            print(f"   Prompt: {developer_prompt}")

            # Step 1: Analyze
            analysis = injector.analyze_prompt(developer_prompt)
            print(f"\n✅ Step 1 - Analysis:")
            print(f"   Detected intents: {analysis.get('detected_intents', [])}")
            print(f"   Strategy: {analysis.get('retrieval_strategy', 'hybrid')}")

            # Step 2: Search
            results = bridge.search_memories(self.project_id, developer_prompt, limit=3)
            print(f"\n✅ Step 2 - Memory Search:")
            print(f"   Found {results.get('found', 0)} relevant memories")

            # Step 3: Create context objects (mock)
            if self.memories_created:
                contexts = []
                for mem_id, content, mem_type, confidence in self.memories_created[:2]:
                    context = MemoryContext(
                        id=str(mem_id),
                        source_type=mem_type,
                        title=content[:50],
                        relevance_score=float(confidence),
                        content_preview=content[:80],
                        keywords=[mem_type],
                        timestamp=datetime.now().isoformat(),
                    )
                    contexts.append(context)

                # Step 4: Inject
                print(f"\n✅ Step 3 - Context Injection:")
                print(f"   Injecting {len(contexts)} memories")

                enhanced = injector.inject_context(developer_prompt, contexts)

                # Quality metrics
                has_metadata = "Relevance:" in enhanced
                has_types = any(t in enhanced for t in ["implementation", "insight", "pattern"])
                preserves_original = developer_prompt in enhanced or "microservice" in enhanced

                print(f"\n✅ Quality Check:")
                print(f"   • Metadata included: {has_metadata}")
                print(f"   • Memory types shown: {has_types}")
                print(f"   • Original preserved: {preserves_original}")

                quality_score = sum([has_metadata, has_types, preserves_original]) / 3
                print(f"\n✅ Integration Quality Score: {quality_score * 100:.0f}%")

                return quality_score >= 0.66
            else:
                print(f"⚠️  No memories to test with")
                return False

        finally:
            bridge.close()

    def run_all(self):
        """Run all hook evaluation tests."""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 68 + "║")
        print("║" + "HOOK EVALUATION TEST SUITE".center(68) + "║")
        print("║" + "Testing consolidation → memory → context injection pipeline".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("╚" + "=" * 68 + "╝")

        self.setup()

        try:
            results = {
                "test_01_create_events": self.test_01_create_realistic_events(),
                "test_02_consolidation": self.test_02_consolidate_to_semantic_memories(),
                "test_03_analysis": self.test_03_hook_context_analysis(),
                "test_04_retrieval": self.test_04_hook_memory_retrieval(),
                "test_05_injection": self.test_05_hook_context_injection(),
                "test_06_performance": self.test_06_hook_performance(),
                "test_07_quality": self.test_07_hook_integration_quality(),
            }

            # Summary
            passed = sum(1 for v in results.values() if v)
            total = len(results)

            print("\n" + "=" * 70)
            print("HOOK EVALUATION SUMMARY")
            print("=" * 70)

            print(f"\nResults:")
            for test_name, result in results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                test_display = test_name.replace("test_", "").replace("_", " ").title()
                print(f"  {status} - {test_display}")

            print(f"\n{'=' * 70}")
            print(f"Total: {passed}/{total} tests passing ({100 * passed / total:.0f}% success rate)")
            print(f"{'=' * 70}\n")

            if passed == total:
                print("🎉 ALL HOOK EVALUATION TESTS PASSING!")
                print("Hooks are ready for production deployment.\n")
            else:
                print(f"⚠️  {total - passed} test(s) need attention.\n")

        finally:
            self.cleanup()


if __name__ == "__main__":
    evaluator = HookEvaluator()
    evaluator.run_all()

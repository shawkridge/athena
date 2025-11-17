#!/usr/bin/env python3
"""
Create Athena Dashboard completion plan using Athena's planning system.

This script uses Athena's native planning and prospective memory layers to:
1. Create a comprehensive plan for completing the dashboard
2. Create prospective tasks for tracking progress
3. Store the plan in semantic memory for reference

Run with: python create_completion_plan.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add Athena to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena import (
    initialize_athena,
    create_plan,
    create_task,
    store,
    remember,
)


async def main():
    """Create dashboard completion plan using Athena."""

    print("🚀 Creating Athena Dashboard Completion Plan...")
    print("-" * 60)

    # Initialize Athena
    success = await initialize_athena()
    if not success:
        print("❌ Failed to initialize Athena")
        return
    print("✅ Athena initialized")

    # Create the main plan
    plan_data = await create_plan(
        goal="Complete Athena Dashboard (Phase 2-3 Transition)",
        description=(
            "Full integration of real-time backend with frontend pages. "
            "Replace mock data with live Athena memory queries. "
            "Dashboard is at Phase 2-3 transition: backend API built (16+ endpoints), "
            "all 17 frontend pages designed, real-time polling implemented but with mock data. "
            "Goal: make fully functional MVP with real Athena integration."
        ),
        depth=3,
        tags=["athena", "dashboard", "priority-high", "phase2", "phase3"],
    )

    plan_id = plan_data.get("id") or plan_data.get("plan_id", "unknown")
    print(f"✅ Main plan created (ID: {plan_id})")
    print(f"   Goal: {plan_data.get('goal')}")
    print(f"   Depth: {plan_data.get('depth')}")

    # Create prospective tasks for major milestones
    task_ids = []
    today = datetime.now()

    # Phase 2: Real-time Updates (3 days)
    print("\n📋 Creating Phase 2 tasks (Real-time Updates)...")

    task1 = await create_task(
        title="Phase 2A: Replace mock data with real Athena queries",
        description=(
            "Replace TaskPollingService mock data with real Athena stores queries. "
            "Implement task predictions using Athena prospective layer. "
            "Wire up dependency tracking from Athena knowledge graph."
        ),
        priority="high",
        tags=["phase2", "backend", "task-polling"],
        due_date=today + timedelta(days=3),
    )
    task1_id = task1.get("id") or task1.get("task_id")
    task_ids.append(task1_id)
    print(f"  ✅ Task 1: {task1_id}")

    task2 = await create_task(
        title="Phase 2B: Fix email notification integration",
        description=(
            "Complete email notification service integration with SendGrid or AWS SES. "
            "Test notification delivery for task updates."
        ),
        priority="medium",
        tags=["phase2", "backend", "notifications"],
        due_date=today + timedelta(days=3),
    )
    task2_id = task2.get("id") or task2.get("task_id")
    task_ids.append(task2_id)
    print(f"  ✅ Task 2: {task2_id}")

    # Phase 3: Frontend Integration (5 days)
    print("\n📋 Creating Phase 3 tasks (Frontend Integration)...")

    task3 = await create_task(
        title="Phase 3A: Implement missing backend endpoints",
        description=(
            "Implement remaining backend endpoints: /api/load/history, "
            "/api/learning/strategies, /api/analysis/* (critical path, bottlenecks, anomalies). "
            "Replace all placeholder data returns with real queries."
        ),
        priority="high",
        tags=["phase3", "backend", "endpoints"],
        due_date=today + timedelta(days=5),
    )
    task3_id = task3.get("id") or task3.get("task_id")
    task_ids.append(task3_id)
    print(f"  ✅ Task 3: {task3_id}")

    task4 = await create_task(
        title="Phase 3B: API integration for Overview and Health pages",
        description=(
            "Connect OverviewPage to /api/system/overview. "
            "Connect SystemHealthPage to /api/system/health. "
            "Implement loading states, error boundaries, data refresh."
        ),
        priority="high",
        tags=["phase3", "frontend", "pages"],
        due_date=today + timedelta(days=6),
    )
    task4_id = task4.get("id") or task4.get("task_id")
    task_ids.append(task4_id)
    print(f"  ✅ Task 4: {task4_id}")

    task5 = await create_task(
        title="Phase 3C: API integration for memory pages",
        description=(
            "Connect EpisodicMemoryPage to /api/episodic/events. "
            "Connect SemanticMemoryPage to /api/semantic/search. "
            "Connect ProceduralMemoryPage to /api/procedural/skills. "
            "Connect ProspectiveMemoryPage to /api/prospective/tasks."
        ),
        priority="high",
        tags=["phase3", "frontend", "pages", "memory"],
        due_date=today + timedelta(days=7),
    )
    task5_id = task5.get("id") or task5.get("task_id")
    task_ids.append(task5_id)
    print(f"  ✅ Task 5: {task5_id}")

    task6 = await create_task(
        title="Phase 3D: API integration for advanced pages",
        description=(
            "Connect KnowledgeGraphPage to /api/graph/stats. "
            "Connect MetaMemoryPage to /api/meta/quality. "
            "Connect ConsolidationPage to /api/consolidation/analytics. "
            "Connect HookExecutionPage, WorkingMemoryPage, RAGPlanningPage, "
            "LearningAnalyticsPage, PerformanceMonitoringPage, ResearchPage, SettingsPage."
        ),
        priority="high",
        tags=["phase3", "frontend", "pages", "advanced"],
        due_date=today + timedelta(days=8),
    )
    task6_id = task6.get("id") or task6.get("task_id")
    task_ids.append(task6_id)
    print(f"  ✅ Task 6: {task6_id}")

    # Testing & Documentation (2 days)
    print("\n📋 Creating Testing & Documentation tasks...")

    task7 = await create_task(
        title="Testing Phase: Integration and E2E tests",
        description=(
            "Write integration tests for backend API endpoints. "
            "Test frontend page data rendering with real API responses. "
            "Run end-to-end testing (backend + frontend together). "
            "Performance testing (verify polling doesn't overload)."
        ),
        priority="high",
        tags=["testing", "quality", "integration"],
        due_date=today + timedelta(days=9),
    )
    task7_id = task7.get("id") or task7.get("task_id")
    task_ids.append(task7_id)
    print(f"  ✅ Task 7: {task7_id}")

    task8 = await create_task(
        title="Documentation: Complete guides and deployment",
        description=(
            "Update README with complete setup instructions. "
            "Document API response schemas. "
            "Create quick-start guide for running locally. "
            "Prepare Docker Compose for full-stack deployment."
        ),
        priority="medium",
        tags=["documentation", "deployment"],
        due_date=today + timedelta(days=10),
    )
    task8_id = task8.get("id") or task8.get("task_id")
    task_ids.append(task8_id)
    print(f"  ✅ Task 8: {task8_id}")

    # Store plan summary in semantic memory
    print("\n💾 Storing plan in semantic memory...")
    fact_id = await store(
        content=(
            "Athena Dashboard completion plan: "
            "Phase 2 (3 days) - Replace mock data with real Athena queries, fix notifications. "
            "Phase 3 (5 days) - API integration for all 17 frontend pages and missing endpoints. "
            "Testing & Docs (2 days) - Integration tests, E2E tests, deployment guides. "
            f"Main plan ID: {plan_id}. "
            f"Associated tasks: {', '.join(map(str, task_ids))}"
        ),
        topics=["athena", "dashboard", "planning", "phase2", "phase3", "completion"],
    )
    print(f"✅ Semantic memory fact stored (ID: {fact_id})")

    # Record in episodic memory
    print("\n📝 Recording in episodic memory...")
    event_id = await remember(
        content=(
            f"Created comprehensive Athena Dashboard completion plan using Athena planning system. "
            f"Plan ID: {plan_id}. "
            f"Created 8 prospective tasks for tracking progress. "
            f"Timeline: 10 days total (Phase 2: 3 days, Phase 3: 5 days, Testing: 2 days). "
            f"Task IDs: {', '.join(map(str, task_ids))}"
        ),
        tags=["athena", "dashboard", "planning", "project-management"],
        importance=0.95,
    )
    print(f"✅ Episodic event recorded (ID: {event_id})")

    # Summary
    print("\n" + "=" * 60)
    print("🎯 Dashboard Completion Plan Created Successfully!")
    print("=" * 60)
    print(f"\n📌 Main Plan ID: {plan_id}")
    print(f"📌 Associated Tasks ({len(task_ids)}):")
    for i, task_id in enumerate(task_ids, 1):
        print(f"   {i}. {task_id}")
    print(f"\n📌 Semantic Memory Fact ID: {fact_id}")
    print(f"📌 Episodic Event ID: {event_id}")
    print("\n✨ Plan is now tracked in Athena memory system!")
    print("   - Progress can be monitored via prospective tasks")
    print("   - Plan details available through planning operations")
    print("   - Summary stored in semantic memory for reference")

    await db.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Create Athena Dashboard completion plan using the planning_bridge.

This script uses the planning bridge to create a plan and associated tasks
for completing the Athena Dashboard.

Run with: python create_plan.py
"""

import sys
import os
from datetime import datetime, timedelta

# Add hooks lib to path
sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from planning_bridge import create_plan, create_task, list_tasks
except ImportError as e:
    print(f"Error importing planning_bridge: {e}")
    print("Make sure planning_bridge.py is in /home/user/.claude/hooks/lib/")
    sys.exit(1)


def main():
    """Create dashboard completion plan."""
    print("🚀 Creating Athena Dashboard Completion Plan...")
    print("-" * 60)

    # Create the main plan
    plan = create_plan(
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

    if "error" in plan:
        print(f"❌ Failed to create plan: {plan['error']}")
        return

    plan_id = plan.get("id")
    print(f"✅ Main plan created (ID: {plan_id})")
    print(f"   Goal: {plan.get('goal')}")
    print(f"   Depth: {plan.get('depth')}")

    # Create prospective tasks for major milestones
    task_ids = []
    today = datetime.now()

    print("\n📋 Creating Phase 2 tasks (Real-time Updates)...")

    # Phase 2: Real-time Updates (3 days)
    task1 = create_task(
        title="Phase 2A: Replace mock data with real Athena queries",
        description=(
            "Replace TaskPollingService mock data with real Athena stores queries. "
            "Implement task predictions using Athena prospective layer. "
            "Wire up dependency tracking from Athena knowledge graph."
        ),
        priority="high",
        due_date=today + timedelta(days=3),
        estimated_effort_hours=12,
    )
    if "error" not in task1:
        task_ids.append(task1.get("id"))
        print(f"  ✅ Task 1: {task1.get('id')}")

    task2 = create_task(
        title="Phase 2B: Fix email notification integration",
        description=(
            "Complete email notification service integration with SendGrid or AWS SES. "
            "Test notification delivery for task updates."
        ),
        priority="medium",
        due_date=today + timedelta(days=3),
        estimated_effort_hours=8,
    )
    if "error" not in task2:
        task_ids.append(task2.get("id"))
        print(f"  ✅ Task 2: {task2.get('id')}")

    # Phase 3: Frontend Integration (5 days)
    print("\n📋 Creating Phase 3 tasks (Frontend Integration)...")

    task3 = create_task(
        title="Phase 3A: Implement missing backend endpoints",
        description=(
            "Implement remaining backend endpoints: /api/load/history, "
            "/api/learning/strategies, /api/analysis/* (critical path, bottlenecks, anomalies). "
            "Replace all placeholder data returns with real queries."
        ),
        priority="high",
        due_date=today + timedelta(days=5),
        estimated_effort_hours=16,
    )
    if "error" not in task3:
        task_ids.append(task3.get("id"))
        print(f"  ✅ Task 3: {task3.get('id')}")

    task4 = create_task(
        title="Phase 3B: API integration for Overview and Health pages",
        description=(
            "Connect OverviewPage to /api/system/overview. "
            "Connect SystemHealthPage to /api/system/health. "
            "Implement loading states, error boundaries, data refresh."
        ),
        priority="high",
        due_date=today + timedelta(days=6),
        estimated_effort_hours=10,
    )
    if "error" not in task4:
        task_ids.append(task4.get("id"))
        print(f"  ✅ Task 4: {task4.get('id')}")

    task5 = create_task(
        title="Phase 3C: API integration for memory pages",
        description=(
            "Connect EpisodicMemoryPage to /api/episodic/events. "
            "Connect SemanticMemoryPage to /api/semantic/search. "
            "Connect ProceduralMemoryPage to /api/procedural/skills. "
            "Connect ProspectiveMemoryPage to /api/prospective/tasks."
        ),
        priority="high",
        due_date=today + timedelta(days=7),
        estimated_effort_hours=14,
    )
    if "error" not in task5:
        task_ids.append(task5.get("id"))
        print(f"  ✅ Task 5: {task5.get('id')}")

    task6 = create_task(
        title="Phase 3D: API integration for advanced pages",
        description=(
            "Connect KnowledgeGraphPage to /api/graph/stats. "
            "Connect MetaMemoryPage to /api/meta/quality. "
            "Connect ConsolidationPage to /api/consolidation/analytics. "
            "Connect HookExecutionPage, WorkingMemoryPage, RAGPlanningPage, "
            "LearningAnalyticsPage, PerformanceMonitoringPage, ResearchPage, SettingsPage."
        ),
        priority="high",
        due_date=today + timedelta(days=8),
        estimated_effort_hours=18,
    )
    if "error" not in task6:
        task_ids.append(task6.get("id"))
        print(f"  ✅ Task 6: {task6.get('id')}")

    # Testing & Documentation (2 days)
    print("\n📋 Creating Testing & Documentation tasks...")

    task7 = create_task(
        title="Testing Phase: Integration and E2E tests",
        description=(
            "Write integration tests for backend API endpoints. "
            "Test frontend page data rendering with real API responses. "
            "Run end-to-end testing (backend + frontend together). "
            "Performance testing (verify polling doesn't overload)."
        ),
        priority="high",
        due_date=today + timedelta(days=9),
        estimated_effort_hours=12,
    )
    if "error" not in task7:
        task_ids.append(task7.get("id"))
        print(f"  ✅ Task 7: {task7.get('id')}")

    task8 = create_task(
        title="Documentation: Complete guides and deployment",
        description=(
            "Update README with complete setup instructions. "
            "Document API response schemas. "
            "Create quick-start guide for running locally. "
            "Prepare Docker Compose for full-stack deployment."
        ),
        priority="medium",
        due_date=today + timedelta(days=10),
        estimated_effort_hours=8,
    )
    if "error" not in task8:
        task_ids.append(task8.get("id"))
        print(f"  ✅ Task 8: {task8.get('id')}")

    # Summary
    print("\n" + "=" * 60)
    print("🎯 Dashboard Completion Plan Created Successfully!")
    print("=" * 60)
    print(f"\n📌 Main Plan ID: {plan_id}")
    print(f"📌 Associated Tasks ({len(task_ids)}):")
    for i, task_id in enumerate(task_ids, 1):
        print(f"   {i}. {task_id}")

    # Show current tasks
    print("\n📋 All Tasks in System:")
    all_tasks = list_tasks(limit=20)
    for task in all_tasks[:5]:
        print(f"   - {task['title']} (ID: {task['id']}, Status: {task['status']})")

    print("\n✨ Plan is now tracked in Athena prospective memory!")
    print("   - Tasks can be monitored through list_tasks()")
    print("   - Progress tracked via task status updates")
    print("   - Plan integrated with Athena planning system")
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

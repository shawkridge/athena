"""Unit tests for episodic memory benchmark framework."""

import pytest
from datetime import datetime, timedelta
import tempfile
import json

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore
from athena.projects.manager import ProjectManager
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.consolidation.system import ConsolidationSystem
from athena.manager import UnifiedMemoryManager

from benchmarks.episodic_benchmark import (
    EpisodicMemoryBenchmark,
    BenchmarkQuery,
    BenchmarkResult,
    BenchmarkReport
)


@pytest.fixture
def test_manager(tmp_path):
    """Create test memory manager."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)

    semantic_store = MemoryStore(db_path)
    project_manager = ProjectManager(semantic_store)
    episodic_store = EpisodicStore(db)
    procedural_store = ProceduralStore(db)
    prospective_store = ProspectiveStore(db)
    graph_store = GraphStore(db)
    meta_store = MetaMemoryStore(db)
    consolidation = ConsolidationSystem(
        db, semantic_store, episodic_store, procedural_store, meta_store
    )

    manager = UnifiedMemoryManager(
        semantic=semantic_store,
        episodic=episodic_store,
        procedural=procedural_store,
        prospective=prospective_store,
        graph=graph_store,
        meta=meta_store,
        consolidation=consolidation,
        project_manager=project_manager,
    )

    # Create test project
    project = project_manager.get_or_create_project()

    # Add some test events
    events = [
        EpisodicEvent(
            project_id=project.id,
            session_id="test",
            timestamp=datetime.now() - timedelta(days=1),
            event_type=EventType.ACTION,
            content="Fixed authentication bug in login system",
            context=EventContext(cwd="/src/auth", files=["login.py"])
        ),
        EpisodicEvent(
            project_id=project.id,
            session_id="test",
            timestamp=datetime.now() - timedelta(hours=12),
            event_type=EventType.ACTION,
            content="Implemented database migration for user table",
            context=EventContext(cwd="/src/db", files=["migrations/001.sql"])
        ),
        EpisodicEvent(
            project_id=project.id,
            session_id="test",
            timestamp=datetime.now() - timedelta(hours=2),
            event_type=EventType.ERROR,
            content="Deployment failed due to missing environment variable",
            context=EventContext(cwd="/deploy", files=["config.yml"])
        ),
    ]

    for event in events:
        episodic_store.record_event(event)

    return manager, episodic_store


def test_benchmark_query_creation():
    """Test creating benchmark queries."""
    query = BenchmarkQuery(
        query="What happened yesterday?",
        query_type="temporal",
        ground_truth_event_ids=[1, 2, 3],
        difficulty="easy"
    )

    assert query.query == "What happened yesterday?"
    assert query.query_type == "temporal"
    assert len(query.ground_truth_event_ids) == 3
    assert query.difficulty == "easy"


def test_benchmark_initialization(test_manager):
    """Test benchmark initialization."""
    manager, _ = test_manager

    benchmark = EpisodicMemoryBenchmark(manager)

    assert benchmark.memory_manager == manager
    assert len(benchmark.queries) == 0
    assert 'GPT-4' in benchmark.BASELINES


def test_benchmark_create_queries(test_manager):
    """Test creating queries programmatically."""
    manager, _ = test_manager

    benchmark = EpisodicMemoryBenchmark(manager)

    queries = [
        BenchmarkQuery(
            query="test query 1",
            query_type="temporal",
            ground_truth_event_ids=[1]
        ),
        BenchmarkQuery(
            query="test query 2",
            query_type="spatial",
            ground_truth_event_ids=[2]
        ),
    ]

    benchmark.create_queries(queries)

    assert len(benchmark.queries) == 2
    assert benchmark.queries[0].query == "test query 1"


def test_benchmark_load_queries(test_manager, tmp_path):
    """Test loading queries from JSON."""
    manager, _ = test_manager

    # Create test queries file
    queries_data = {
        "queries": [
            {
                "query": "test query",
                "type": "temporal",
                "ground_truth": [1, 2],
                "difficulty": "easy"
            }
        ]
    }

    queries_file = tmp_path / "test_queries.json"
    with open(queries_file, 'w') as f:
        json.dump(queries_data, f)

    # Load queries
    benchmark = EpisodicMemoryBenchmark(manager)
    benchmark.load_queries(str(queries_file))

    assert len(benchmark.queries) == 1
    assert benchmark.queries[0].query == "test query"
    assert benchmark.queries[0].ground_truth_event_ids == [1, 2]


def test_calculate_metrics():
    """Test metric calculation."""
    manager = None  # Not needed for this test
    benchmark = EpisodicMemoryBenchmark(manager)

    # Perfect match
    metrics = benchmark._calculate_metrics([1, 2, 3], [1, 2, 3])
    assert metrics['precision'] == 1.0
    assert metrics['recall'] == 1.0
    assert metrics['f1'] == 1.0

    # Partial match
    metrics = benchmark._calculate_metrics([1, 2], [1, 2, 3])
    assert metrics['precision'] == 1.0  # All predicted are correct
    assert metrics['recall'] == pytest.approx(2/3)  # Found 2 out of 3
    assert metrics['f1'] == pytest.approx(2 * 1.0 * (2/3) / (1.0 + 2/3))

    # No match
    metrics = benchmark._calculate_metrics([1, 2], [3, 4])
    assert metrics['precision'] == 0.0
    assert metrics['recall'] == 0.0
    assert metrics['f1'] == 0.0


def test_benchmark_run_single_query(test_manager):
    """Test running a single benchmark query."""
    manager, episodic_store = test_manager

    # Get event IDs from database
    recent_events = episodic_store.get_recent_events(project_id=1, limit=3)
    event_ids = [e.id for e in recent_events]

    # Create query
    query = BenchmarkQuery(
        query="Show me authentication events",
        query_type="contextual",
        ground_truth_event_ids=[event_ids[0]],  # First event is auth-related
        difficulty="medium"
    )

    benchmark = EpisodicMemoryBenchmark(manager)
    result = benchmark._evaluate_query(query)

    assert isinstance(result, BenchmarkResult)
    assert result.query == query.query
    assert result.query_type == "contextual"
    assert result.retrieval_time_ms > 0
    assert 0 <= result.precision <= 1.0
    assert 0 <= result.recall <= 1.0
    assert 0 <= result.f1_score <= 1.0


def test_benchmark_full_run(test_manager):
    """Test running full benchmark."""
    manager, episodic_store = test_manager

    # Get event IDs
    recent_events = episodic_store.get_recent_events(project_id=1, limit=3)
    event_ids = [e.id for e in recent_events]

    # Create test queries
    queries = [
        BenchmarkQuery(
            query="authentication",
            query_type="contextual",
            ground_truth_event_ids=[event_ids[0]],
            difficulty="easy"
        ),
        BenchmarkQuery(
            query="database",
            query_type="contextual",
            ground_truth_event_ids=[event_ids[1]],
            difficulty="easy"
        ),
    ]

    benchmark = EpisodicMemoryBenchmark(manager)
    benchmark.create_queries(queries)

    # Run benchmark
    report = benchmark.run_benchmark(verbose=False)

    assert isinstance(report, BenchmarkReport)
    assert report.overall_precision >= 0
    assert report.overall_recall >= 0
    assert report.overall_f1 >= 0
    assert len(report.individual_results) == 2
    assert 'contextual' in report.by_type
    assert 'easy' in report.by_difficulty


def test_benchmark_report_formatting(test_manager):
    """Test benchmark report string formatting."""
    manager, _ = test_manager

    report = BenchmarkReport(
        run_id="test_run",
        timestamp=datetime.now(),
        overall_precision=0.85,
        overall_recall=0.80,
        overall_f1=0.825,
        avg_retrieval_time_ms=45.5,
        by_type={
            'temporal': {'precision': 0.9, 'recall': 0.85, 'f1': 0.875}
        },
        baselines={'GPT-4': 0.32}
    )

    report_str = str(report)

    assert "EPISODIC MEMORY BENCHMARK RESULTS" in report_str
    assert "Precision: 85.00%" in report_str
    assert "Recall: 80.00%" in report_str
    assert "F1 Score: 82.50%" in report_str
    assert "GPT-4" in report_str


def test_benchmark_save_results(test_manager, tmp_path):
    """Test saving benchmark results to JSON."""
    manager, _ = test_manager

    report = BenchmarkReport(
        run_id="test_run",
        timestamp=datetime.now(),
        overall_precision=0.85,
        overall_recall=0.80,
        overall_f1=0.825,
        avg_retrieval_time_ms=45.5
    )

    benchmark = EpisodicMemoryBenchmark(manager)
    output_file = tmp_path / "results.json"

    benchmark.save_results(report, str(output_file))

    # Verify file was created and contains correct data
    assert output_file.exists()

    with open(output_file) as f:
        data = json.load(f)

    assert data['run_id'] == "test_run"
    assert data['overall']['f1'] == 0.825
    assert data['overall']['precision'] == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Episodic Memory Benchmark Framework.

Based on Huet et al. 2025 (arXiv:2501.13121) benchmark for evaluating
episodic memory in LLM systems.

Target: F1 > 0.80 (vs GPT-4: 0.32, Claude-3.5: 0.35, Llama-3.1: 0.29)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import time


@dataclass
class BenchmarkQuery:
    """Single benchmark test case."""

    query: str
    query_type: str  # temporal, spatial, contextual, causal
    ground_truth_event_ids: List[int]
    spatial_context: Optional[str] = None
    temporal_context: Optional[datetime] = None
    difficulty: str = "medium"  # easy, medium, hard
    description: str = ""


@dataclass
class BenchmarkResult:
    """Results for a single query."""

    query: str
    query_type: str
    predicted_event_ids: List[int]
    ground_truth_event_ids: List[int]

    precision: float
    recall: float
    f1_score: float

    retrieval_time_ms: float
    difficulty: str = "medium"

    def __str__(self) -> str:
        return (
            f"Query: {self.query[:50]}...\n"
            f"  P={self.precision:.2%}, R={self.recall:.2%}, F1={self.f1_score:.2%}\n"
            f"  Time: {self.retrieval_time_ms:.1f}ms"
        )


@dataclass
class BenchmarkReport:
    """Complete benchmark run results."""

    run_id: str
    timestamp: datetime

    # Overall metrics
    overall_precision: float
    overall_recall: float
    overall_f1: float
    avg_retrieval_time_ms: float

    # By query type
    by_type: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # By difficulty
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Individual results
    individual_results: List[BenchmarkResult] = field(default_factory=list)

    # Baseline comparisons
    baselines: Dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        output = [
            "="*80,
            f"EPISODIC MEMORY BENCHMARK RESULTS",
            f"Run ID: {self.run_id}",
            f"Timestamp: {self.timestamp}",
            "="*80,
            "",
            "OVERALL METRICS:",
            f"  Precision: {self.overall_precision:.2%}",
            f"  Recall: {self.overall_recall:.2%}",
            f"  F1 Score: {self.overall_f1:.2%}",
            f"  Avg Retrieval Time: {self.avg_retrieval_time_ms:.1f}ms",
            "",
        ]

        if self.by_type:
            output.extend([
                "BY QUERY TYPE:",
            ])
            for qtype, metrics in self.by_type.items():
                output.append(
                    f"  {qtype.upper():12} - "
                    f"P={metrics['precision']:.2%}, "
                    f"R={metrics['recall']:.2%}, "
                    f"F1={metrics['f1']:.2%}"
                )
            output.append("")

        if self.by_difficulty:
            output.extend([
                "BY DIFFICULTY:",
            ])
            for difficulty, metrics in self.by_difficulty.items():
                output.append(
                    f"  {difficulty.upper():12} - "
                    f"P={metrics['precision']:.2%}, "
                    f"R={metrics['recall']:.2%}, "
                    f"F1={metrics['f1']:.2%}"
                )
            output.append("")

        if self.baselines:
            output.extend([
                "COMPARISON TO BASELINES:",
            ])
            for model, score in self.baselines.items():
                diff = self.overall_f1 - score
                emoji = "✅" if diff > 0 else "❌"
                output.append(f"  {emoji} vs {model:12} - {diff:+.2%} ({score:.2%} → {self.overall_f1:.2%})")
            output.append("")

        output.append("="*80)

        return "\n".join(output)


class EpisodicMemoryBenchmark:
    """Benchmark suite for episodic memory evaluation."""

    # Research baselines from Huet et al. 2025
    BASELINES = {
        'GPT-4': 0.32,
        'Claude-3.5': 0.35,
        'Llama-3.1': 0.29,
        'o1-mini': 0.28,
    }

    def __init__(self, memory_manager):
        """Initialize benchmark with memory manager.

        Args:
            memory_manager: UnifiedMemoryManager instance
        """
        self.memory_manager = memory_manager
        self.queries: List[BenchmarkQuery] = []

    def load_queries(self, path: str):
        """Load benchmark queries from JSON file.

        Args:
            path: Path to JSON file with benchmark queries
        """
        with open(path, 'r') as f:
            data = json.load(f)

        self.queries = []
        for item in data['queries']:
            query = BenchmarkQuery(
                query=item['query'],
                query_type=item['type'],
                ground_truth_event_ids=item['ground_truth'],
                spatial_context=item.get('spatial_context'),
                temporal_context=datetime.fromisoformat(item['temporal_context'])
                    if item.get('temporal_context') else None,
                difficulty=item.get('difficulty', 'medium'),
                description=item.get('description', '')
            )
            self.queries.append(query)

        print(f"✓ Loaded {len(self.queries)} benchmark queries from {path}")

    def create_queries(self, queries: List[BenchmarkQuery]):
        """Create queries programmatically.

        Args:
            queries: List of BenchmarkQuery objects
        """
        self.queries = queries
        print(f"✓ Created {len(self.queries)} benchmark queries")

    def run_benchmark(self, verbose: bool = True) -> BenchmarkReport:
        """Run full benchmark suite.

        Args:
            verbose: Print progress during benchmark

        Returns:
            BenchmarkReport with complete results
        """
        if not self.queries:
            raise ValueError("No queries loaded. Use load_queries() or create_queries() first.")

        if verbose:
            print(f"\n{'='*80}")
            print(f"Running Episodic Memory Benchmark")
            print(f"Total queries: {len(self.queries)}")
            print(f"{'='*80}\n")

        results = []

        for i, query in enumerate(self.queries, 1):
            if verbose:
                print(f"[{i}/{len(self.queries)}] {query.query_type}: {query.query[:60]}...")

            result = self._evaluate_query(query)
            results.append(result)

            if verbose:
                print(f"  → F1={result.f1_score:.2%}, Time={result.retrieval_time_ms:.1f}ms")

        # Generate report
        report = self._generate_report(results)

        if verbose:
            print(f"\n{report}")

        return report

    def _evaluate_query(self, query: BenchmarkQuery) -> BenchmarkResult:
        """Evaluate a single query.

        Args:
            query: Benchmark query

        Returns:
            BenchmarkResult with metrics
        """
        start = time.time()

        # Build context
        context = {}
        if query.spatial_context:
            context['cwd'] = query.spatial_context
        if query.temporal_context:
            context['temporal_hint'] = query.temporal_context

        # Execute query through memory manager
        try:
            retrieved = self.memory_manager.retrieve(
                query=query.query,
                context=context,
                k=10
            )
        except Exception as e:
            import traceback
            print(f"  ⚠️ Query failed: {e}")
            print(f"     Traceback: {traceback.format_exc()}")
            retrieved = {}

        retrieval_time_ms = (time.time() - start) * 1000

        # Extract event IDs from results
        predicted_ids = self._extract_event_ids(retrieved)

        # Calculate metrics
        metrics = self._calculate_metrics(
            predicted_ids,
            query.ground_truth_event_ids
        )

        return BenchmarkResult(
            query=query.query,
            query_type=query.query_type,
            predicted_event_ids=predicted_ids,
            ground_truth_event_ids=query.ground_truth_event_ids,
            precision=metrics['precision'],
            recall=metrics['recall'],
            f1_score=metrics['f1'],
            retrieval_time_ms=retrieval_time_ms,
            difficulty=query.difficulty
        )

    def _extract_event_ids(self, retrieved: dict) -> List[int]:
        """Extract event IDs from retrieval results.

        Args:
            retrieved: Results from memory_manager.retrieve()

        Returns:
            List of event IDs
        """
        event_ids = []

        # Check episodic results
        if 'episodic' in retrieved:
            for event in retrieved['episodic']:
                if isinstance(event, dict) and 'event_id' in event:
                    event_ids.append(event['event_id'])
                elif hasattr(event, 'id'):
                    event_ids.append(event.id)

        return event_ids

    def _calculate_metrics(
        self,
        predicted: List[int],
        ground_truth: List[int]
    ) -> Dict[str, float]:
        """Calculate precision, recall, F1.

        Args:
            predicted: Predicted event IDs
            ground_truth: Ground truth event IDs

        Returns:
            Dictionary with precision, recall, f1
        """
        if not ground_truth:
            return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}

        predicted_set = set(predicted)
        ground_truth_set = set(ground_truth)

        true_positives = len(predicted_set & ground_truth_set)
        false_positives = len(predicted_set - ground_truth_set)
        false_negatives = len(ground_truth_set - predicted_set)

        precision = true_positives / len(predicted_set) if predicted_set else 0.0
        recall = true_positives / len(ground_truth_set) if ground_truth_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    def _generate_report(self, results: List[BenchmarkResult]) -> BenchmarkReport:
        """Generate benchmark report from results.

        Args:
            results: List of BenchmarkResult objects

        Returns:
            BenchmarkReport with aggregated metrics
        """
        # Overall metrics
        avg_precision = sum(r.precision for r in results) / len(results)
        avg_recall = sum(r.recall for r in results) / len(results)
        avg_f1 = sum(r.f1_score for r in results) / len(results)
        avg_time = sum(r.retrieval_time_ms for r in results) / len(results)

        # By query type
        by_type = {}
        for qtype in set(r.query_type for r in results):
            type_results = [r for r in results if r.query_type == qtype]
            by_type[qtype] = {
                'precision': sum(r.precision for r in type_results) / len(type_results),
                'recall': sum(r.recall for r in type_results) / len(type_results),
                'f1': sum(r.f1_score for r in type_results) / len(type_results),
                'count': len(type_results)
            }

        # By difficulty
        by_difficulty = {}
        for difficulty in set(r.difficulty for r in results):
            diff_results = [r for r in results if r.difficulty == difficulty]
            by_difficulty[difficulty] = {
                'precision': sum(r.precision for r in diff_results) / len(diff_results),
                'recall': sum(r.recall for r in diff_results) / len(diff_results),
                'f1': sum(r.f1_score for r in diff_results) / len(diff_results),
                'count': len(diff_results)
            }

        return BenchmarkReport(
            run_id=f"benchmark_{int(time.time())}",
            timestamp=datetime.now(),
            overall_precision=avg_precision,
            overall_recall=avg_recall,
            overall_f1=avg_f1,
            avg_retrieval_time_ms=avg_time,
            by_type=by_type,
            by_difficulty=by_difficulty,
            individual_results=results,
            baselines=self.BASELINES
        )

    def save_results(self, report: BenchmarkReport, path: str):
        """Save benchmark results to JSON.

        Args:
            report: BenchmarkReport to save
            path: Output file path
        """
        data = {
            'run_id': report.run_id,
            'timestamp': report.timestamp.isoformat(),
            'overall': {
                'precision': report.overall_precision,
                'recall': report.overall_recall,
                'f1': report.overall_f1,
                'avg_retrieval_time_ms': report.avg_retrieval_time_ms
            },
            'by_type': report.by_type,
            'by_difficulty': report.by_difficulty,
            'baselines': report.baselines,
            'results': [
                {
                    'query': r.query,
                    'query_type': r.query_type,
                    'predicted_event_ids': r.predicted_event_ids,
                    'ground_truth_event_ids': r.ground_truth_event_ids,
                    'precision': r.precision,
                    'recall': r.recall,
                    'f1_score': r.f1_score,
                    'retrieval_time_ms': r.retrieval_time_ms,
                    'difficulty': r.difficulty
                }
                for r in report.individual_results
            ]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n✓ Results saved to {path}")

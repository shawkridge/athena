"""Unit tests for Planning Validation Benchmarks.

Tests planning validation against GPQA, GSM8K, and MBPP benchmarks.
Validates F1 score computation and benchmark execution.
"""

import pytest
from unittest.mock import MagicMock

from athena.planning.validation_benchmark import (
    PlanningValidationBenchmark,
    BenchmarkQuestion,
    ValidationResult,
    BenchmarkResult,
)


class TestBenchmarkQuestion:
    """Test BenchmarkQuestion dataclass."""

    def test_benchmark_question_creation(self):
        """Test creating a benchmark question."""
        question = BenchmarkQuestion(
            question_id="gpqa_0001",
            benchmark="GPQA",
            question_text="What is the mechanism of action?",
            correct_answer="answer_0",
            difficulty="graduate",
            category="biology",
        )

        assert question.question_id == "gpqa_0001"
        assert question.benchmark == "GPQA"
        assert question.difficulty == "graduate"
        assert question.category == "biology"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_valid(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            is_valid=True,
            quality_score=0.95,
            validation_time_ms=45.3,
            reasons=["Structure correct", "Steps feasible"],
        )

        assert result.is_valid is True
        assert result.quality_score == 0.95
        assert len(result.reasons) == 2

    def test_validation_result_invalid(self):
        """Test creating an invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            quality_score=0.3,
            validation_time_ms=30.0,
            reasons=["Missing steps"],
        )

        assert result.is_valid is False
        assert result.quality_score == 0.3


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_benchmark_result_structure(self):
        """Test BenchmarkResult structure."""
        result = BenchmarkResult(
            benchmark_name="GPQA",
            sample_count=50,
            answer_accuracy=0.82,
            validation_accuracy=0.88,
            validation_precision=0.90,
            validation_recall=0.85,
            validation_f1=0.875,
            avg_validation_time_ms=42.5,
            target_f1=0.85,
        )

        assert result.benchmark_name == "GPQA"
        assert result.validation_f1 >= result.target_f1
        assert result.sample_count == 50


class TestPlanningValidationBenchmark:
    """Test PlanningValidationBenchmark class."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        store = MagicMock()
        # Mock validate_plan to return valid results
        store.validate_plan.return_value = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            validation_time_ms=40.0,
            reasons=["Valid"],
        )
        return store

    @pytest.fixture
    def benchmark(self, mock_planning_store):
        """Create PlanningValidationBenchmark instance."""
        return PlanningValidationBenchmark(mock_planning_store)

    def test_benchmark_initialization(self, benchmark):
        """Test benchmark initialization."""
        assert benchmark.planning_store is not None
        assert benchmark.llm_client is None
        assert benchmark.results == []

    def test_load_gpqa_dataset(self, benchmark):
        """Test loading GPQA dataset."""
        questions = benchmark._load_gpqa_dataset(10)

        assert len(questions) == 10
        assert all(q.benchmark == "GPQA" for q in questions)
        assert all(q.difficulty == "graduate" for q in questions)
        assert all(q.question_id.startswith("gpqa_") for q in questions)

    def test_load_gpqa_dataset_respects_size(self, benchmark):
        """Test GPQA loader respects max size."""
        questions = benchmark._load_gpqa_dataset(1000)
        # Max size is 448 for GPQA
        assert len(questions) == 448

    def test_load_gsm8k_dataset(self, benchmark):
        """Test loading GSM8K dataset."""
        questions = benchmark._load_gsm8k_dataset(10)

        assert len(questions) == 10
        assert all(q.benchmark == "GSM8K" for q in questions)
        assert all(q.category == "math" for q in questions)

    def test_load_mbpp_dataset(self, benchmark):
        """Test loading MBPP dataset."""
        questions = benchmark._load_mbpp_dataset(10)

        assert len(questions) == 10
        assert all(q.benchmark == "MBPP" for q in questions)
        assert all(q.category == "python" for q in questions)

    def test_infer_reasoning_type_gpqa(self, benchmark):
        """Test reasoning type inference for GPQA."""
        question = BenchmarkQuestion(
            question_id="test",
            benchmark="GPQA",
            question_text="What is...?",
            correct_answer="answer",
            difficulty="graduate",
        )

        reasoning_type = benchmark._infer_reasoning_type(question)
        assert reasoning_type == "analytical"

    def test_infer_reasoning_type_gsm8k(self, benchmark):
        """Test reasoning type inference for GSM8K."""
        question = BenchmarkQuestion(
            question_id="test",
            benchmark="GSM8K",
            question_text="If there are 5 apples...",
            correct_answer="10",
            difficulty="medium",
        )

        reasoning_type = benchmark._infer_reasoning_type(question)
        assert reasoning_type == "mathematical"

    def test_infer_reasoning_type_mbpp(self, benchmark):
        """Test reasoning type inference for MBPP."""
        question = BenchmarkQuestion(
            question_id="test",
            benchmark="MBPP",
            question_text="Write a function...",
            correct_answer="def solution(): pass",
            difficulty="medium",
        )

        reasoning_type = benchmark._infer_reasoning_type(question)
        assert reasoning_type == "code"

    def test_create_answer_plan(self, benchmark):
        """Test creating an answer plan."""
        question = BenchmarkQuestion(
            question_id="test_1",
            benchmark="GPQA",
            question_text="What is the mechanism?",
            correct_answer="answer_0",
            difficulty="graduate",
        )

        plan = benchmark._create_answer_plan(question)

        assert plan["question_id"] == "test_1"
        assert plan["benchmark"] == "GPQA"
        assert len(plan["steps"]) >= 3
        assert "reasoning_type" in plan
        assert "success_criteria" in plan

    def test_execute_plan_without_llm(self, benchmark):
        """Test executing plan without LLM (heuristic)."""
        question = BenchmarkQuestion(
            question_id="test",
            benchmark="GPQA",
            question_text="What is the mechanism of...",
            correct_answer="answer_0",
            difficulty="graduate",
        )

        plan = benchmark._create_answer_plan(question)
        answer = benchmark._execute_plan(plan, question)

        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_check_math_answer_correct(self, benchmark):
        """Test checking correct math answer."""
        is_correct = benchmark._check_math_answer("42", "42")
        assert is_correct is True

    def test_check_math_answer_incorrect(self, benchmark):
        """Test checking incorrect math answer."""
        is_correct = benchmark._check_math_answer("41", "42")
        assert is_correct is False

    def test_check_math_answer_float(self, benchmark):
        """Test checking math answer with floats."""
        is_correct = benchmark._check_math_answer("3.14", "3.14")
        assert is_correct is True

    def test_check_code_answer_valid(self, benchmark):
        """Test checking valid Python code."""
        code = "def solution(x):\n    return x"
        question = BenchmarkQuestion(
            question_id="test",
            benchmark="MBPP",
            question_text="Write a function",
            correct_answer=code,
            difficulty="easy",
        )

        is_correct = benchmark._check_code_answer(code, question)
        assert is_correct is True

    def test_check_code_answer_invalid_syntax(self, benchmark):
        """Test checking invalid Python code."""
        code = "def solution(x)\n    return x"  # Missing colon
        question = BenchmarkQuestion(
            question_id="test",
            benchmark="MBPP",
            question_text="Write a function",
            correct_answer="def solution(x):\n    return x",
            difficulty="easy",
        )

        is_correct = benchmark._check_code_answer(code, question)
        assert is_correct is False

    def test_compute_f1_metrics_all_correct(self, benchmark):
        """Test F1 computation when validation and answers all correct."""
        results = [
            {
                "question_id": "q1",
                "validation_passed": True,
                "answer_correct": True,
                "validation_time_ms": 40.0,
            },
            {
                "question_id": "q2",
                "validation_passed": True,
                "answer_correct": True,
                "validation_time_ms": 45.0,
            },
        ]

        metrics = benchmark._compute_f1_metrics(
            results=results,
            benchmark_name="TEST",
            sample_count=2,
        )

        assert metrics.answer_accuracy == 1.0
        assert metrics.validation_accuracy == 1.0
        assert metrics.validation_f1 == 1.0
        assert metrics.validation_precision == 1.0
        assert metrics.validation_recall == 1.0

    def test_compute_f1_metrics_mixed(self, benchmark):
        """Test F1 computation with mixed results."""
        results = [
            {
                "question_id": "q1",
                "validation_passed": True,
                "answer_correct": True,
                "validation_time_ms": 40.0,
            },
            {
                "question_id": "q2",
                "validation_passed": True,
                "answer_correct": False,
                "validation_time_ms": 45.0,
            },
            {
                "question_id": "q3",
                "validation_passed": False,
                "answer_correct": True,
                "validation_time_ms": 35.0,
            },
            {
                "question_id": "q4",
                "validation_passed": False,
                "answer_correct": False,
                "validation_time_ms": 38.0,
            },
        ]

        metrics = benchmark._compute_f1_metrics(
            results=results,
            benchmark_name="TEST",
            sample_count=4,
        )

        # TP = 1, FP = 1, FN = 1
        # precision = 1 / (1 + 1) = 0.5
        # recall = 1 / (1 + 1) = 0.5
        # f1 = 2 * (0.5 * 0.5) / (0.5 + 0.5) = 0.5
        assert metrics.validation_f1 == 0.5
        assert metrics.validation_precision == 0.5
        assert metrics.validation_recall == 0.5

    def test_run_gpqa_benchmark(self, benchmark, mock_planning_store):
        """Test running GPQA benchmark."""
        # Mock planning store
        mock_planning_store.validate_plan.return_value = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            validation_time_ms=40.0,
        )

        result = benchmark.run_gpqa_benchmark(sample_size=10)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "GPQA"
        assert result.sample_count == 10
        assert 0.0 <= result.validation_f1 <= 1.0

    def test_run_gsm8k_benchmark(self, benchmark, mock_planning_store):
        """Test running GSM8K benchmark."""
        mock_planning_store.validate_plan.return_value = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            validation_time_ms=40.0,
        )

        result = benchmark.run_gsm8k_benchmark(sample_size=10)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "GSM8K"
        assert result.sample_count == 10

    def test_run_mbpp_benchmark(self, benchmark, mock_planning_store):
        """Test running MBPP benchmark."""
        mock_planning_store.validate_plan.return_value = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            validation_time_ms=40.0,
        )

        result = benchmark.run_mbpp_benchmark(sample_size=10)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "MBPP"
        assert result.sample_count == 10

    def test_run_all_benchmarks(self, benchmark, mock_planning_store):
        """Test running all benchmarks together."""
        mock_planning_store.validate_plan.return_value = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            validation_time_ms=40.0,
        )

        results = benchmark.run_all_benchmarks(
            gpqa_size=10, gsm8k_size=10, mbpp_size=10
        )

        assert "GPQA" in results
        assert "GSM8K" in results
        assert "MBPP" in results
        assert "aggregate" in results

        # Check aggregate metrics
        aggregate = results["aggregate"]
        assert "mean_f1" in aggregate
        assert "min_f1" in aggregate
        assert "max_f1" in aggregate
        assert "all_benchmarks_pass" in aggregate

    def test_validation_result_f1_measurement(self, benchmark, mock_planning_store):
        """Test that F1 score measures validation quality correctly.

        F1 should be high when:
        - Validation is correct (valid/invalid matches answer correctness)

        F1 should be low when:
        - Validation is wrong (valid but answer wrong, or invalid but answer right)
        """
        # Scenario: Good validation (1 TP, 0 FP, 0 FN)
        results_good = [
            {
                "question_id": f"q{i}",
                "validation_passed": True,
                "answer_correct": True,
                "validation_time_ms": 40.0,
            }
            for i in range(10)
        ]

        metrics_good = benchmark._compute_f1_metrics(
            results=results_good,
            benchmark_name="GOOD",
            sample_count=10,
        )

        # Scenario: Bad validation (all predictions wrong)
        results_bad = [
            {
                "question_id": f"q{i}",
                "validation_passed": True,
                "answer_correct": False,
                "validation_time_ms": 40.0,
            }
            for i in range(10)
        ]

        metrics_bad = benchmark._compute_f1_metrics(
            results=results_bad,
            benchmark_name="BAD",
            sample_count=10,
        )

        # Good validation should have higher F1
        assert metrics_good.validation_f1 > metrics_bad.validation_f1
        assert metrics_good.validation_f1 == 1.0
        assert metrics_bad.validation_f1 == 0.0

    def test_benchmark_f1_target(self, benchmark):
        """Test that benchmark target F1 is 0.85."""
        assert benchmark._compute_f1_metrics(
            results=[],
            benchmark_name="TEST",
            sample_count=0,
        ).target_f1 == 0.85

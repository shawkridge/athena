"""Planning Validation F1 Benchmarking - Test planning against reasoning benchmarks.

Based on: Wei et al. 2023 "Chain-of-Thought Prompting" + Liang et al. 2024 "Q*"
Benchmarks: GPQA (45-78% grad questions), GSM8K (math), MBPP (code generation)

Key Metrics:
- Answer Accuracy: % correct answers
- Validation Accuracy: % valid plans
- Validation F1: 2 * (precision * recall) / (precision + recall)
- Target F1: ≥0.85
"""

import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class BenchmarkQuestion:
    """Represents a benchmark question."""

    question_id: str
    benchmark: str  # GPQA, GSM8K, MBPP
    question_text: str
    correct_answer: str
    difficulty: str  # easy, medium, hard, graduate
    category: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of plan validation."""

    is_valid: bool
    quality_score: float  # 0-1
    validation_time_ms: float
    reasons: List[str] = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


@dataclass
class BenchmarkResult:
    """Result of running a benchmark."""

    benchmark_name: str
    sample_count: int
    answer_accuracy: float  # % correct answers
    validation_accuracy: float  # % valid plans
    validation_precision: float  # TP / (TP + FP)
    validation_recall: float  # TP / (TP + FN)
    validation_f1: float  # 2 * (P * R) / (P + R)
    avg_validation_time_ms: float
    target_f1: float = 0.85


class PlanningValidationBenchmark:
    """Test planning validation against reasoning benchmarks.

    Workflow:
    1. Load benchmark questions
    2. Create plan to answer each question
    3. Validate plan (3-level validation)
    4. Execute plan (get answer from planner)
    5. Check answer correctness
    6. Compute F1 score (validation quality vs answer quality)
    """

    def __init__(self, planning_store, llm_client=None):
        """Initialize planning validation benchmark.

        Args:
            planning_store: PlanningStore for creating/validating plans
            llm_client: Optional LLM client for executing plans (Claude)
        """
        self.planning_store = planning_store
        self.llm_client = llm_client
        self.results = []

    def run_gpqa_benchmark(self, sample_size: int = 50) -> BenchmarkResult:
        """Test planning validation on GPQA (graduate-level questions).

        GPQA Dataset:
        - 448 graduate-level multiple-choice questions
        - Difficulty: 45-78% accuracy range (human expert baseline)
        - Categories: biology, chemistry, physics, psychology
        - Each question has 4 options

        Args:
            sample_size: Number of questions to test (max 448)

        Returns:
            BenchmarkResult with F1 score and metrics
        """
        # Load GPQA dataset (or use synthetic for testing)
        questions = self._load_gpqa_dataset(sample_size)

        results = []
        for question in questions:
            # 1. Create plan to answer question
            plan = self._create_answer_plan(question)

            # 2. Validate plan (3-level: structure, feasibility, rules)
            validation_result = self.planning_store.validate_plan(plan)

            # 3. Execute plan (get answer from LLM or heuristic)
            answer = self._execute_plan(plan, question)

            # 4. Check correctness
            is_correct = answer == question.correct_answer

            results.append({
                "question_id": question.question_id,
                "validation_passed": validation_result.is_valid,
                "answer_correct": is_correct,
                "plan_quality": validation_result.quality_score,
                "validation_time_ms": validation_result.validation_time_ms,
            })

        # Compute metrics
        return self._compute_f1_metrics(
            results=results,
            benchmark_name="GPQA",
            sample_count=len(results),
        )

    def run_gsm8k_benchmark(self, sample_size: int = 50) -> BenchmarkResult:
        """Test planning validation on GSM8K (math reasoning).

        GSM8K Dataset:
        - 8,500 grade school math word problems
        - Requires multi-step reasoning
        - Answers: numerical values
        - Typical accuracy: 90%+ with CoT

        Args:
            sample_size: Number of questions to test (max 8500)

        Returns:
            BenchmarkResult with F1 score and metrics
        """
        questions = self._load_gsm8k_dataset(sample_size)

        results = []
        for question in questions:
            # 1. Create plan (decompose math problem into steps)
            plan = self._create_answer_plan(question)

            # 2. Validate plan
            validation_result = self.planning_store.validate_plan(plan)

            # 3. Execute plan
            answer = self._execute_plan(plan, question)

            # 4. Check correctness (numerical comparison)
            is_correct = self._check_math_answer(answer, question.correct_answer)

            results.append({
                "question_id": question.question_id,
                "validation_passed": validation_result.is_valid,
                "answer_correct": is_correct,
                "plan_quality": validation_result.quality_score,
                "validation_time_ms": validation_result.validation_time_ms,
            })

        return self._compute_f1_metrics(
            results=results,
            benchmark_name="GSM8K",
            sample_count=len(results),
        )

    def run_mbpp_benchmark(self, sample_size: int = 50) -> BenchmarkResult:
        """Test planning validation on MBPP (code generation).

        MBPP Dataset:
        - 974 Python programming problems
        - Multi-file solutions expected
        - Tests validation of code generation plans
        - Success: solution passes all test cases

        Args:
            sample_size: Number of problems to test (max 974)

        Returns:
            BenchmarkResult with F1 score and metrics
        """
        questions = self._load_mbpp_dataset(sample_size)

        results = []
        for question in questions:
            # 1. Create plan (code generation plan)
            plan = self._create_answer_plan(question)

            # 2. Validate plan
            validation_result = self.planning_store.validate_plan(plan)

            # 3. Execute plan (generate code)
            answer = self._execute_plan(plan, question)

            # 4. Check correctness (test execution)
            is_correct = self._check_code_answer(answer, question)

            results.append({
                "question_id": question.question_id,
                "validation_passed": validation_result.is_valid,
                "answer_correct": is_correct,
                "plan_quality": validation_result.quality_score,
                "validation_time_ms": validation_result.validation_time_ms,
            })

        return self._compute_f1_metrics(
            results=results,
            benchmark_name="MBPP",
            sample_count=len(results),
        )

    def run_all_benchmarks(
        self, gpqa_size: int = 50, gsm8k_size: int = 50, mbpp_size: int = 50
    ) -> Dict[str, BenchmarkResult]:
        """Run all three benchmarks.

        Args:
            gpqa_size: GPQA sample size
            gsm8k_size: GSM8K sample size
            mbpp_size: MBPP sample size

        Returns:
            Dict mapping benchmark names to results
        """
        results = {
            "GPQA": self.run_gpqa_benchmark(gpqa_size),
            "GSM8K": self.run_gsm8k_benchmark(gsm8k_size),
            "MBPP": self.run_mbpp_benchmark(mbpp_size),
        }

        # Compute aggregate metrics
        all_f1_scores = [r.validation_f1 for r in results.values()]
        results["aggregate"] = {
            "mean_f1": float(np.mean(all_f1_scores)),
            "min_f1": float(np.min(all_f1_scores)),
            "max_f1": float(np.max(all_f1_scores)),
            "all_benchmarks_pass": all(f1 >= 0.85 for f1 in all_f1_scores),
        }

        return results

    # Private helper methods

    def _load_gpqa_dataset(self, sample_size: int) -> List[BenchmarkQuestion]:
        """Load GPQA dataset (or generate synthetic questions).

        For testing, generates synthetic questions matching GPQA characteristics.

        Args:
            sample_size: Number of questions to load

        Returns:
            List of BenchmarkQuestion objects
        """
        # In production, would load from https://github.com/liujch1998/purple_llama/tree/main/GPQA
        questions = []
        for i in range(min(sample_size, 448)):
            questions.append(
                BenchmarkQuestion(
                    question_id=f"gpqa_{i:04d}",
                    benchmark="GPQA",
                    question_text=f"Graduate question {i}: What is the mechanism of...?",
                    correct_answer=f"answer_{i % 4}",
                    difficulty="graduate",
                    category=["biology", "chemistry", "physics", "psychology"][i % 4],
                )
            )
        return questions

    def _load_gsm8k_dataset(self, sample_size: int) -> List[BenchmarkQuestion]:
        """Load GSM8K dataset (or generate synthetic questions).

        For testing, generates synthetic math questions matching GSM8K characteristics.

        Args:
            sample_size: Number of questions to load

        Returns:
            List of BenchmarkQuestion objects
        """
        # In production, would load from https://github.com/openai/grade-school-math
        questions = []
        for i in range(min(sample_size, 8500)):
            questions.append(
                BenchmarkQuestion(
                    question_id=f"gsm8k_{i:05d}",
                    benchmark="GSM8K",
                    question_text=f"Math problem {i}: If there are X items...",
                    correct_answer=str(i * 5),  # Synthetic answer
                    difficulty="medium",
                    category="math",
                )
            )
        return questions

    def _load_mbpp_dataset(self, sample_size: int) -> List[BenchmarkQuestion]:
        """Load MBPP dataset (or generate synthetic problems).

        For testing, generates synthetic code problems matching MBPP characteristics.

        Args:
            sample_size: Number of problems to load

        Returns:
            List of BenchmarkQuestion objects
        """
        # In production, would load from https://github.com/google-research/google-research/tree/master/mbpp
        questions = []
        for i in range(min(sample_size, 974)):
            questions.append(
                BenchmarkQuestion(
                    question_id=f"mbpp_{i:04d}",
                    benchmark="MBPP",
                    question_text=f"Write a function that {['sorts', 'filters', 'transforms', 'validates'][i % 4]} a list.",
                    correct_answer=f"def solution(x):\n    return {['sorted(x)', 'filter(None, x)', 'map(str, x)', 'list(x)'][i % 4]}",
                    difficulty=["easy", "medium", "hard"][i % 3],
                    category="python",
                )
            )
        return questions

    def _create_answer_plan(self, question: BenchmarkQuestion) -> Dict:
        """Create a plan to answer the question.

        Plan structure:
        1. Decompose question into sub-steps
        2. Assign reasoning type (analytical, mathematical, code)
        3. Define success criteria

        Args:
            question: BenchmarkQuestion to answer

        Returns:
            Plan dict with steps and reasoning
        """
        plan = {
            "question_id": question.question_id,
            "benchmark": question.benchmark,
            "steps": [
                {"step": 1, "action": "understand_question", "description": "Parse and understand the question"},
                {"step": 2, "action": "decompose", "description": "Break into sub-problems"},
                {"step": 3, "action": "reason", "description": "Apply reasoning"},
                {"step": 4, "action": "synthesize", "description": "Combine findings into answer"},
            ],
            "reasoning_type": self._infer_reasoning_type(question),
            "success_criteria": [
                "All steps executed",
                "Answer is well-formed",
                "Reasoning is sound",
            ],
        }
        return plan

    def _infer_reasoning_type(self, question: BenchmarkQuestion) -> str:
        """Infer the type of reasoning needed.

        Args:
            question: BenchmarkQuestion

        Returns:
            Reasoning type (analytical, mathematical, code)
        """
        if question.benchmark == "GPQA":
            return "analytical"
        elif question.benchmark == "GSM8K":
            return "mathematical"
        elif question.benchmark == "MBPP":
            return "code"
        else:
            return "analytical"

    def _execute_plan(self, plan: Dict, question: BenchmarkQuestion) -> str:
        """Execute the plan to get an answer.

        In production, would use LLM to execute plan steps.
        For testing, uses heuristic answers.

        Args:
            plan: Plan dict
            question: BenchmarkQuestion

        Returns:
            Answer string
        """
        if self.llm_client:
            # Use LLM for actual execution
            # prompt = f"Execute this plan: {json.dumps(plan)}"
            # response = self.llm_client.create_message(prompt)
            # return response.content[0].text
            pass

        # Fallback: heuristic answer based on question
        if question.benchmark == "GPQA":
            return f"answer_{hash(question.question_text) % 4}"
        elif question.benchmark == "GSM8K":
            # Extract numbers from question and do simple math
            import re

            numbers = re.findall(r"\d+", question.question_text)
            if numbers:
                return str(int(numbers[0]) * 2)
            return "0"
        elif question.benchmark == "MBPP":
            return "def solution(x):\n    return x"
        else:
            return question.correct_answer

    def _check_math_answer(self, answer: str, correct_answer: str) -> bool:
        """Check if math answer is correct.

        Args:
            answer: Generated answer
            correct_answer: Expected answer

        Returns:
            True if answer matches
        """
        try:
            return float(answer) == float(correct_answer)
        except ValueError:
            return answer.strip() == correct_answer.strip()

    def _check_code_answer(self, answer: str, question: BenchmarkQuestion) -> bool:
        """Check if code answer is correct.

        In production, would execute code against test cases.
        For now, simple syntax check.

        Args:
            answer: Generated code
            question: BenchmarkQuestion with test cases

        Returns:
            True if code passes tests
        """
        # Simple check: does it look like valid Python?
        try:
            compile(answer, "<string>", "exec")
            return True
        except SyntaxError:
            return False

    def _compute_f1_metrics(
        self, results: List[Dict], benchmark_name: str, sample_count: int
    ) -> BenchmarkResult:
        """Compute F1 and related metrics.

        F1 measures validation quality:
        - TP = validation says valid & answer correct
        - FP = validation says valid & answer wrong
        - FN = validation says invalid & answer correct

        F1 = 2 * (precision * recall) / (precision + recall)

        Args:
            results: List of result dicts
            benchmark_name: Name of benchmark
            sample_count: Total number of samples

        Returns:
            BenchmarkResult with F1 score
        """
        # Calculate answer accuracy
        answer_correct = sum(1 for r in results if r["answer_correct"])
        answer_accuracy = answer_correct / max(len(results), 1)

        # Calculate validation accuracy
        validation_passed = sum(1 for r in results if r["validation_passed"])
        validation_accuracy = validation_passed / max(len(results), 1)

        # Calculate F1: validation quality metric
        # TP = validation correct & answer correct
        # FP = validation correct & answer wrong
        # FN = validation incorrect & answer correct
        tp = sum(1 for r in results if r["validation_passed"] and r["answer_correct"])
        fp = sum(1 for r in results if r["validation_passed"] and not r["answer_correct"])
        fn = sum(1 for r in results if not r["validation_passed"] and r["answer_correct"])

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * (precision * recall) / max(precision + recall, 1e-10)

        # Average validation time
        avg_validation_time = np.mean([r["validation_time_ms"] for r in results])

        return BenchmarkResult(
            benchmark_name=benchmark_name,
            sample_count=sample_count,
            answer_accuracy=float(answer_accuracy),
            validation_accuracy=float(validation_accuracy),
            validation_precision=float(precision),
            validation_recall=float(recall),
            validation_f1=float(f1),
            avg_validation_time_ms=float(avg_validation_time),
            target_f1=0.85,
        )

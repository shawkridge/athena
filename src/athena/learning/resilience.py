"""Resilience & Error Recovery for Learning System.

Ensures learning system continues working even when infrastructure fails:
- Database unavailable: Use in-memory fallback
- LLM servers down: Use heuristic analysis
- Network issues: Retry with exponential backoff
- Data consistency: Validate before storing

Implements graceful degradation and circuit breaker patterns.
"""

from typing import Optional, Dict, Any, TypeVar, Callable
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """Circuit breaker for handling service failures.

    States: CLOSED (working) -> OPEN (failing) -> HALF_OPEN (testing)
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60
    ):
        """Initialize circuit breaker.

        Args:
            service_name: Name of service being protected
            failure_threshold: Failures before opening circuit
            recovery_timeout_seconds: Time before trying again
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)

        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None

    def record_success(self):
        """Record successful call - reset counter."""
        self.failure_count = 0
        if self.state != "CLOSED":
            logger.info(f"Circuit {self.service_name} recovered - CLOSED")
            self.state = "CLOSED"

    def record_failure(self):
        """Record failed call - increment counter."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit {self.service_name} opened after {self.failure_count} failures")
            self.state = "OPEN"

    def is_available(self) -> bool:
        """Check if service is available to call."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = datetime.now() - self.last_failure_time
                if elapsed > self.recovery_timeout:
                    logger.info(f"Circuit {self.service_name} entering HALF_OPEN state")
                    self.state = "HALF_OPEN"
                    return True
            return False

        # HALF_OPEN: try the call
        return True


class ResilientLearningBridge:
    """Wrapper around learning system with resilience features.

    Provides fallbacks and error recovery for learning operations.
    """

    def __init__(self):
        """Initialize resilient bridge."""
        # Circuit breakers for different services
        self.db_breaker = CircuitBreaker("database", failure_threshold=3, recovery_timeout_seconds=30)
        self.llm_breaker = CircuitBreaker("llm", failure_threshold=5, recovery_timeout_seconds=60)

        # In-memory fallback storage
        self._local_outcomes = []
        self._local_metrics = []

    async def track_outcome_resilient(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        success_rate: float,
        execution_time_ms: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track outcome with fallback to local storage if database unavailable.

        Args:
            agent_name: Name of agent
            decision: Decision made
            outcome: Result
            success_rate: Success metric
            execution_time_ms: Execution time
            context: Additional context

        Returns:
            Status with outcome_id or fallback marker
        """
        try:
            # Try database first if circuit is closed
            if self.db_breaker.is_available():
                try:
                    from athena.learning.tracker import LearningTracker
                    from athena.core.database import Database

                    db = Database()
                    await db.initialize()
                    tracker = LearningTracker(db)

                    outcome_id = await tracker.track_outcome(
                        agent_name=agent_name,
                        decision=decision,
                        outcome=outcome,
                        success_rate=success_rate,
                        execution_time_ms=execution_time_ms,
                        context=context or {}
                    )

                    self.db_breaker.record_success()
                    return {
                        "status": "success",
                        "outcome_id": outcome_id,
                        "stored_in": "database"
                    }

                except Exception as e:
                    logger.warning(f"Database tracking failed: {e}")
                    self.db_breaker.record_failure()
                    # Fall through to local storage

        except Exception as e:
            logger.warning(f"Database unavailable: {e}")

        # Fallback: store locally
        try:
            local_id = len(self._local_outcomes)
            self._local_outcomes.append({
                "id": local_id,
                "agent_name": agent_name,
                "decision": decision,
                "outcome": outcome,
                "success_rate": success_rate,
                "execution_time_ms": execution_time_ms,
                "context": context,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"Outcome stored locally (ID: {local_id}) - will sync when database available")

            return {
                "status": "fallback",
                "outcome_id": local_id,
                "stored_in": "local_cache",
                "will_sync": True
            }

        except Exception as e:
            logger.error(f"Even local storage failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_failed": True
            }

    async def analyze_outcome_resilient(
        self,
        success_rate: float,
        events_processed: int,
        patterns_extracted: int,
        execution_time_ms: float,
        strategy: str = "balanced"
    ) -> Dict[str, Any]:
        """Analyze outcome with LLM, fallback to heuristic if unavailable.

        Args:
            success_rate: Success metric
            events_processed: Number of events
            patterns_extracted: Number of patterns
            execution_time_ms: Execution time
            strategy: Strategy used

        Returns:
            Analysis with reasoning
        """
        # Try LLM first if circuit is closed
        if self.llm_breaker.is_available():
            try:
                from athena.learning.llm_analyzer import LLMOutcomeAnalyzer

                analyzer = LLMOutcomeAnalyzer(llm_client=None)  # Will try to load LLM client
                analysis = await analyzer.analyze_consolidation_outcome(
                    success_rate=success_rate,
                    events_processed=events_processed,
                    patterns_extracted=patterns_extracted,
                    execution_time_ms=execution_time_ms,
                    strategy=strategy
                )

                self.llm_breaker.record_success()
                return {
                    "status": "success",
                    "analysis": analysis,
                    "reasoning_type": "llm-based"
                }

            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")
                self.llm_breaker.record_failure()

        # Fallback: use heuristic analysis
        try:
            heuristic_analysis = self._heuristic_analysis(
                success_rate=success_rate,
                events_processed=events_processed,
                patterns_extracted=patterns_extracted,
                execution_time_ms=execution_time_ms
            )

            return {
                "status": "fallback",
                "analysis": heuristic_analysis,
                "reasoning_type": "heuristic"
            }

        except Exception as e:
            logger.error(f"Even heuristic analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_local_outcomes(self) -> list:
        """Get outcomes stored in local cache.

        Used for syncing when database becomes available.

        Returns:
            List of local outcomes
        """
        return self._local_outcomes.copy()

    def clear_local_cache(self):
        """Clear local cache after successful sync."""
        count = len(self._local_outcomes)
        self._local_outcomes = []
        logger.info(f"Cleared local cache ({count} items synced)")

    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of dependent services.

        Returns:
            Health report for monitoring
        """
        return {
            "database": {
                "state": self.db_breaker.state,
                "failures": self.db_breaker.failure_count,
                "available": self.db_breaker.is_available()
            },
            "llm": {
                "state": self.llm_breaker.state,
                "failures": self.llm_breaker.failure_count,
                "available": self.llm_breaker.is_available()
            },
            "local_cache": {
                "items": len(self._local_outcomes),
                "status": "active" if self._local_outcomes else "empty"
            }
        }

    # Private methods

    def _heuristic_analysis(
        self,
        success_rate: float,
        events_processed: int,
        patterns_extracted: int,
        execution_time_ms: float
    ) -> Dict[str, Any]:
        """Generate heuristic analysis without LLM.

        Args:
            success_rate: Success metric
            events_processed: Number of events
            patterns_extracted: Number of patterns
            execution_time_ms: Execution time

        Returns:
            Analysis dictionary
        """
        if success_rate > 0.9:
            quality = "excellent"
        elif success_rate > 0.8:
            quality = "good"
        elif success_rate > 0.6:
            quality = "fair"
        else:
            quality = "poor"

        return {
            "status": "success",
            "reason": f"Consolidation quality is {quality} ({success_rate:.0%}).",
            "confidence": 0.6,  # Lower confidence for heuristic
            "recommendations": [
                "Monitor this metric over time",
                "Use heuristic until LLM services recover"
            ]
        }


async def with_retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay_ms: float = 100.0
) -> T:
    """Execute function with exponential backoff retry.

    Args:
        func: Async function to call
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between attempts
        initial_delay_ms: Initial delay in milliseconds

    Returns:
        Result from function

    Raises:
        Exception: If all attempts fail
    """
    last_exception = None
    delay_ms = initial_delay_ms

    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            if attempt < max_attempts - 1:
                delay_seconds = delay_ms / 1000.0
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay_seconds:.1f}s..."
                )
                await asyncio.sleep(delay_seconds)
                delay_ms *= backoff_factor

    # All attempts failed
    if last_exception:
        raise last_exception


def validate_outcome(
    agent_name: str,
    decision: str,
    outcome: str,
    success_rate: float
) -> bool:
    """Validate outcome data before storing.

    Args:
        agent_name: Agent name
        decision: Decision made
        outcome: Result
        success_rate: Success metric

    Returns:
        True if valid, False otherwise
    """
    if not agent_name or not isinstance(agent_name, str):
        logger.error("Invalid agent_name")
        return False

    if not decision or not isinstance(decision, str):
        logger.error("Invalid decision")
        return False

    if outcome not in ('success', 'failure', 'partial', 'error'):
        logger.error(f"Invalid outcome: {outcome}")
        return False

    if not (0.0 <= success_rate <= 1.0):
        logger.error(f"Invalid success_rate: {success_rate}")
        return False

    return True

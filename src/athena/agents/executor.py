"""
Executor Agent

Executes planned steps with adaptive error handling.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base import AgentType, BaseAgent


class ExecutionResult(BaseModel):
    """Result of executing a single step"""
    step_id: int
    status: str  # success, error, skipped
    actual_duration_ms: int
    actual_resources: Dict[str, float] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_recovery_attempted: bool = False
    recovery_successful: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_id": self.step_id,
            "status": self.status,
            "actual_duration_ms": self.actual_duration_ms,
            "actual_resources": self.actual_resources,
            "output": self.output,
            "error": self.error,
            "error_recovery_attempted": self.error_recovery_attempted,
            "recovery_successful": self.recovery_successful
        }


class ExecutionRecord(BaseModel):
    """Complete record of task execution"""
    execution_id: int
    plan_id: int
    status: str  # completed, failed, aborted
    start_time: int
    end_time: Optional[int] = None
    steps_completed: List[ExecutionResult] = Field(default_factory=list)
    actual_duration_ms: Optional[int] = None
    errors: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "steps_completed": [s.to_dict() for s in self.steps_completed],
            "actual_duration_ms": self.actual_duration_ms,
            "errors": self.errors
        }


class ExecutorAgent(BaseAgent):
    """
    Executor Agent: Runs planned steps with adaptive error handling.

    Responsibilities:
    - Execute steps in order
    - Handle errors gracefully
    - Adapt execution based on runtime conditions
    - Report detailed results
    - Request resources as needed
    """

    def __init__(self, db_path: str):
        """
        Initialize Executor agent.

        Args:
            db_path: Path to memory database
        """
        super().__init__(AgentType.EXECUTOR, db_path)
        self.active_executions: Dict[int, Dict[str, Any]] = {}
        self.execution_counter = 0

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming messages.

        Args:
            message: Message payload

        Returns:
            Response payload
        """
        try:
            if message.get("action") == "execute":
                return await self.execute_plan(
                    message.get("plan", {}),
                    message.get("execution_id")
                )
            elif message.get("action") == "abort":
                return await self.abort_execution(
                    message.get("execution_id")
                )
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {message.get('action')}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an execution decision based on context.

        Args:
            context: Decision context

        Returns:
            Decision output with confidence score
        """
        plan = context.get("plan", {})
        return await self.execute_plan(plan, context.get("execution_id"))

    async def execute_plan(self, plan: Dict[str, Any],
                          execution_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute plan steps in order.

        Args:
            plan: Execution plan
            execution_id: Execution ID for tracking

        Returns:
            Execution record
        """
        start_time = datetime.now()
        self.status = self.status.PROCESSING
        self.execution_counter += 1
        exec_id = execution_id or self.execution_counter

        self.active_executions[exec_id] = {
            "plan": plan,
            "steps_completed": [],
            "start_time": start_time
        }

        try:
            plan_id = plan.get("id")
            steps = plan.get("steps", [])
            results = []
            errors = []

            for step in steps:
                try:
                    # 1. Check preconditions
                    preconditions_met = await self._check_preconditions(step)
                    if not preconditions_met:
                        results.append(ExecutionResult(
                            step_id=step["id"],
                            status="skipped",
                            actual_duration_ms=0,
                            error="Preconditions not met"
                        ))
                        continue

                    # 2. Acquire resources
                    resources_acquired = await self._acquire_resources(
                        step.get("estimated_resources", {})
                    )
                    if not resources_acquired:
                        results.append(ExecutionResult(
                            step_id=step["id"],
                            status="error",
                            actual_duration_ms=0,
                            error="Could not acquire resources"
                        ))
                        errors.append(f"Step {step['id']}: Resource acquisition failed")
                        continue

                    # 3. Execute step
                    step_start = datetime.now()
                    result = await self._execute_step(step)
                    actual_duration = int((datetime.now() - step_start).total_seconds() * 1000)

                    # 4. Validate outcome
                    outcome_valid = await self._validate_outcome(step, result)

                    if outcome_valid:
                        results.append(ExecutionResult(
                            step_id=step["id"],
                            status="success",
                            actual_duration_ms=actual_duration,
                            actual_resources=resources_acquired,
                            output=result
                        ))
                    else:
                        # 5. Attempt error recovery
                        recovery_attempted, recovery_successful = await self._handle_error(
                            step, result
                        )

                        status = "success" if recovery_successful else "error"
                        results.append(ExecutionResult(
                            step_id=step["id"],
                            status=status,
                            actual_duration_ms=actual_duration,
                            actual_resources=resources_acquired,
                            error=f"Outcome validation failed: {result}",
                            error_recovery_attempted=recovery_attempted,
                            recovery_successful=recovery_successful
                        ))

                        if not recovery_successful and step.get("risk_level") == "high":
                            errors.append(f"Step {step['id']}: High-risk step failed, halting")
                            break

                except Exception as e:
                    results.append(ExecutionResult(
                        step_id=step["id"],
                        status="error",
                        actual_duration_ms=0,
                        error=str(e)
                    ))
                    errors.append(f"Step {step['id']}: {str(e)}")

            # Determine overall status
            overall_status = "completed"
            if errors:
                overall_status = "failed"
            elif all(r.status in ["success", "skipped"] for r in results):
                overall_status = "completed"

            total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
            success = len(errors) == 0

            # Record decision metrics
            confidence = 1.0 - (len(errors) / max(1, len(steps)))
            self.record_decision(success, total_duration, confidence)

            execution_record = ExecutionRecord(
                execution_id=exec_id,
                plan_id=plan_id,
                status=overall_status,
                start_time=int(start_time.timestamp()),
                end_time=int(datetime.now().timestamp()),
                steps_completed=results,
                actual_duration_ms=total_duration,
                errors=errors
            )

            del self.active_executions[exec_id]
            self.status = self.status.IDLE

            return {
                "status": "success" if success else "partial_failure",
                "execution": execution_record.to_dict(),
                "results": [r.to_dict() for r in results],
                "total_errors": len(errors)
            }

        except Exception as e:
            del self.active_executions[exec_id]
            self.status = self.status.ERROR

            return {
                "status": "error",
                "error": str(e),
                "execution_id": exec_id
            }

    async def abort_execution(self, execution_id: int) -> Dict[str, Any]:
        """
        Gracefully abort in-flight execution.

        Args:
            execution_id: ID of execution to abort

        Returns:
            Abort confirmation
        """
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]
            return {
                "status": "success",
                "message": "Execution aborted",
                "execution_id": execution_id
            }
        return {
            "status": "error",
            "message": "Execution not found",
            "execution_id": execution_id
        }

    async def _check_preconditions(self, step: Dict[str, Any]) -> bool:
        """
        Verify step preconditions are met.

        Args:
            step: Step definition

        Returns:
            True if preconditions are met
        """
        # Simple implementation: assume all preconditions are met
        # In full implementation, would verify dependencies, environment, etc.
        return True

    async def _acquire_resources(self, required: Dict[str, float]) -> Dict[str, float]:
        """
        Reserve resources needed for step.

        Args:
            required: Required resources

        Returns:
            Actual resources allocated (or empty dict if failed)
        """
        # Simple implementation: return requested resources
        # In full implementation, would check system availability
        return required

    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actually run the step.

        Args:
            step: Step definition

        Returns:
            Step output
        """
        # Simulate step execution with a small delay
        import asyncio
        await asyncio.sleep(0.01)

        return {
            "step_id": step.get("id"),
            "description": step.get("description"),
            "executed": True,
            "timestamp": datetime.now().isoformat()
        }

    async def _validate_outcome(self, step: Dict[str, Any],
                               outcome: Dict[str, Any]) -> bool:
        """
        Check if outcome meets success criteria.

        Args:
            step: Step definition
            outcome: Step execution outcome

        Returns:
            True if outcome is valid
        """
        # Simple implementation: assume success if step executed
        return outcome.get("executed", False)

    async def _handle_error(self, step: Dict[str, Any],
                           error: Dict[str, Any]) -> tuple:
        """
        Attempt error recovery.

        Args:
            step: Step definition
            error: Error information

        Returns:
            (recovery_attempted, recovery_successful)
        """
        # Simple implementation: no recovery attempt
        return (False, False)

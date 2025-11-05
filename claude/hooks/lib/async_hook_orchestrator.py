#!/usr/bin/env python3
"""
Async Hook Orchestrator - Phase 6 Implementation

Manages hook execution with:
- Concurrent/parallel execution of hooks with no dependencies
- Dependency resolution with asyncio
- Timeout protection per hook
- Failure handling and cascading
- Metric recording
- Backward compatibility with sync mode

Usage:
    orchestrator = AsyncHookOrchestrator()

    # Async execution (Phase 6+)
    result = await orchestrator.execute_phase_async("session-start", hook_input)

    # Fallback to sync if needed
    result = orchestrator.execute_phase_sync("session-start", hook_input)
"""

import json
import subprocess
import sys
import time
import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("async_hook_orchestrator")


class HookStatus(Enum):
    """Hook execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CACHED = "cached"


@dataclass
class HookExecution:
    """Record of a hook's execution"""
    name: str
    phase: str
    status: HookStatus
    start_time: float
    end_time: float
    duration_ms: int
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    was_parallel: bool = False
    was_cached: bool = False

    def to_dict(self):
        return {
            "name": self.name,
            "phase": self.phase,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "was_parallel": self.was_parallel,
            "was_cached": self.was_cached,
        }


class ExecutionGroup:
    """Group of hooks to execute together (sequentially or in parallel)"""

    def __init__(self, group_id: int, hooks: List[str],
                 parallel: bool = False, description: str = ""):
        self.group_id = group_id
        self.hooks = hooks
        self.parallel = parallel
        self.description = description

    def __repr__(self):
        mode = "PARALLEL" if self.parallel else "SEQUENTIAL"
        return f"Group({self.group_id}, {mode}, {len(self.hooks)} hooks)"


class AsyncHookOrchestrator:
    """
    Async version of HookOrchestrator supporting parallel execution

    Features:
    - asyncio-based concurrent execution
    - Dependency-respecting parallelization
    - Timeout protection per hook
    - Failure handling and cascading
    - Metrics collection
    - Backward compatibility with sync mode
    """

    def __init__(self, manifest_path: Optional[str] = None):
        """
        Initialize orchestrator with hook manifest

        Args:
            manifest_path: Path to hook_manifest.json
        """
        if manifest_path is None:
            manifest_path = str(Path(__file__).parent.parent / "hook_manifest.json")

        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()
        self.executions: List[HookExecution] = []
        self.hook_map = {h["name"]: h for h in self.manifest.get("hooks", [])}
        self.execution_groups: Dict[str, List[ExecutionGroup]] = {}
        self._build_execution_groups()

    def _load_manifest(self) -> Dict:
        """Load and parse hook manifest"""
        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            logger.info(f"Loaded manifest from {self.manifest_path}")
            return manifest
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load manifest: {e}")
            sys.exit(1)

    def _build_execution_groups(self):
        """
        Build execution groups from manifest

        Creates sequential and parallel groups based on:
        1. Dependencies (hooks with same dependency can be parallel)
        2. Manifest execution flows
        3. Phase configuration
        """
        for phase_name, flow_config in self.manifest.get("executionFlows", {}).items():
            phase = flow_config.get("phase")
            if not phase:
                continue

            groups = []
            parallelizable = set(flow_config.get("parallelizable", []))
            order = flow_config.get("order", [])

            if not order:
                continue

            # Build groups: sequential core, then parallel optionals
            sequential_hooks = []
            parallel_hooks = []

            for hook_name in order:
                if hook_name in parallelizable:
                    parallel_hooks.append(hook_name)
                else:
                    sequential_hooks.append(hook_name)

            # Create sequential group for critical hooks
            if sequential_hooks:
                groups.append(ExecutionGroup(
                    group_id=1,
                    hooks=sequential_hooks,
                    parallel=False,
                    description="Critical path hooks (sequential)"
                ))

            # Create parallel group for optional hooks
            if parallel_hooks:
                groups.append(ExecutionGroup(
                    group_id=2,
                    hooks=parallel_hooks,
                    parallel=True,
                    description="Non-critical hooks (parallel)"
                ))

            self.execution_groups[phase] = groups
            logger.debug(f"Phase '{phase}': {len(groups)} groups")
            for group in groups:
                logger.debug(f"  {group} -> {group.hooks}")

    def get_execution_groups(self, phase: str) -> List[ExecutionGroup]:
        """Get execution groups for a phase"""
        return self.execution_groups.get(phase, [])

    async def execute_phase_async(self, phase: str, hook_input: Dict,
                                  skip_on_failure: bool = False) -> Dict:
        """
        Execute all hooks in a phase asynchronously

        Runs hooks in groups:
        - Group 1 (critical path): sequential
        - Group N (parallel): concurrent with asyncio.gather()

        Args:
            phase: Phase name
            hook_input: Input JSON for hooks
            skip_on_failure: Skip remaining hooks if one fails

        Returns:
            Execution summary
        """
        groups = self.get_execution_groups(phase)

        if not groups:
            logger.warning(f"No execution groups for phase: {phase}")
            # Fallback to topological order if no groups defined
            return await self._execute_phase_fallback_async(phase, hook_input, skip_on_failure)

        executed = 0
        failed = 0
        start_phase_time = time.time()

        logger.info(f"Starting phase '{phase}' with {len(groups)} groups")

        for group in groups:
            logger.debug(f"Executing {group}")

            if group.parallel:
                # Execute group hooks in parallel
                results = await self._execute_group_parallel(
                    group.hooks, hook_input, skip_on_failure
                )
            else:
                # Execute group hooks sequentially
                results = await self._execute_group_sequential(
                    group.hooks, hook_input, skip_on_failure
                )

            executed += len(results)
            failed += sum(1 for h in results if results[h].status != HookStatus.SUCCESS)

            if failed > 0 and skip_on_failure:
                logger.error(f"Hook failed in {group}, stopping phase")
                return {
                    "phase": phase,
                    "status": "failed",
                    "hook_count": executed,
                    "failed_count": failed,
                    "execution_time_ms": int((time.time() - start_phase_time) * 1000)
                }

        phase_duration = int((time.time() - start_phase_time) * 1000)

        return {
            "phase": phase,
            "status": "success" if failed == 0 else "partial",
            "hook_count": executed,
            "failed_count": failed,
            "execution_time_ms": phase_duration,
            "execution_groups": len(groups),
            "parallel_hooks": sum(len(g.hooks) for g in groups if g.parallel),
            "sequential_hooks": sum(len(g.hooks) for g in groups if not g.parallel)
        }

    async def _execute_group_sequential(self, hook_names: List[str],
                                       hook_input: Dict,
                                       skip_on_failure: bool) -> Dict[str, HookExecution]:
        """Execute hooks in group sequentially"""
        results = {}

        for hook_name in hook_names:
            if hook_name not in self.hook_map:
                logger.warning(f"Hook not found: {hook_name}")
                continue

            hook = self.hook_map[hook_name]

            # Check if dependencies succeeded
            deps_ok = True
            for dep in hook.get("dependsOn", []):
                if dep not in results:
                    # Look in previous executions
                    dep_exec = next((e for e in self.executions if e.name == dep), None)
                    if dep_exec is None or dep_exec.status != HookStatus.SUCCESS:
                        logger.warning(f"Skipping {hook_name} - dependency {dep} failed")
                        deps_ok = False
                        if skip_on_failure:
                            return results

                elif results[dep].status != HookStatus.SUCCESS:
                    logger.warning(f"Skipping {hook_name} - dependency {dep} failed")
                    deps_ok = False
                    if skip_on_failure:
                        return results

            if not deps_ok:
                continue

            # Execute hook
            execution = await self._execute_hook_async(hook, hook_input, parallel=False)
            self.executions.append(execution)
            results[hook_name] = execution

        return results

    async def _execute_group_parallel(self, hook_names: List[str],
                                     hook_input: Dict,
                                     skip_on_failure: bool) -> Dict[str, HookExecution]:
        """Execute hooks in group in parallel using asyncio.gather()"""
        # Filter hooks with satisfied dependencies
        ready_hooks = []
        for hook_name in hook_names:
            if hook_name not in self.hook_map:
                logger.warning(f"Hook not found: {hook_name}")
                continue

            hook = self.hook_map[hook_name]

            # Check if dependencies succeeded
            deps_ok = True
            for dep in hook.get("dependsOn", []):
                dep_exec = next((e for e in self.executions if e.name == dep), None)
                if dep_exec is None or dep_exec.status != HookStatus.SUCCESS:
                    logger.warning(f"Skipping {hook_name} - dependency {dep} not satisfied")
                    deps_ok = False
                    if skip_on_failure:
                        return {}

            if deps_ok:
                ready_hooks.append(hook_name)

        if not ready_hooks:
            logger.warning(f"No ready hooks in parallel group")
            return {}

        logger.debug(f"Executing {len(ready_hooks)} hooks in parallel")

        # Execute all ready hooks concurrently
        tasks = [
            self._execute_hook_async(self.hook_map[hook_name], hook_input, parallel=True)
            for hook_name in ready_hooks
        ]

        executions = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for hook_name, execution in zip(ready_hooks, executions):
            if isinstance(execution, Exception):
                logger.error(f"Exception during hook execution: {execution}")
                results[hook_name] = HookExecution(
                    name=hook_name,
                    phase="unknown",
                    status=HookStatus.FAILURE,
                    start_time=time.time(),
                    end_time=time.time(),
                    duration_ms=0,
                    exit_code=-1,
                    was_parallel=True
                )
            else:
                self.executions.append(execution)
                results[hook_name] = execution

        return results

    async def _execute_phase_fallback_async(self, phase: str, hook_input: Dict,
                                          skip_on_failure: bool) -> Dict:
        """Fallback to topological order if no execution groups defined"""
        logger.info(f"No execution groups found, using topological order for '{phase}'")

        phase_hooks = [h["name"] for h in self.manifest.get("hooks", [])
                      if h.get("phase") == phase]

        if not phase_hooks:
            logger.warning(f"No hooks found for phase: {phase}")
            return {"phase": phase, "status": "skipped", "hook_count": 0}

        # Build dependency map
        dep_map = {}
        for hook_name in phase_hooks:
            hook = self.hook_map[hook_name]
            deps = [d for d in hook.get("dependsOn", []) if d in phase_hooks]
            dep_map[hook_name] = deps

        # Topological sort
        order = []
        visited = set()
        temp_visited = set()

        def visit(node):
            if node in visited:
                return
            if node in temp_visited:
                logger.warning(f"Cycle detected involving {node}")
                return

            temp_visited.add(node)
            for dep in dep_map.get(node, []):
                visit(dep)
            temp_visited.remove(node)

            visited.add(node)
            order.append(node)

        for hook in phase_hooks:
            visit(hook)

        # Execute in topological order
        executed = 0
        failed = 0

        for hook_name in order:
            hook = self.hook_map[hook_name]
            execution = await self._execute_hook_async(hook, hook_input, parallel=False)
            self.executions.append(execution)
            executed += 1

            if execution.status != HookStatus.SUCCESS:
                failed += 1
                if skip_on_failure:
                    return {
                        "phase": phase,
                        "status": "failed",
                        "hook_count": executed,
                        "failed_count": failed
                    }

        return {
            "phase": phase,
            "status": "success" if failed == 0 else "partial",
            "hook_count": executed,
            "failed_count": failed
        }

    async def _execute_hook_async(self, hook: Dict, hook_input: Dict,
                                 parallel: bool = False) -> HookExecution:
        """
        Execute a single hook asynchronously

        Args:
            hook: Hook definition from manifest
            hook_input: Input JSON for the hook
            parallel: Whether hook is running in parallel group

        Returns:
            HookExecution record
        """
        hook_name = hook["name"]
        hook_file = hook["filePath"]
        timeout = hook.get("timeout", 3000) / 1000.0  # Convert ms to seconds

        execution = HookExecution(
            name=hook_name,
            phase=hook["phase"],
            status=HookStatus.RUNNING,
            start_time=time.time(),
            end_time=0,
            duration_ms=0,
            exit_code=-1,
            was_parallel=parallel
        )

        try:
            # Prepare hook input
            input_data = json.dumps(hook_input)

            # Execute hook with timeout using asyncio.create_subprocess_exec
            logger.debug(f"Executing {hook_file} asynchronously (timeout: {timeout}s)")

            process = await asyncio.create_subprocess_exec(
                "/bin/bash", hook_file,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024  # 1MB buffer limit
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data.encode()),
                    timeout=timeout
                )

                execution.stdout = stdout.decode('utf-8', errors='replace')
                execution.stderr = stderr.decode('utf-8', errors='replace')
                execution.exit_code = process.returncode
                execution.status = HookStatus.SUCCESS if process.returncode == 0 else HookStatus.FAILURE

                if process.returncode != 0:
                    logger.warning(f"Hook {hook_name} exited with code {process.returncode}")
                    if execution.stderr:
                        logger.debug(f"  stderr: {execution.stderr[:200]}")

            except asyncio.TimeoutError:
                # Kill the process on timeout
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass

                execution.status = HookStatus.TIMEOUT
                logger.error(f"Hook {hook_name} timed out after {timeout}s")

        except Exception as e:
            execution.status = HookStatus.FAILURE
            execution.exit_code = -1
            logger.error(f"Hook {hook_name} failed: {e}")

        execution.end_time = time.time()
        execution.duration_ms = int((execution.end_time - execution.start_time) * 1000)

        return execution

    def execute_phase_sync(self, phase: str, hook_input: Dict,
                          skip_on_failure: bool = False) -> Dict:
        """
        Execute phase synchronously (fallback to sync mode)

        For use when async is not available or when calling from sync code
        """
        try:
            # Try to use existing event loop, or create new one
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use run_until_complete
                logger.warning("Event loop is already running, cannot execute async")
                # Fall back to basic sync execution
                return {"phase": phase, "status": "skipped", "reason": "event_loop_running"}
        except RuntimeError:
            # No event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(
                self.execute_phase_async(phase, hook_input, skip_on_failure)
            )
        finally:
            # Don't close the loop if we didn't create it
            pass

    def get_summary(self) -> Dict:
        """Get summary of all executions"""
        if not self.executions:
            return {"total": 0, "summary": "No executions recorded"}

        by_status = {}
        for exec in self.executions:
            status = exec.status.value
            by_status[status] = by_status.get(status, 0) + 1

        parallel_count = sum(1 for e in self.executions if e.was_parallel)
        sequential_count = len(self.executions) - parallel_count

        return {
            "total": len(self.executions),
            "by_status": by_status,
            "total_time_ms": sum(e.duration_ms for e in self.executions),
            "parallel_executions": parallel_count,
            "sequential_executions": sequential_count,
            "executions": [e.to_dict() for e in self.executions]
        }

    def export_metrics(self, output_path: Optional[str] = None) -> str:
        """Export execution metrics to file"""
        if output_path is None:
            output_path = str(Path(__file__).parent.parent / "async_orchestration_metrics.json")

        metrics = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": self.get_summary(),
            "hooks": [asdict(e) for e in self.executions]
        }

        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)

        logger.info(f"Metrics exported to {output_path}")
        return output_path


async def main_async():
    """Async CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Async Hook Orchestrator")
    parser.add_argument("--phase", help="Phase to execute")
    parser.add_argument("--input", help="JSON input for hooks", default="{}")
    parser.add_argument("--manifest", help="Path to hook_manifest.json")
    parser.add_argument("--export-metrics", help="Export metrics to file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    orchestrator = AsyncHookOrchestrator(args.manifest)

    if not args.phase:
        parser.print_help()
        sys.exit(1)

    try:
        hook_input = json.loads(args.input)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)

    logger.info(f"Starting async phase execution: {args.phase}")
    result = await orchestrator.execute_phase_async(args.phase, hook_input)

    if args.export_metrics:
        orchestrator.export_metrics(args.export_metrics)

    print(json.dumps(orchestrator.get_summary(), indent=2))

    sys.exit(0 if result.get("failed_count", 0) == 0 else 1)


def main():
    """Sync wrapper for CLI"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()

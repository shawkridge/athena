#!/usr/bin/env python3
"""
Hook Orchestrator - Phase 4 Implementation

Manages hook execution with:
- Dependency resolution (topological sort)
- Execution ordering
- Timeout protection
- Failure handling
- Metric recording

Usage:
    python3 hook_orchestrator.py --phase session-start --input '{"cwd":"..."}'
    python3 hook_orchestrator.py --phase user-prompt-submit --input '{"cwd":"..."}'
    python3 hook_orchestrator.py --validate  # Validate manifest
"""

import json
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hook_orchestrator")


class HookStatus(Enum):
    """Hook execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


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

    def to_dict(self):
        return {
            "name": self.name,
            "phase": self.phase,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
        }


class HookOrchestrator:
    """
    Orchestrates hook execution with dependency management
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

    def validate_manifest(self) -> Tuple[bool, List[str]]:
        """
        Validate hook manifest for consistency

        Returns:
            (is_valid, errors)
        """
        errors = []
        hooks = {h["name"]: h for h in self.manifest.get("hooks", [])}

        # Check for duplicate names
        if len(hooks) != len(self.manifest.get("hooks", [])):
            errors.append("Duplicate hook names found")

        # Check all dependencies exist
        for hook in self.manifest.get("hooks", []):
            for dep in hook.get("dependsOn", []):
                if dep not in hooks:
                    errors.append(f"Hook '{hook['name']}' depends on non-existent '{dep}'")

        # Check for circular dependencies
        cycles = self._detect_cycles()
        if cycles:
            errors.append(f"Circular dependencies detected: {cycles}")

        # Check all files exist
        for hook in self.manifest.get("hooks", []):
            hook_file = Path(hook["filePath"])
            if not hook_file.exists():
                errors.append(f"Hook file not found: {hook['filePath']}")

        is_valid = len(errors) == 0
        status = "✅ Valid" if is_valid else "❌ Invalid"
        logger.info(f"Manifest validation: {status}")

        if errors:
            for error in errors:
                logger.error(f"  - {error}")

        return is_valid, errors

    def _detect_cycles(self) -> List[List[str]]:
        """
        Detect circular dependencies using DFS

        Returns:
            List of cycles found
        """
        hooks = {h["name"]: h for h in self.manifest.get("hooks", [])}
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in hooks[node].get("dependsOn", []):
                if dep not in visited:
                    dfs(dep, path.copy())
                elif dep in rec_stack:
                    cycle = path[path.index(dep):] + [dep]
                    cycles.append(cycle)

            rec_stack.remove(node)

        for hook in hooks:
            if hook not in visited:
                dfs(hook, [])

        return cycles

    def get_execution_order(self, phase: str) -> List[str]:
        """
        Get execution order for hooks in a phase using topological sort

        Args:
            phase: Phase name (e.g., "session-start", "user-prompt-submit")

        Returns:
            List of hook names in execution order
        """
        # Get hooks in this phase
        phase_hooks = [h["name"] for h in self.manifest.get("hooks", [])
                      if h.get("phase") == phase]

        if not phase_hooks:
            logger.warning(f"No hooks found for phase: {phase}")
            return []

        # Build dependency map for this phase
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

        logger.info(f"Phase '{phase}' execution order: {order}")
        return order

    def execute_phase(self, phase: str, hook_input: Dict,
                     skip_on_failure: bool = False) -> Dict:
        """
        Execute all hooks in a phase

        Args:
            phase: Phase name
            hook_input: Input JSON for hooks
            skip_on_failure: Skip remaining hooks if one fails

        Returns:
            Execution summary
        """
        order = self.get_execution_order(phase)

        if not order:
            logger.warning(f"No hooks to execute for phase: {phase}")
            return {"phase": phase, "status": "skipped", "hook_count": 0}

        executed = 0
        failed = 0

        for hook_name in order:
            hook = self.hook_map[hook_name]

            # Check if dependencies succeeded
            deps_ok = True
            for dep in hook.get("dependsOn", []):
                dep_exec = next((e for e in self.executions if e.name == dep), None)
                if dep_exec and dep_exec.status != HookStatus.SUCCESS:
                    logger.warning(f"Skipping {hook_name} - dependency {dep} failed")
                    deps_ok = False
                    if skip_on_failure:
                        return {
                            "phase": phase,
                            "status": "dependency_failed",
                            "failed_dependency": dep,
                            "hook_count": executed,
                            "failed_count": failed
                        }

            if not deps_ok:
                continue

            # Execute hook
            logger.info(f"Executing hook: {hook_name}")
            execution = self._execute_hook(hook, hook_input)
            self.executions.append(execution)
            executed += 1

            if execution.status != HookStatus.SUCCESS:
                failed += 1
                if skip_on_failure:
                    logger.error(f"Hook {hook_name} failed, stopping phase")
                    return {
                        "phase": phase,
                        "status": "failed",
                        "failed_hook": hook_name,
                        "hook_count": executed,
                        "failed_count": failed
                    }

        return {
            "phase": phase,
            "status": "success" if failed == 0 else "partial",
            "hook_count": executed,
            "failed_count": failed,
            "execution_time_ms": sum(e.duration_ms for e in self.executions
                                     if e.phase == phase)
        }

    def _execute_hook(self, hook: Dict, hook_input: Dict) -> HookExecution:
        """
        Execute a single hook

        Args:
            hook: Hook definition from manifest
            hook_input: Input JSON for the hook

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
            exit_code=-1
        )

        try:
            # Prepare hook input
            input_data = json.dumps(hook_input)

            # Execute hook with timeout
            logger.debug(f"Executing {hook_file} with timeout {timeout}s")
            result = subprocess.run(
                ["/bin/bash", hook_file],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            execution.exit_code = result.returncode
            execution.stdout = result.stdout
            execution.stderr = result.stderr
            execution.status = HookStatus.SUCCESS if result.returncode == 0 else HookStatus.FAILURE

            if result.returncode != 0:
                logger.warning(f"Hook {hook_name} exited with code {result.returncode}")
                if result.stderr:
                    logger.debug(f"  stderr: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            execution.status = HookStatus.TIMEOUT
            logger.error(f"Hook {hook_name} timed out after {timeout}s")
        except Exception as e:
            execution.status = HookStatus.FAILURE
            execution.exit_code = -1
            logger.error(f"Hook {hook_name} failed: {e}")

        execution.end_time = time.time()
        execution.duration_ms = int((execution.end_time - execution.start_time) * 1000)

        return execution

    def get_summary(self) -> Dict:
        """Get summary of all executions"""
        if not self.executions:
            return {"total": 0, "summary": "No executions recorded"}

        by_status = {}
        for exec in self.executions:
            status = exec.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total": len(self.executions),
            "by_status": by_status,
            "total_time_ms": sum(e.duration_ms for e in self.executions),
            "executions": [e.to_dict() for e in self.executions]
        }

    def export_metrics(self, output_path: Optional[str] = None) -> str:
        """
        Export execution metrics to file

        Args:
            output_path: Path to write metrics (default: metrics.json)

        Returns:
            Path to metrics file
        """
        if output_path is None:
            output_path = str(Path(__file__).parent.parent / "orchestration_metrics.json")

        metrics = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": self.get_summary(),
            "hooks": [asdict(e) for e in self.executions]
        }

        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)

        logger.info(f"Metrics exported to {output_path}")
        return output_path


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Hook Orchestrator")
    parser.add_argument("--phase", help="Phase to execute (session-start, user-prompt-submit, etc)")
    parser.add_argument("--input", help="JSON input for hooks", default="{}")
    parser.add_argument("--manifest", help="Path to hook_manifest.json")
    parser.add_argument("--validate", action="store_true", help="Validate manifest")
    parser.add_argument("--dry-run", action="store_true", help="Show execution order without running")
    parser.add_argument("--export-metrics", help="Export metrics to file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Initialize orchestrator
    orchestrator = HookOrchestrator(args.manifest)

    # Validate if requested
    if args.validate:
        is_valid, errors = orchestrator.validate_manifest()
        if not is_valid:
            sys.exit(1)
        sys.exit(0)

    if not args.phase:
        parser.print_help()
        sys.exit(1)

    # Parse input
    try:
        hook_input = json.loads(args.input)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)

    # Dry run: show execution order
    if args.dry_run:
        order = orchestrator.get_execution_order(args.phase)
        print(f"Execution order for phase '{args.phase}':")
        for i, hook in enumerate(order, 1):
            print(f"  {i}. {hook}")
        sys.exit(0)

    # Execute phase
    logger.info(f"Starting phase execution: {args.phase}")
    result = orchestrator.execute_phase(args.phase, hook_input)

    # Export metrics if requested
    if args.export_metrics:
        orchestrator.export_metrics(args.export_metrics)
    else:
        # Always export to default location
        orchestrator.export_metrics()

    # Print summary
    print(json.dumps(orchestrator.get_summary(), indent=2))

    # Exit with error if any hooks failed
    if result.get("failed_count", 0) > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

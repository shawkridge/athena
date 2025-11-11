"""Git-backed procedure storage with versioning and audit trail.

This module provides GitBackedProcedureStore, which stores executable procedures
in git with full version history, enabling code-centric procedure management
aligned with the MCP paradigm.
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from .models import ExecutableProcedure, ProcedureVersion, ProcedureCategory

logger = logging.getLogger(__name__)


class GitBackedProcedureStore:
    """Stores executable procedures in git with full version control.

    Features:
    - Procedures stored as individual Python files in git
    - Full commit history and audit trail
    - Rollback and version recovery
    - Semantic versioning support
    - Metadata storage alongside code
    """

    def __init__(self, git_repo_path: str, procedures_dir: str = "procedures"):
        """Initialize git-backed procedure store.

        Args:
            git_repo_path: Path to git repository root
            procedures_dir: Subdirectory in repo for procedures (default: "procedures")
        """
        self.git_repo_path = Path(git_repo_path)
        self.procedures_dir = self.git_repo_path / procedures_dir
        self.metadata_dir = self.procedures_dir / ".metadata"

        # Ensure git repo and directories exist
        self._ensure_git_repo()
        self._ensure_directories()

        # Store in-memory procedures for fast access
        self._procedures: Dict[int, ExecutableProcedure] = {}

    def _ensure_git_repo(self):
        """Ensure git repository exists, initialize if needed."""
        git_dir = self.git_repo_path / ".git"
        if not git_dir.exists():
            logger.info(f"Initializing git repository at {self.git_repo_path}")
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=self.git_repo_path,
                    check=True,
                    capture_output=True,
                )
                # Configure git user for commits
                subprocess.run(
                    ["git", "config", "user.email", "athena-system@local"],
                    cwd=self.git_repo_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "config", "user.name", "Athena System"],
                    cwd=self.git_repo_path,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to initialize git repo: {e}")
                raise

    def _ensure_directories(self):
        """Ensure procedure and metadata directories exist."""
        self.procedures_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _get_procedure_path(self, procedure_id: int, procedure_name: str) -> Path:
        """Get filesystem path for a procedure.

        Args:
            procedure_id: Procedure ID
            procedure_name: Procedure name (for readability)

        Returns:
            Path to procedure file
        """
        # Create a safe filename from procedure name
        safe_name = procedure_name.lower().replace(" ", "_").replace("/", "_")
        return self.procedures_dir / f"{procedure_id}_{safe_name}.py"

    def _get_metadata_path(self, procedure_id: int) -> Path:
        """Get filesystem path for procedure metadata.

        Args:
            procedure_id: Procedure ID

        Returns:
            Path to metadata file
        """
        return self.metadata_dir / f"{procedure_id}_metadata.json"

    def store_procedure(
        self,
        procedure: ExecutableProcedure,
        author: str = "athena-system",
        commit_message: Optional[str] = None,
    ) -> str:
        """Store procedure in git with commit.

        Args:
            procedure: Procedure to store
            author: Author name for git commit
            commit_message: Custom commit message (optional)

        Returns:
            Git commit hash

        Raises:
            ValueError: If procedure validation fails
            subprocess.CalledProcessError: If git operations fail
        """
        # Validate procedure
        if not procedure.id:
            raise ValueError("Procedure must have an ID")
        if not procedure.code:
            raise ValueError("Procedure must have executable code")

        procedure_path = self._get_procedure_path(procedure.id, procedure.name)
        metadata_path = self._get_metadata_path(procedure.id)

        # Write code to file
        procedure_path.write_text(procedure.code, encoding="utf-8")
        logger.info(f"Wrote procedure code to {procedure_path}")

        # Write metadata as JSON
        metadata = {
            "id": procedure.id,
            "name": procedure.name,
            "category": procedure.category,
            "description": procedure.description,
            "code_version": procedure.code_version,
            "code_language": procedure.code_language,
            "code_generation_confidence": procedure.code_generation_confidence,
            "parameters": [p.model_dump() for p in procedure.parameters],
            "returns": procedure.returns,
            "examples": procedure.examples,
            "preconditions": procedure.preconditions,
            "postconditions": procedure.postconditions,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info(f"Wrote procedure metadata to {metadata_path}")

        # Stage files
        try:
            subprocess.run(
                ["git", "add", str(procedure_path), str(metadata_path)],
                cwd=self.git_repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stage procedure files: {e}")
            raise

        # Create commit
        if not commit_message:
            commit_message = f"Add procedure {procedure.id}: {procedure.name} (v{procedure.code_version})"

        try:
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Check if nothing to commit (file unchanged)
                if "nothing to commit" in result.stdout.lower():
                    logger.info(f"No changes to commit for procedure {procedure.id}")
                    # Still get the hash of the last commit
                    return self._get_last_commit_hash()
                else:
                    logger.error(f"Git commit failed: {result.stderr}")
                    raise subprocess.CalledProcessError(result.returncode, "git commit")

            # Get commit hash
            git_hash = self._get_last_commit_hash()
            procedure.code_git_hash = git_hash
            logger.info(f"Committed procedure {procedure.id} with hash {git_hash}")

            return git_hash

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit procedure: {e}")
            raise

    def get_procedure(self, procedure_id: int) -> Optional[ExecutableProcedure]:
        """Retrieve procedure from git.

        Args:
            procedure_id: Procedure ID

        Returns:
            ExecutableProcedure if found, None otherwise
        """
        metadata_path = self._get_metadata_path(procedure_id)

        if not metadata_path.exists():
            logger.warning(f"Metadata not found for procedure {procedure_id}")
            return None

        try:
            metadata_text = metadata_path.read_text(encoding="utf-8")
            metadata = json.loads(metadata_text)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read metadata for procedure {procedure_id}: {e}")
            return None

        # Find and read code file
        code_path = self._find_code_path(procedure_id)
        if not code_path:
            logger.warning(f"Code file not found for procedure {procedure_id}")
            return None

        try:
            code = code_path.read_text(encoding="utf-8")
        except IOError as e:
            logger.error(f"Failed to read code for procedure {procedure_id}: {e}")
            return None

        # Reconstruct ExecutableProcedure
        procedure = ExecutableProcedure(
            id=metadata.get("id"),
            procedure_id=metadata.get("id"),
            name=metadata.get("name"),
            category=metadata.get("category"),
            code=code,
            code_version=metadata.get("code_version", "1.0.0"),
            code_language=metadata.get("code_language", "python"),
            code_generated_at=datetime.now(),
            code_generation_confidence=metadata.get("code_generation_confidence", 0.8),
            description=metadata.get("description"),
            returns=metadata.get("returns"),
            examples=metadata.get("examples", []),
            preconditions=metadata.get("preconditions", []),
            postconditions=metadata.get("postconditions", []),
        )

        return procedure

    def _find_code_path(self, procedure_id: int) -> Optional[Path]:
        """Find code file for procedure by ID.

        Args:
            procedure_id: Procedure ID

        Returns:
            Path to code file if found, None otherwise
        """
        # Search for files matching pattern: {procedure_id}_*.py
        for file_path in self.procedures_dir.glob(f"{procedure_id}_*.py"):
            if file_path.is_file():
                return file_path
        return None

    def get_version(self, procedure_id: int, version: str) -> Optional[str]:
        """Retrieve code for a specific version.

        Args:
            procedure_id: Procedure ID
            version: Semantic version string (e.g., "1.0.0")

        Returns:
            Code content for that version, or None if not found
        """
        try:
            # Use git show to get file at specific version
            code_path = self._find_code_path(procedure_id)
            if not code_path:
                return None

            result = subprocess.run(
                ["git", "log", "--all", "--grep", version, str(code_path)],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout:
                # Extract commit hash from log output
                for line in result.stdout.split("\n"):
                    if line.startswith("commit "):
                        commit_hash = line.split()[1]
                        return self._get_file_at_commit(str(code_path), commit_hash)

            return None

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to retrieve version {version}: {e}")
            return None

    def _get_file_at_commit(self, file_path: str, commit_hash: str) -> Optional[str]:
        """Get file contents at a specific commit.

        Args:
            file_path: Relative file path
            commit_hash: Git commit hash

        Returns:
            File contents, or None if not found
        """
        try:
            result = subprocess.run(
                ["git", "show", f"{commit_hash}:{file_path}"],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return result.stdout

            return None

        except subprocess.CalledProcessError:
            return None

    def rollback_procedure(
        self,
        procedure_id: int,
        target_version: str,
        author: str = "athena-system",
    ) -> bool:
        """Rollback procedure to a previous version.

        Args:
            procedure_id: Procedure ID
            target_version: Version to rollback to
            author: Author name for rollback commit

        Returns:
            True if rollback successful, False otherwise
        """
        try:
            code = self.get_version(procedure_id, target_version)
            if not code:
                logger.error(f"Version {target_version} not found for procedure {procedure_id}")
                return False

            code_path = self._find_code_path(procedure_id)
            if not code_path:
                logger.error(f"Code file not found for procedure {procedure_id}")
                return False

            # Write old code
            code_path.write_text(code, encoding="utf-8")

            # Commit rollback
            message = f"Rollback procedure {procedure_id} to version {target_version}"
            subprocess.run(
                ["git", "add", str(code_path)],
                cwd=self.git_repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.git_repo_path,
                check=True,
                capture_output=True,
            )

            logger.info(f"Rolled back procedure {procedure_id} to version {target_version}")
            return True

        except (subprocess.CalledProcessError, IOError) as e:
            logger.error(f"Failed to rollback procedure {procedure_id}: {e}")
            return False

    def get_procedure_history(self, procedure_id: int) -> List[Dict]:
        """Get git history for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            List of commit info dicts in reverse chronological order
        """
        try:
            code_path = self._find_code_path(procedure_id)
            if not code_path:
                return []

            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--pretty=format:%H|%an|%ai|%s",
                    str(code_path),
                ],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Failed to get history for procedure {procedure_id}")
                return []

            history = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 4:
                    history.append({
                        "commit": parts[0],
                        "author": parts[1],
                        "timestamp": parts[2],
                        "message": parts[3],
                    })

            return history

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get procedure history: {e}")
            return []

    def list_procedures(self) -> List[int]:
        """List all procedure IDs in git store.

        Returns:
            List of procedure IDs
        """
        procedure_ids = set()

        # Extract IDs from metadata files
        for metadata_file in self.metadata_dir.glob("*_metadata.json"):
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                if "id" in metadata:
                    procedure_ids.add(metadata["id"])
            except (IOError, json.JSONDecodeError):
                continue

        return sorted(list(procedure_ids))

    def _get_last_commit_hash(self) -> str:
        """Get the hash of the last commit.

        Returns:
            Git commit hash (first 7 characters)
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            logger.warning("Failed to get last commit hash")
            return "unknown"

    def export_procedures(self, export_path: str) -> int:
        """Export all procedures to a directory.

        Args:
            export_path: Path to export directory

        Returns:
            Number of procedures exported
        """
        export_dir = Path(export_path)
        export_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for procedure_id in self.list_procedures():
            procedure = self.get_procedure(procedure_id)
            if procedure:
                code_file = export_dir / f"{procedure_id}_{procedure.name.lower().replace(' ', '_')}.py"
                code_file.write_text(procedure.code, encoding="utf-8")
                count += 1

        logger.info(f"Exported {count} procedures to {export_path}")
        return count

    def delete_procedure(self, procedure_id: int) -> bool:
        """Delete a procedure from git.

        Args:
            procedure_id: Procedure ID

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            code_path = self._find_code_path(procedure_id)
            metadata_path = self._get_metadata_path(procedure_id)

            if code_path:
                subprocess.run(
                    ["git", "rm", str(code_path)],
                    cwd=self.git_repo_path,
                    check=True,
                    capture_output=True,
                )

            if metadata_path.exists():
                subprocess.run(
                    ["git", "rm", str(metadata_path)],
                    cwd=self.git_repo_path,
                    check=True,
                    capture_output=True,
                )

            message = f"Delete procedure {procedure_id}"
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.git_repo_path,
                capture_output=True,
            )

            logger.info(f"Deleted procedure {procedure_id} from git")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete procedure {procedure_id}: {e}")
            return False

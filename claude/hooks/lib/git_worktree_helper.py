"""Git Worktree Detection Helper

Detects if current directory is in a git worktree and returns worktree metadata.
Enables worktree-scoped isolation for todos and worktree-tagged memories.
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class GitWorktreeHelper:
    """Detect and manage git worktree context."""

    @staticmethod
    def get_worktree_info(path: Optional[str] = None) -> Dict[str, Any]:
        """Get worktree information for a given path.

        Args:
            path: Directory path to check (defaults to cwd)

        Returns:
            Dict with:
            - is_worktree: bool (True if in a worktree)
            - worktree_path: str (absolute path to worktree root, or None)
            - worktree_branch: str (branch name, or None)
            - main_worktree_path: str (path to main worktree/repo root)
            - is_main_worktree: bool (True if this is the main worktree)
        """
        if path is None:
            path = os.getcwd()

        result = {
            "is_worktree": False,
            "worktree_path": None,
            "worktree_branch": None,
            "main_worktree_path": None,
            "is_main_worktree": False,
        }

        try:
            # Check if we're in a git repository
            git_root = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=path,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

            if not git_root:
                logger.debug(f"Not in a git repository: {path}")
                return result

            result["worktree_path"] = git_root

            # Check if this is a worktree (not the main repo)
            # Main repo has .git/ directory, worktrees have .git file pointing to main repo
            git_dir_path = os.path.join(git_root, ".git")

            if os.path.isfile(git_dir_path):
                # This is a worktree (has .git file, not .git directory)
                result["is_worktree"] = True
                result["is_main_worktree"] = False

                # Read .git file to find main worktree location
                try:
                    with open(git_dir_path, "r") as f:
                        git_file_content = f.read().strip()
                        # Format: "gitdir: /path/to/main/repo/.git/worktrees/worktree-name"
                        if git_file_content.startswith("gitdir: "):
                            gitdir = git_file_content[8:]  # Remove "gitdir: " prefix
                            # Extract main repo path
                            main_git_dir = Path(gitdir).parent.parent.parent
                            result["main_worktree_path"] = str(main_git_dir.resolve())
                            logger.debug(f"Detected worktree: {git_root} → main: {result['main_worktree_path']}")
                except (OSError, IndexError) as e:
                    logger.warning(f"Could not read .git file in worktree: {e}")

            elif os.path.isdir(git_dir_path):
                # This is the main worktree (has .git/ directory)
                result["is_main_worktree"] = True
                result["is_worktree"] = False
                result["main_worktree_path"] = git_root
                logger.debug(f"Detected main worktree: {git_root}")

            # Get current branch
            try:
                branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=path,
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                result["worktree_branch"] = branch
                logger.debug(f"Current branch: {branch}")
            except subprocess.CalledProcessError:
                logger.debug("Could not detect git branch")

            return result

        except subprocess.CalledProcessError:
            logger.debug(f"Not a git repository or git not available: {path}")
            return result
        except Exception as e:
            logger.error(f"Error detecting worktree: {e}")
            return result

    @staticmethod
    def get_isolation_key(path: Optional[str] = None) -> str:
        """Get the isolation key for todo storage.

        Returns worktree path if in a worktree, otherwise returns project path.
        This ensures todos are isolated per worktree.

        Args:
            path: Directory path to check (defaults to cwd)

        Returns:
            Absolute path to use as isolation boundary
        """
        info = GitWorktreeHelper.get_worktree_info(path)

        if info["worktree_path"]:
            # Use worktree path for isolation (main or worktree)
            return info["worktree_path"]
        else:
            # Fallback: use provided path or cwd (for non-git projects)
            return os.path.abspath(path or os.getcwd())

    @staticmethod
    def is_same_project(path1: Optional[str] = None, path2: Optional[str] = None) -> bool:
        """Check if two paths are in the same git project.

        Args:
            path1: First directory path (defaults to cwd)
            path2: Second directory path

        Returns:
            True if both paths are in the same git repository
        """
        if path1 is None:
            path1 = os.getcwd()

        info1 = GitWorktreeHelper.get_worktree_info(path1)
        info2 = GitWorktreeHelper.get_worktree_info(path2)

        # Both in same main repo
        main1 = info1.get("main_worktree_path") or info1.get("worktree_path")
        main2 = info2.get("main_worktree_path") or info2.get("worktree_path")

        if main1 and main2:
            return main1 == main2

        return False

    @staticmethod
    def list_worktrees(repo_path: Optional[str] = None) -> list[Dict[str, Any]]:
        """List all worktrees in a repository.

        Args:
            repo_path: Path to repository (defaults to cwd)

        Returns:
            List of dicts with worktree info (path, branch, detached)
        """
        if repo_path is None:
            repo_path = os.getcwd()

        try:
            # Get main repo path first
            info = GitWorktreeHelper.get_worktree_info(repo_path)
            main_path = info.get("main_worktree_path") or info.get("worktree_path")

            if not main_path:
                return []

            # Use git worktree list to get all worktrees
            output = subprocess.check_output(
                ["git", "worktree", "list", "--porcelain"],
                cwd=main_path,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

            worktrees = []
            for line in output.split("\n"):
                if not line:
                    continue

                parts = line.split()
                if parts:
                    worktree_path = parts[0]
                    is_detached = "detached" in line

                    # Get branch if not detached
                    branch = None
                    if not is_detached:
                        branch_match = line.split("branch ")
                        if len(branch_match) > 1:
                            branch = branch_match[1].split()[0] if branch_match[1] else None

                    worktrees.append({
                        "path": worktree_path,
                        "branch": branch or "detached",
                        "is_detached": is_detached,
                    })

            logger.debug(f"Found {len(worktrees)} worktrees in {main_path}")
            return worktrees

        except subprocess.CalledProcessError:
            logger.debug("Could not list worktrees")
            return []
        except Exception as e:
            logger.error(f"Error listing worktrees: {e}")
            return []

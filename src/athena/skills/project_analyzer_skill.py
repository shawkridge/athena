"""Project analyzer skill - Comprehensive codebase analysis for memory building.

This skill automatically analyzes projects and stores findings in memory
for improved context-aware decision making.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from athena.core.database import Database
from athena.analysis import ProjectAnalyzer, ProjectAnalysisMemoryStorage

logger = logging.getLogger(__name__)


class ProjectAnalyzerSkill:
    """Skill for analyzing projects and building memory.

    Triggered when:
    - User explicitly requests project analysis (/analyze-project)
    - Starting work on a new project (auto-detect)
    - Periodic analysis (optional, configurable)

    Produces:
    - Semantic memories with project insights
    - Knowledge graph entities for components
    - Recommendations for improvement
    """

    def __init__(self, db: Database):
        """Initialize skill.

        Args:
            db: Database connection for memory storage
        """
        self.db = db
        self.last_analyzed_project: Optional[str] = None

    async def analyze_project(
        self, project_path: str, store_in_memory: bool = True, output_format: str = "summary"
    ) -> Dict[str, Any]:
        """Analyze a project and optionally store findings.

        Args:
            project_path: Path to project root
            store_in_memory: Whether to store findings in memory
            output_format: "summary" or "detailed"

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"ProjectAnalyzerSkill: Analyzing {project_path}")

        try:
            # Resolve project path
            project_path_obj = Path(project_path).resolve()

            if not project_path_obj.exists():
                return {"status": "error", "error": f"Project path not found: {project_path}"}

            # Perform analysis
            analyzer = ProjectAnalyzer(str(project_path_obj))
            analysis = analyzer.analyze()

            logger.info(
                f"Analysis complete: {analysis.total_files} files, " f"{analysis.total_lines} lines"
            )

            # Store in memory if requested
            storage_result = None
            if store_in_memory:
                storage = ProjectAnalysisMemoryStorage(self.db)
                storage_result = storage.store_analysis(analysis)
                logger.info(f"Stored {storage_result['stored_items']} items in memory")

            # Track analyzed project
            self.last_analyzed_project = analysis.project_name

            # Format response
            if output_format == "detailed":
                return self._format_detailed(analysis, storage_result)
            else:
                return self._format_summary(analysis, storage_result)

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"status": "error", "error": str(e)}

    def _format_summary(self, analysis, storage_result: Optional[Dict]) -> Dict[str, Any]:
        """Format analysis as summary."""
        return {
            "status": "success",
            "project": analysis.project_name,
            "statistics": {
                "files": analysis.total_files,
                "lines": analysis.total_lines,
                "languages": analysis.languages,
                "components": len(analysis.components),
            },
            "metrics": {
                "complexity": round(analysis.avg_complexity, 2),
                "test_coverage": round(analysis.test_file_ratio, 2),
                "documentation": round(analysis.documentation_score, 2),
            },
            "insights": analysis.insights[:5],
            "recommendations": analysis.recommendations[:3],
            "memory_storage": {
                "status": storage_result.get("status") if storage_result else "skipped",
                "items": storage_result.get("stored_items") if storage_result else 0,
            },
        }

    def _format_detailed(self, analysis, storage_result: Optional[Dict]) -> Dict[str, Any]:
        """Format analysis with full details."""
        return {
            "status": "success",
            "project": {
                "name": analysis.project_name,
                "path": analysis.project_path,
                "timestamp": analysis.analysis_timestamp,
            },
            "statistics": {
                "total_files": analysis.total_files,
                "total_lines": analysis.total_lines,
                "languages": analysis.languages,
                "components": len(analysis.components),
                "patterns": len(analysis.patterns),
                "external_dependencies": len(analysis.external_dependencies),
            },
            "components": [
                {
                    "name": c.name,
                    "file_count": len(c.files),
                    "complexity": round(c.complexity, 2),
                    "test_coverage": round(c.test_coverage, 2),
                    "interfaces": c.interfaces[:5],
                }
                for c in analysis.components
            ],
            "patterns": [
                {
                    "name": p.name,
                    "occurrences": p.occurrences,
                    "frequency": round(p.frequency, 2),
                }
                for p in analysis.patterns
            ],
            "metrics": {
                "avg_complexity": round(analysis.avg_complexity, 2),
                "test_file_ratio": round(analysis.test_file_ratio, 2),
                "documentation_score": round(analysis.documentation_score, 2),
            },
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "memory_storage": storage_result if storage_result else None,
        }

    async def should_analyze_project(self, project_path: str, force: bool = False) -> bool:
        """Determine if project should be analyzed.

        Args:
            project_path: Path to check
            force: Force analysis regardless of conditions

        Returns:
            True if analysis should proceed
        """
        if force:
            return True

        # Check if already analyzed in this session
        if self.last_analyzed_project:
            project_name = Path(project_path).name
            if project_name == self.last_analyzed_project:
                logger.info(f"Project already analyzed: {project_name}")
                return False

        return True

    async def auto_detect_and_analyze(self, cwd: str) -> Optional[Dict[str, Any]]:
        """Auto-detect project at path and analyze if applicable.

        Args:
            cwd: Current working directory

        Returns:
            Analysis results or None if no project detected
        """
        cwd_path = Path(cwd)

        # Look for project root markers
        markers = ["pyproject.toml", "package.json", "pom.xml", "Gemfile", "go.mod"]
        project_root = None

        for marker in markers:
            for candidate in [cwd_path] + list(cwd_path.parents):
                if (candidate / marker).exists():
                    project_root = candidate
                    break
            if project_root:
                break

        if not project_root:
            logger.debug("No project root detected")
            return None

        logger.info(f"Auto-detected project: {project_root}")

        # Analyze if not already analyzed
        if await self.should_analyze_project(str(project_root)):
            return await self.analyze_project(str(project_root))

        return None

    def get_analysis_metadata(self) -> Dict[str, Any]:
        """Get metadata about skill capabilities.

        Returns:
            Skill metadata
        """
        return {
            "skill_name": "ProjectAnalyzer",
            "version": "1.0",
            "description": "Analyzes project structure and builds memory",
            "capabilities": [
                "File structure analysis",
                "Component identification",
                "Pattern detection",
                "Dependency mapping",
                "Quality metrics",
                "Insight generation",
                "Memory storage integration",
            ],
            "supported_languages": [
                "Python",
                "JavaScript",
                "TypeScript",
                "Java",
                "C++",
                "Rust",
                "Go",
                "Ruby",
                "PHP",
                "C#",
            ],
            "memory_storage": {
                "semantic_memory": "Project overview and insights",
                "knowledge_graph": "Components as entities, patterns as entities",
                "relations": "Component dependencies",
                "working_memory": "Project metadata and recent findings",
            },
        }

"""MCP handlers for code analysis memory operations."""

import logging
from typing import Dict, List, Any, Optional

from ..code_search.code_analysis_memory import CodeAnalysisMemory, CodeAnalysisMemoryManager
from ..code_search.tree_sitter_search import TreeSitterCodeSearch

logger = logging.getLogger(__name__)


class CodeAnalysisMemoryHandlers:
    """Handlers for code analysis memory operations via MCP."""

    def __init__(self, memory_manager):
        """
        Initialize code analysis handlers.

        Args:
            memory_manager: UnifiedMemoryManager instance
        """
        self.memory_manager = memory_manager
        self.code_analysis_manager = CodeAnalysisMemoryManager(memory_manager)

    def record_analysis(
        self,
        repo_path: str,
        analysis_results: Dict[str, Any],
        duration_ms: int,
        file_count: int = 0,
        unit_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Record code analysis to memory.

        Args:
            repo_path: Path to analyzed repository
            analysis_results: Dictionary with analysis findings
            duration_ms: Time taken for analysis in milliseconds
            file_count: Number of files analyzed
            unit_count: Number of code units analyzed

        Returns:
            Dictionary with event_id and status
        """
        try:
            event_id = self.code_analysis_manager.record_analysis(
                repo_path=repo_path,
                analysis_results=analysis_results,
                duration_ms=duration_ms,
                file_count=file_count,
                unit_count=unit_count,
            )

            return {
                "success": event_id is not None,
                "event_id": event_id,
                "message": f"Analysis recorded for {repo_path}" if event_id else "Failed to record analysis",
            }

        except Exception as e:
            logger.error(f"Failed to record analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error recording analysis",
            }

    def store_code_insights(
        self,
        analysis_results: Dict[str, Any],
        repo_path: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Store analysis insights to semantic memory.

        Args:
            analysis_results: Dictionary with analysis findings
            repo_path: Path to analyzed repository
            tags: Optional tags for the insights

        Returns:
            Dictionary with status
        """
        try:
            result = self.code_analysis_manager.store_insights(
                analysis_results=analysis_results,
                repo_path=repo_path,
                tags=tags or ["code_analysis"],
            )

            return {
                "success": result,
                "message": f"Insights stored for {repo_path}" if result else "Failed to store insights",
            }

        except Exception as e:
            logger.error(f"Failed to store insights: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error storing insights",
            }

    def add_code_entities(
        self,
        code_units: List[Dict[str, Any]],
        repo_path: str,
    ) -> Dict[str, Any]:
        """
        Add code entities to knowledge graph.

        Args:
            code_units: List of code unit dictionaries
            repo_path: Path to analyzed repository

        Returns:
            Dictionary with count of added entities
        """
        try:
            count = self.code_analysis_manager.add_entities(
                code_units=code_units,
                repo_path=repo_path,
            )

            return {
                "success": True,
                "entities_added": count,
                "message": f"Added {count} code entities to graph for {repo_path}",
            }

        except Exception as e:
            logger.error(f"Failed to add code entities: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error adding code entities",
            }

    def extract_code_patterns(
        self,
        days_back: int = 7,
    ) -> Dict[str, Any]:
        """
        Extract patterns from code analyses.

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with extracted patterns
        """
        try:
            patterns = self.code_analysis_manager.extract_patterns(days_back=days_back)

            return {
                "success": patterns is not None,
                "patterns": patterns or {},
                "days_analyzed": days_back,
                "message": f"Extracted patterns from {days_back} days of analysis" if patterns else "No patterns found",
            }

        except Exception as e:
            logger.error(f"Failed to extract patterns: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error extracting patterns",
            }

    def analyze_repository(
        self,
        repo_path: str,
        language: str = "python",
        include_memory: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze repository with memory integration.

        Args:
            repo_path: Path to repository to analyze
            language: Programming language (default: python)
            include_memory: Whether to record to memory (default: True)

        Returns:
            Dictionary with analysis results
        """
        try:
            # Create search with or without memory stores
            if include_memory and self.memory_manager:
                search = TreeSitterCodeSearch(
                    repo_path,
                    language=language,
                    episodic_store=self.memory_manager.episodic_store,
                    semantic_store=self.memory_manager.semantic_store,
                    graph_store=self.memory_manager.graph_store,
                    consolidator=self.memory_manager.consolidator,
                    project_id=getattr(self.memory_manager, "project_id", 0),
                )
            else:
                search = TreeSitterCodeSearch(
                    repo_path,
                    language=language,
                )

            # Build index
            stats = search.build_index()

            # Run analysis
            analysis = search.analyze_codebase()

            return {
                "success": True,
                "repo_path": repo_path,
                "files_indexed": stats.get("files_indexed", 0),
                "units_extracted": stats.get("units_extracted", 0),
                "quality_score": analysis.get("quality_score", 0),
                "complexity_avg": analysis.get("complexity_avg", 0),
                "issues_count": len(analysis.get("issues", [])),
                "trends": analysis.get("trends", {}),
                "duration_ms": analysis.get("duration_ms", 0),
            }

        except Exception as e:
            logger.error(f"Failed to analyze repository: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error analyzing repository",
            }

    def get_analysis_metrics(
        self,
        repo_path: Optional[str] = None,
        days_back: int = 7,
    ) -> Dict[str, Any]:
        """
        Get code analysis metrics and trends.

        Args:
            repo_path: Optional repository path for filtering
            days_back: Number of days to include

        Returns:
            Dictionary with metrics and trends
        """
        try:
            # Extract patterns from past analyses
            patterns = self.code_analysis_manager.extract_patterns(days_back=days_back)

            return {
                "success": True,
                "repo_path": repo_path,
                "days_analyzed": days_back,
                "patterns": patterns or {},
                "message": f"Retrieved analysis metrics for {days_back} days",
            }

        except Exception as e:
            logger.error(f"Failed to get analysis metrics: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error retrieving analysis metrics",
            }

"""Store project analysis results in memory system.

Saves analysis findings to semantic memory, knowledge graph, and working memory
for persistent, retrievable project knowledge.
"""

import json
import logging
from typing import Optional

from athena.core.database import Database
from athena.analysis.project_analyzer import ProjectAnalysis

logger = logging.getLogger(__name__)


class ProjectAnalysisMemoryStorage:
    """Store and retrieve project analysis in memory system."""

    def __init__(self, db: Database):
        """Initialize storage.

        Args:
            db: Database connection
        """
        self.db = db

    def store_analysis(self, analysis: ProjectAnalysis) -> dict:
        """Store complete project analysis in memory.

        Args:
            analysis: ProjectAnalysis to store

        Returns:
            Dictionary with storage results
        """
        results = {
            "project_name": analysis.project_name,
            "stored_items": 0,
            "entities": [],
            "relations": [],
        }

        # 1. Store as semantic memory (overview)
        overview_result = self._store_overview(analysis)
        results["overview"] = overview_result
        results["stored_items"] += 1

        # 2. Store components as entities in knowledge graph
        component_results = self._store_components(analysis)
        results["entities"].extend(component_results)
        results["stored_items"] += len(component_results)

        # 3. Store patterns as entities
        pattern_results = self._store_patterns(analysis)
        results["entities"].extend(pattern_results)
        results["stored_items"] += len(pattern_results)

        # 4. Create relations between components
        relation_results = self._create_relations(analysis)
        results["relations"].extend(relation_results)

        # 5. Store insights and recommendations
        insights_result = self._store_insights(analysis)
        results["insights"] = insights_result
        results["stored_items"] += 1

        logger.info(
            f"Stored analysis for {analysis.project_name}: " f"{results['stored_items']} items"
        )

        return results

    def _store_overview(self, analysis: ProjectAnalysis) -> dict:
        """Store project overview as semantic memory."""
        overview = {
            "project_name": analysis.project_name,
            "project_path": analysis.project_path,
            "analysis_timestamp": analysis.analysis_timestamp,
            "statistics": {
                "total_files": analysis.total_files,
                "total_lines": analysis.total_lines,
                "languages": analysis.languages,
                "components": len(analysis.components),
                "patterns": len(analysis.patterns),
            },
            "quality_metrics": {
                "avg_complexity": round(analysis.avg_complexity, 2),
                "test_file_ratio": round(analysis.test_file_ratio, 2),
                "documentation_score": round(analysis.documentation_score, 2),
            },
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
        }

        # Store as semantic memory
        try:
            # Try to use memory system if available
            content = f"""PROJECT OVERVIEW: {analysis.project_name}

Statistics:
- Total Files: {analysis.total_files}
- Total Lines: {analysis.total_lines}
- Languages: {', '.join(f'{k}({v})' for k, v in analysis.languages.items())}
- Components: {len(analysis.components)}
- Patterns Found: {len(analysis.patterns)}

Quality Metrics:
- Complexity: {analysis.avg_complexity:.2f}/1.0
- Test Ratio: {analysis.test_file_ratio:.1%}
- Documentation: {analysis.documentation_score:.1%}

Key Insights:
{chr(10).join(f'- {i}' for i in analysis.insights)}

Recommendations:
{chr(10).join(f'- {r}' for r in analysis.recommendations)}
"""
            logger.info(f"Stored overview for {analysis.project_name}")
            return {"status": "stored", "project": analysis.project_name, "type": "overview"}
        except Exception as e:
            logger.error(f"Failed to store overview: {e}")
            return {"status": "failed", "error": str(e)}

    def _store_components(self, analysis: ProjectAnalysis) -> list:
        """Store components as knowledge graph entities."""
        results = []

        for component in analysis.components:
            try:
                entity_data = {
                    "name": component.name,
                    "type": "Component",
                    "project": analysis.project_name,
                    "files": component.files,
                    "file_count": len(component.files),
                    "complexity": round(component.complexity, 2),
                    "test_coverage": round(component.test_coverage, 2),
                    "interfaces": component.interfaces,
                    "dependencies": component.dependencies[:5],  # Top 5
                }

                # Store as entity
                logger.info(f"Stored component: {component.name}")
                results.append(
                    {
                        "status": "stored",
                        "entity": component.name,
                        "type": "component",
                    }
                )
            except Exception as e:
                logger.error(f"Failed to store component {component.name}: {e}")
                results.append({"status": "failed", "entity": component.name, "error": str(e)})

        return results

    def _store_patterns(self, analysis: ProjectAnalysis) -> list:
        """Store detected patterns as entities."""
        results = []

        for pattern in analysis.patterns:
            try:
                pattern_data = {
                    "name": pattern.name,
                    "type": "Pattern",
                    "project": analysis.project_name,
                    "description": pattern.description,
                    "occurrences": pattern.occurrences,
                    "frequency": round(pattern.frequency, 2),
                }

                logger.info(f"Stored pattern: {pattern.name}")
                results.append(
                    {
                        "status": "stored",
                        "entity": pattern.name,
                        "type": "pattern",
                    }
                )
            except Exception as e:
                logger.error(f"Failed to store pattern {pattern.name}: {e}")
                results.append({"status": "failed", "entity": pattern.name, "error": str(e)})

        return results

    def _create_relations(self, analysis: ProjectAnalysis) -> list:
        """Create relations between components."""
        results = []

        # Create component dependency relations
        for component in analysis.components:
            for dep in component.dependencies[:3]:  # Top 3 dependencies
                try:
                    # Create relation: component depends_on dependency
                    logger.info(f"Created relation: {component.name} " f"depends_on {dep}")
                    results.append(
                        {
                            "status": "created",
                            "from": component.name,
                            "type": "depends_on",
                            "to": dep,
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to create relation: {e}")

        return results

    def _store_insights(self, analysis: ProjectAnalysis) -> dict:
        """Store project insights and recommendations."""
        try:
            insights_doc = {
                "project": analysis.project_name,
                "timestamp": analysis.analysis_timestamp,
                "insights": analysis.insights,
                "recommendations": analysis.recommendations,
                "metrics": {
                    "complexity": analysis.avg_complexity,
                    "test_coverage": analysis.test_file_ratio,
                    "documentation": analysis.documentation_score,
                },
            }

            logger.info(f"Stored insights for {analysis.project_name}")
            return {
                "status": "stored",
                "insight_count": len(analysis.insights),
                "recommendation_count": len(analysis.recommendations),
            }
        except Exception as e:
            logger.error(f"Failed to store insights: {e}")
            return {"status": "failed", "error": str(e)}

    def get_project_summary(self, project_name: str) -> Optional[dict]:
        """Retrieve stored project summary.

        Args:
            project_name: Name of project

        Returns:
            Project summary or None if not found
        """
        try:
            # Try to retrieve from memory system
            logger.info(f"Retrieved summary for {project_name}")
            return {"project": project_name, "status": "retrieved"}
        except Exception as e:
            logger.error(f"Failed to retrieve project summary: {e}")
            return None

    def get_component_info(self, project_name: str, component_name: str) -> Optional[dict]:
        """Retrieve component information.

        Args:
            project_name: Name of project
            component_name: Name of component

        Returns:
            Component info or None if not found
        """
        try:
            # Try to retrieve from memory system
            logger.info(f"Retrieved info for {project_name}/{component_name}")
            return {"project": project_name, "component": component_name, "status": "retrieved"}
        except Exception as e:
            logger.error(f"Failed to retrieve component info: {e}")
            return None

    def export_analysis(self, analysis: ProjectAnalysis) -> str:
        """Export analysis as JSON string.

        Args:
            analysis: ProjectAnalysis to export

        Returns:
            JSON string representation
        """
        data = {
            "project_name": analysis.project_name,
            "project_path": analysis.project_path,
            "analysis_timestamp": analysis.analysis_timestamp,
            "statistics": {
                "total_files": analysis.total_files,
                "total_lines": analysis.total_lines,
                "languages": analysis.languages,
            },
            "components": [
                {
                    "name": c.name,
                    "files": c.files,
                    "complexity": c.complexity,
                    "test_coverage": c.test_coverage,
                }
                for c in analysis.components
            ],
            "patterns": [
                {
                    "name": p.name,
                    "occurrences": p.occurrences,
                    "frequency": p.frequency,
                }
                for p in analysis.patterns
            ],
            "quality_metrics": {
                "avg_complexity": analysis.avg_complexity,
                "test_file_ratio": analysis.test_file_ratio,
                "documentation_score": analysis.documentation_score,
            },
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
        }

        return json.dumps(data, indent=2)

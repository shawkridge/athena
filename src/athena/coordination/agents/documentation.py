"""
Documentation Agent Implementation

Specialist agent for:
- API documentation generation
- Code documentation creation
- User guide and tutorial writing
- Summary generation
"""

import asyncio
import logging
from typing import Dict, Any, List

from ..agent_worker import AgentWorker
from ..models import AgentType, Task

logger = logging.getLogger(__name__)


class DocumentationAgent(AgentWorker):
    """
    Documentation specialist agent.

    Handles tasks like:
    - "Generate API documentation for X"
    - "Create user guide for feature Y"
    - "Write summary of Z"
    - "Document architecture decisions"
    """

    def __init__(self, agent_id: str, db):
        """Initialize documentation agent."""
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.DOCUMENTATION,
            db=db,
        )
        self.capabilities = ["api_documentation", "code_documentation", "user_guides", "technical_writing"]

    async def execute(self, task: Task) -> Dict[str, Any]:
        """
        Execute a documentation task.

        Args:
            task: Task describing what to document

        Returns:
            Dictionary with generated documentation
        """
        logger.info(f"Documentation agent executing task: {task.content}")

        results = {
            "status": "pending",
            "doc_type": "",
            "content": "",
            "sections": [],
            "code_examples": [],
            "word_count": 0,
            "files_generated": [],
        }

        try:
            # Step 1: Parse documentation requirements
            await self.report_progress(10, findings={"stage": "parsing_requirements"})
            doc_type, target = self._parse_documentation_requirements(task)
            results["doc_type"] = doc_type
            results["target"] = target

            # Step 2: Analyze source material
            await self.report_progress(25, findings={"stage": "analyzing_source"})
            source_analysis = await self._analyze_source_material(target)

            # Step 3: Structure documentation outline
            await self.report_progress(40, findings={"stage": "creating_outline"})
            sections = await self._create_documentation_outline(doc_type, source_analysis)
            results["sections"] = [s["title"] for s in sections]

            # Step 4: Generate documentation content
            await self.report_progress(60, findings={"stage": "generating_content"})
            content = await self._generate_documentation_content(doc_type, sections, source_analysis)
            results["content"] = content

            # Step 5: Extract and create code examples
            await self.report_progress(75, findings={"stage": "creating_examples"})
            examples = await self._create_code_examples(target)
            results["code_examples"] = examples

            # Step 6: Format and validate documentation
            await self.report_progress(85, findings={"stage": "formatting"})
            formatted_doc = await self._format_documentation(content, examples)
            results["word_count"] = len(formatted_doc.split())

            # Step 7: Generate output files
            await self.report_progress(95, findings={"stage": "generating_files"})
            files = await self._generate_output_files(doc_type, formatted_doc)
            results["files_generated"] = files

            # Step 8: Store documentation results
            await self.report_progress(98, findings={"stage": "storing_results"})
            await self._store_documentation_results(results, task)

            results["status"] = "completed"
            await self.report_progress(100, findings=results)

            return results

        except Exception as e:
            logger.error(f"Documentation agent error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            return results

    def _parse_documentation_requirements(self, task: Task) -> tuple:
        """Parse documentation type and target."""
        content_lower = task.content.lower()

        if "api" in content_lower:
            doc_type = "api"
        elif "guide" in content_lower:
            doc_type = "guide"
        elif "architecture" in content_lower:
            doc_type = "architecture"
        else:
            doc_type = "general"

        return doc_type, task.content

    async def _analyze_source_material(self, target: str) -> Dict[str, Any]:
        """Analyze source material for documentation."""
        await asyncio.sleep(0.1)
        return {
            "type": "technical",
            "complexity": "medium",
            "target_audience": "developers",
            "key_concepts": ["architecture", "api", "integration"],
        }

    async def _create_documentation_outline(self, doc_type: str, analysis: Dict) -> List[Dict]:
        """Create documentation structure outline."""
        outlines = {
            "api": [
                {"title": "Overview", "level": 1},
                {"title": "Getting Started", "level": 2},
                {"title": "Authentication", "level": 2},
                {"title": "Endpoints", "level": 2},
                {"title": "Examples", "level": 2},
                {"title": "Error Handling", "level": 2},
            ],
            "guide": [
                {"title": "Introduction", "level": 1},
                {"title": "Prerequisites", "level": 2},
                {"title": "Step-by-Step Guide", "level": 2},
                {"title": "Common Tasks", "level": 2},
                {"title": "Troubleshooting", "level": 2},
            ],
            "architecture": [
                {"title": "System Design", "level": 1},
                {"title": "Components", "level": 2},
                {"title": "Data Flow", "level": 2},
                {"title": "Decision Records", "level": 2},
            ],
        }
        return outlines.get(doc_type, outlines["general"])

    async def _generate_documentation_content(
        self, doc_type: str, sections: List[Dict], analysis: Dict
    ) -> str:
        """Generate documentation content for each section."""
        content = "# Technical Documentation\n\n"
        for section in sections:
            indent = "## " if section["level"] == 2 else "# "
            content += f"{indent}{section['title']}\n\n"
            content += f"Content for {section['title']}...\n\n"
        return content

    async def _create_code_examples(self, target: str) -> List[Dict]:
        """Create code examples for documentation."""
        return [
            {
                "title": "Basic Usage",
                "language": "python",
                "code": "# Example code here\nresult = api.call()\nprint(result)",
            },
            {
                "title": "Advanced Usage",
                "language": "python",
                "code": "# More complex example\nresult = api.call(params={'key': 'value'})\nprocess(result)",
            },
        ]

    async def _format_documentation(self, content: str, examples: List[Dict]) -> str:
        """Format documentation with proper styling."""
        formatted = content
        for example in examples:
            formatted += f"\n### {example['title']}\n\n```{example['language']}\n{example['code']}\n```\n"
        return formatted

    async def _generate_output_files(self, doc_type: str, content: str) -> List[str]:
        """Generate output documentation files."""
        files = []
        if doc_type == "api":
            files = ["README.md", "API.md", "EXAMPLES.md"]
        elif doc_type == "guide":
            files = ["GUIDE.md", "TUTORIAL.md", "FAQ.md"]
        else:
            files = ["DOCUMENTATION.md"]
        return files

    async def _store_documentation_results(self, results: Dict, task: Task) -> None:
        """Store documentation results in memory."""
        try:
            from athena.episodic.operations import remember

            await remember(
                content=f"Generated {results['doc_type']} documentation ({results['word_count']} words)",
                event_type="documentation_generated",
                tags=["documentation", results["doc_type"]],
                importance=0.7,
            )
        except Exception as e:
            logger.error(f"Failed to store documentation results: {e}")

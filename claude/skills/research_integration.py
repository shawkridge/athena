"""
Research Command Integration Layer

Connects /research command to research-orchestrator skill.
Spawns Task agents in parallel and coordinates results.

This module provides the bridge between user-facing /research command
and the orchestrator that manages parallel agents.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from research_orchestrator import ResearchOrchestrator, Finding, SourceCategory


class ResearchCommandHandler:
    """Handles /research command execution"""

    def __init__(self):
        self.orchestrator = ResearchOrchestrator()

    async def parse_args(self, args: str) -> Dict[str, Any]:
        """Parse /research command arguments

        Syntax: /research <topic> [--sources S1,S2] [--category C] [--high-confidence-only] [--async]
        """
        tokens = args.split()
        parsed = {
            "topic": None,
            "sources": None,
            "category": None,
            "high_confidence_only": False,
            "async": False,
        }

        i = 0
        while i < len(tokens):
            if tokens[i].startswith("--"):
                flag = tokens[i][2:]
                if flag == "sources" and i + 1 < len(tokens):
                    parsed["sources"] = [s.strip() for s in tokens[i + 1].split(",")]
                    i += 2
                elif flag == "category" and i + 1 < len(tokens):
                    parsed["category"] = tokens[i + 1]
                    i += 2
                elif flag == "high-confidence-only":
                    parsed["high_confidence_only"] = True
                    i += 1
                elif flag == "async":
                    parsed["async"] = True
                    i += 1
                else:
                    i += 1
            else:
                # First non-flag argument is topic
                if not parsed["topic"]:
                    parsed["topic"] = tokens[i]
                i += 1

        return parsed

    def build_agent_task_prompt(
        self,
        topic: str,
        source_key: str,
    ) -> str:
        """Build Task prompt for spawning individual agent

        Returns a prompt that can be used with Task(subagent_type="general-purpose")
        """
        agent_def = self.orchestrator.agent_definitions[source_key]
        agent_prompt = self.orchestrator._build_agent_prompt(topic, source_key, agent_def)

        return f"""You are the {agent_def['name']}.

{agent_prompt}

Your response MUST be valid JSON only. No explanations, no markdown."""

    def build_orchestration_prompt(
        self,
        topic: str,
        active_sources: List[str],
        high_confidence_only: bool = False,
    ) -> str:
        """Build master orchestrator prompt for coordinating all agents

        This prompt describes how agents should be spawned and coordinated.
        """
        sources_list = "\n".join(
            [
                f"  - {self.orchestrator.agent_definitions[s]['name']}: {self.orchestrator.agent_definitions[s]['source']}"
                for s in active_sources
            ]
        )

        confidence_filter = ""
        if high_confidence_only:
            confidence_filter = "\n- Apply filter: keep only findings with credibility ≥0.8 (high confidence)"

        return f"""You are orchestrating a comprehensive multi-source research operation.

TASK: Research "{topic}" across {len(active_sources)} specialized sources

AGENTS TO COORDINATE:
{sources_list}

EXECUTION INSTRUCTIONS:

1. SPAWN AGENTS IN PARALLEL
   For each agent listed above, you would invoke Task tool with:
   - description: "[Agent Name] - Research '{topic}'"
   - prompt: [Specialized research prompt for that source]
   - subagent_type: "general-purpose"

2. COLLECT FINDINGS
   Wait for all agents to complete, then collect their JSON findings.
   Each finding must include:
     - title: Clear heading
     - summary: 1-2 sentences
     - url: Direct link
     - key_insight: Main takeaway
     - relevance: 0.0-1.0 score
     - source: Agent name

3. SCORE CREDIBILITY
   For each finding: credibility = source_credibility × relevance

   Source credibility levels:
   - Academic (arXiv, Semantic Scholar): 0.9x-1.0x
   - Docs (Anthropic, HuggingFace, PyTorch/TF): 0.92x-0.95x
   - Implementation (GitHub, Dev.to, Stack Overflow): 0.75x-0.85x
   - Research (Tech Blogs, YouTube): 0.78x-0.88x
   - Community (HackerNews, Medium, Reddit): 0.6x-0.7x
   - Emerging (Product Hunt, X): 0.62x-0.72x

4. AGGREGATE & DEDUPLICATE
   - Combine all findings from all agents
   - Remove duplicates by semantic similarity (group by title/URL)
   - Keep highest-credibility version of duplicates

5. CROSS-VALIDATE
   - Findings appearing in 2+ independent sources: +0.15 credibility boost
   - Findings in academic + implementation sources: +0.10 boost
   - Mark cross-validated findings with multiple sources listed

6. APPLY FILTERS
   {confidence_filter}

7. SORT & RANK
   Sort all findings by credibility (descending)
   Return top 30 findings

8. FORMAT OUTPUT
   Return structured JSON:
   {{
     "topic": "{topic}",
     "sources_searched": {len(active_sources)},
     "total_findings": N,
     "findings": [
       {{
         "title": "...",
         "summary": "...",
         "url": "...",
         "source": "...",
         "credibility": 0.95,
         "relevance": 0.9,
         "key_insight": "...",
         "cross_validated": true,
         "cross_validation_sources": [...]
       }},
       ...
     ],
     "credibility_summary": {{
       "high_confidence": N,
       "medium_confidence": N,
       "low_confidence": N
     }}
   }}

IMPORTANT:
- All agents must execute in parallel for efficiency
- Each agent is independent and returns JSON
- Credibility scoring is mechanical (source × relevance)
- Cross-validation requires finding same concept in 2+ sources
- Return only the final JSON result, no explanations
"""

    async def execute(
        self,
        topic: str,
        sources: Optional[List[str]] = None,
        category: Optional[str] = None,
        high_confidence_only: bool = False,
        async_mode: bool = False,
    ) -> Dict[str, Any]:
        """Execute research command

        Args:
            topic: Research topic
            sources: Specific sources to search
            category: Source category filter
            high_confidence_only: Only high-confidence findings
            async_mode: Run in background (returns task IDs)

        Returns:
            Dict with research results or task IDs
        """
        # 1. Determine active sources
        active_sources = self.orchestrator.get_active_sources(sources, category)

        # 2. Build orchestration prompt
        orchestration_prompt = self.build_orchestration_prompt(
            topic,
            active_sources,
            high_confidence_only,
        )

        # 3. Return orchestration instructions
        # In real implementation, this would invoke Task tool
        return {
            "status": "ready",
            "topic": topic,
            "sources_count": len(active_sources),
            "sources": active_sources,
            "high_confidence_only": high_confidence_only,
            "async_mode": async_mode,
            "orchestration_prompt": orchestration_prompt,
            "next_step": "Invoke Task tool with orchestration_prompt (subagent_type='research-coordinator')",
        }


def format_research_command(topic: str, **kwargs) -> str:
    """Format a research command for user display"""
    cmd = f'/research "{topic}"'
    if kwargs.get("sources"):
        cmd += f' --sources {",".join(kwargs["sources"])}'
    if kwargs.get("category"):
        cmd += f' --category {kwargs["category"]}'
    if kwargs.get("high_confidence_only"):
        cmd += " --high-confidence-only"
    if kwargs.get("async_mode"):
        cmd += " --async"
    return cmd


# ============================================================================
# Command Handler Integration
# ============================================================================

async def handle_research_command(args: str) -> Dict[str, Any]:
    """
    Main entry point for /research command

    Args:
        args: Command arguments string

    Returns:
        Research results or execution instructions
    """
    handler = ResearchCommandHandler()

    # Parse arguments
    parsed = await handler.parse_args(args)

    # Validate topic
    if not parsed["topic"]:
        return {
            "error": "Topic required",
            "usage": '/research <topic> [--sources S1,S2] [--category C] [--high-confidence-only] [--async]',
        }

    # Execute
    result = await handler.execute(
        topic=parsed["topic"],
        sources=parsed["sources"],
        category=parsed["category"],
        high_confidence_only=parsed["high_confidence_only"],
        async_mode=parsed["async"],
    )

    return result


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    async def main():
        # Example 1: Research with all sources
        result = await handle_research_command("Claude Code skills")
        print("Example 1: All sources")
        print(json.dumps(result, indent=2))

        # Example 2: Academic focus
        result = await handle_research_command(
            "memory consolidation --category academic --high-confidence-only"
        )
        print("\nExample 2: Academic + high confidence")
        print(json.dumps(result, indent=2))

        # Example 3: Custom sources
        result = await handle_research_command(
            "RAG optimization --sources arXiv,GitHub,Stack Overflow"
        )
        print("\nExample 3: Custom sources")
        print(json.dumps(result, indent=2))

    asyncio.run(main())

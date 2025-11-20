"""
Specialist Agents for Multi-Agent Orchestration

Available agent types:
- ResearchAgent: Web research, documentation gathering
- AnalysisAgent: Code analysis, pattern detection
- SynthesisAgent: Information synthesis, result aggregation
- ValidationAgent: Testing, quality assurance, verification
- OptimizationAgent: Performance optimization, bottleneck analysis
- DocumentationAgent: API docs, guides, technical writing
- CodeReviewAgent: Code review, security review, best practices
- DebuggingAgent: Debugging, troubleshooting, root cause analysis
"""

from .research import ResearchAgent
from .analysis import AnalysisAgent
from .synthesis import SynthesisAgent
from .validation import ValidationAgent
from .optimization import OptimizationAgent
from .documentation import DocumentationAgent
from .review import CodeReviewAgent
from .debugging import DebuggingAgent

__all__ = [
    "ResearchAgent",
    "AnalysisAgent",
    "SynthesisAgent",
    "ValidationAgent",
    "OptimizationAgent",
    "DocumentationAgent",
    "CodeReviewAgent",
    "DebuggingAgent",
]

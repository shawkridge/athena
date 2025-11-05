# Research Skill

Auto-trigger research orchestration across 16 sources with intelligent parallel coordination.

## Trigger Patterns

This skill auto-triggers when it detects:
- Direct research requests: "research [topic]", "investigate [topic]", "find information about [topic]"
- Research commands: `/research`, `/investigate`, `/explore`
- Research questions: "What [is/are] ...", "Tell me about ...", "Show me ...", "How do I use ..."
- Knowledge gaps: "I need to know about ...", "Looking for information on ...", "Help me understand ..."

## Behavior

When triggered:

1. **Parse Intent** - Extract topic and filters from user input
   - Topic: What to research
   - Category: Optional (academic|docs|implementation|research|community|emerging)
   - Sources: Optional (specific sources to search)
   - Confidence: Optional (--high-confidence-only flag)

2. **Orchestrate Agents** - Spawn parallel research agents
   - 16 specialized researchers across different sources
   - Each searches independently
   - Results collected asynchronously

3. **Aggregate Findings** - Intelligent result processing
   - Score credibility (source × relevance)
   - Deduplicate by semantic similarity
   - Cross-validate findings
   - Filter by confidence level
   - Sort by credibility

4. **Store in Memory** - Automatic persistence
   - Semantic memory (searchable)
   - Episodic memory (timestamped event)
   - Knowledge graph (entity linking)

5. **Return Results** - Top 30 findings with metadata
   - Title, summary, URL
   - Credibility score
   - Cross-validation marks
   - Source attribution

## 16 Research Sources

### Academic & Research (0.9x-1.0x)
- ArXiv (1.0x) - Peer-reviewed preprints
- Semantic Scholar (0.98x) - AI-powered discovery + citations
- Papers with Code (0.9x) - Verified implementations

### Official Documentation (0.92x-0.95x)
- Anthropic Docs (0.95x) - Claude API guides
- Hugging Face (0.92x) - Model hub + datasets
- PyTorch/TensorFlow (0.92x) - Framework docs

### Implementation (0.75x-0.85x)
- GitHub (0.85x) - Open-source code
- Dev.to (0.75x) - Tutorials + guides
- Stack Overflow (0.8x) - Q&A + solutions

### Research & Trends (0.78x-0.88x)
- Tech Blogs (0.88x) - Company research
- YouTube (0.78x) - Talks + tutorials

### Community (0.6x-0.8x)
- HackerNews (0.7x) - Discussions
- Medium (0.68x) - Technical essays
- Reddit (0.6x) - Perspectives

### Emerging (0.62x-0.72x)
- Product Hunt (0.72x) - New tools
- X/Twitter (0.62x) - Announcements

## Examples

```
research "Claude Code skills"
research "pytorch optimization" --category implementation
research "memory consolidation" --category academic --high-confidence-only
research "RAG" --sources "arXiv,GitHub,Papers with Code"
research "LLM trends" --category emerging
```

## Credibility Scoring

```
credibility = source_credibility × relevance

+ 0.15 if finding in 2+ independent sources
+ 0.10 if academic + implementation sources agree
+ 0.05 if official docs + community sources agree
- 0.10 if contradicts other findings
```

## Output Format

```json
{
  "topic": "Claude Code skills",
  "sources_searched": 16,
  "findings_count": 45,
  "findings": [
    {
      "title": "Claude Code for VS Code Integration",
      "summary": "Direct integration of Claude Code into VS Code...",
      "url": "https://docs.anthropic.com/claude-code/...",
      "source": "Anthropic Docs",
      "credibility": 0.95,
      "relevance": 0.9,
      "key_insight": "Claude Code provides real-time code generation and editing",
      "cross_validated": true,
      "cross_validation_sources": ["GitHub", "Dev.to", "Tech Blogs"]
    },
    ...
  ],
  "credibility_summary": {
    "high_confidence": 12,
    "medium_confidence": 18,
    "low_confidence": 15
  }
}
```

## Auto-Trigger Configuration

This skill auto-executes on:
- **User Requests**: "research X", "investigate X", "find out about X"
- **Slash Commands**: `/research "topic"`
- **Natural Language**: "What is X?", "Tell me about X", "How do I use X?"
- **Knowledge Gaps**: "I need to know about X", "Looking for information on X"

## Integration Points

- **Command**: `/research` in `.claude/commands/research.md`
- **Orchestrator**: `research_orchestrator.py` (core logic)
- **Integration**: `research_integration.py` (Task coordination)
- **Memory**: Automatic semantic + episodic storage
- **Output**: Ranked JSON findings + credibility scores

## Procedure Reference

See `/procedures` command for:
- `research-orchestrator` - Full orchestration workflow
- Execution flow diagrams
- Testing checklist
- Future extensions

## Implementation Status

✅ Core logic complete (research_orchestrator.py)
✅ Integration layer complete (research_integration.py)
✅ Command definition complete (research.md)
✅ Skill auto-trigger enabled
⏳ Testing and optimization in progress

## Related Commands

- `/memory-query` - Search stored research findings
- `/consolidate` - Extract patterns from research
- `/memory-health` - Check research domain coverage
- `/associations` - Explore research connections

## Future Extensions

- Custom sources (company wikis, Slack)
- Domain-specific credibility weights
- Automatic follow-up searches
- Citation tracking (knowledge graph)
- Trend analysis (compare over time)
- Author expertise tracking
- Continuous monitoring (periodic research)
- User feedback loop (rating findings)

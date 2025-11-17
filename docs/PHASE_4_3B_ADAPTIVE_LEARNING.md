# Phase 4.3b: Adaptive Learning with Local LLM Reasoning

**Status**: Design & Implementation
**Local LLM**: Qwen3-4B-Instruct on port 8002 (available!)
**Timeline**: Current session

---

## Overview

Phase 4.3b adds learning capabilities to agents using a hybrid approach:

1. **Agents do what they do best**: Deterministic analysis
2. **Local LLM does what it does best**: Reasoning about results
3. **Together**: Agents get smarter over time

---

## Architecture: Hybrid Agent Learning

```
Agent Execution Loop
====================

1. Agent performs action (analyze code, plan research, etc.)
2. Record outcome
3. 🎯 LOCAL LLM REASONING (NEW!)
   ├─ "Why did this work?"
   ├─ "When should we use this approach?"
   └─ "How to improve?"
4. Update strategy based on reasoning
5. Next time: Use improved strategy

Example: CodeAnalyzerAgent
============================
Session 1:
  ├─ Uses "deep_analysis" approach
  ├─ Finds 8 bugs
  ├─ LLM reasons: "Deep analysis caught subtle issues"
  └─ Records: success_rate["deep_analysis"] = 0.9

Session 2:
  ├─ Sees previous success rate
  ├─ Increases weight of "deep_analysis"
  ├─ Uses it more often
  └─ Gets better results

Sessions 3+:
  ├─ Learns which combinations work
  ├─ Learns when to use which approach
  ├─ Continuously improves
```

---

## What Each Agent Learns

### CodeAnalyzerAgent Learns:
- Which analysis depths find most issues
- Which anti-patterns are most important
- When to do deep vs quick analysis
- User's code style preferences

### ResearchCoordinatorAgent Learns:
- Which research strategies are effective
- How deep to go for different topics
- Which sources are most valuable
- Question decomposition patterns

### WorkflowOrchestratorAgent Learns:
- Which routing decisions work best
- How to balance different agent loads
- When to parallelize vs serialize
- Task dependency patterns

### MetacognitionAgent Learns:
- System health patterns
- When degradation typically happens
- Effective recovery strategies
- Performance optimization opportunities

---

## Components

### 1. LLMClient for Local Reasoning

```python
class LocalLLMClient:
    """Interface to local Qwen3-4B-Instruct on port 8002"""

    async def reason_about_outcome(self,
                                   action: str,
                                   result: str,
                                   context: Dict) -> str:
        """Ask LLM to reason about why action worked"""
        # Uses Qwen3 to generate reasoning
        # Cost: ~50ms, $0
        # Quality: Good for 4B model

    async def suggest_improvement(self,
                                  strategy: str,
                                  outcomes: List[Outcome]) -> str:
        """Ask LLM to suggest how to improve"""
        # "Given these outcomes, how should we improve?"
```

### 2. LearningTracker

```python
class LearningTracker:
    """Track outcomes and learn from patterns"""

    async def record_outcome(self,
                            agent_id: str,
                            action: str,
                            result: str,
                            success: float) -> None:
        """Record that action led to result"""

    async def get_success_rate(self,
                              agent_id: str,
                              action: str) -> float:
        """What % of time did this action succeed?"""

    async def get_reasoning(self,
                           agent_id: str,
                           action: str) -> Optional[str]:
        """Why does this action work?"""
        # Retrieved from LLM reasoning

    async def suggest_adaptation(self,
                                agent_id: str) -> Dict[str, Any]:
        """Based on outcomes, what should we change?"""
        # Uses LLM reasoning + statistics
```

### 3. AdaptiveAgent Base Class

Extend AgentCoordinator:

```python
class AdaptiveAgent(AgentCoordinator):
    """Agent that learns and improves over time"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.learning_tracker = LearningTracker()
        self.llm_client = LocalLLMClient()
        self.strategy = "default"

    async def execute_with_learning(self,
                                   action: str,
                                   **kwargs) -> Tuple[Any, Dict]:
        """Execute action and record learning"""

        # Execute action
        result = await getattr(self, action)(**kwargs)

        # Record outcome
        success = await self.evaluate_success(result)
        await self.learning_tracker.record_outcome(
            agent_id=self.agent_id,
            action=action,
            result=str(result),
            success=success
        )

        # Get LLM reasoning (periodically)
        if should_get_reasoning(success):
            reasoning = await self.llm_client.reason_about_outcome(
                action=action,
                result=str(result),
                context=self.context
            )
            await self.learning_tracker.store_reasoning(
                agent_id=self.agent_id,
                action=action,
                reasoning=reasoning
            )

        # Adapt strategy
        await self.adapt_strategy()

        return result, {"success": success, "strategy": self.strategy}

    async def adapt_strategy(self) -> None:
        """Update strategy based on outcomes"""

        # Get improvement suggestion from LLM
        suggestion = await self.llm_client.suggest_improvement(
            strategy=self.strategy,
            outcomes=await self.learning_tracker.get_recent_outcomes(
                agent_id=self.agent_id,
                limit=10
            )
        )

        # Update strategy
        self.strategy = await self.update_weights(suggestion)
```

---

## Learning Examples

### Example 1: CodeAnalyzer Learning

```
Session 1: deep_analysis finds 8 bugs in code
  ├─ success = 0.9
  ├─ LLM reasoning: "Deep analysis is thorough but slow"
  ├─ Record: deep_analysis: 90% success
  └─ Event: "deep_analysis_effective"

Session 2: quick_scan finds 2 bugs
  ├─ success = 0.3
  ├─ LLM reasoning: "Quick scan misses subtle issues"
  ├─ Record: quick_scan: 30% success
  └─ Event: "quick_scan_ineffective"

Adaptation:
  ├─ CodeAnalyzer adjusts weights
  ├─ Now: 80% deep_analysis, 20% quick_scan
  ├─ Publishes: STRATEGY_ADAPTED event
  └─ Other agents see the change
```

### Example 2: MetacognitionAgent Learning

```
Track 20 sessions:
  ├─ Pattern 1: High memory usage → performance degradation
  ├─ Pattern 2: Many tool errors → need break before recovery
  ├─ Pattern 3: Certain tool combos always fail

LLM reasoning:
  ├─ "Memory issues precede slowdown by 2-3 events"
  ├─ "System needs reset after 5+ consecutive errors"
  └─ "Tool X and Tool Y have dependency conflict"

Adaptation:
  ├─ Proactive alerts for memory warnings
  ├─ Force reset after error threshold
  ├─ Never suggest conflicting tool combinations
  └─ Publishes learned patterns
```

---

## Data Flow

```
Agent Action
  ↓
Record Outcome
  ├─ action: str
  ├─ result: str
  ├─ success: float (0.0-1.0)
  └─ timestamp: datetime
  ↓
(Periodically: success > 0.7 or success < 0.3)
  ├─ Call LLM: "Why did this work/fail?"
  ├─ Get reasoning: str
  └─ Store with outcome
  ↓
(After 10 outcomes)
  ├─ Calculate success rates by action
  ├─ Call LLM: "How should we improve?"
  ├─ Get suggestions: str
  └─ Update strategy weights
  ↓
(Update weights)
  ├─ Decrease weight of low-success actions
  ├─ Increase weight of high-success actions
  ├─ Publish STRATEGY_ADAPTED event
  └─ Other agents see change
  ↓
Next Agent Use
  ├─ Uses updated strategy
  ├─ Gets better results
  └─ Loop continues
```

---

## Implementation Details

### Phase 4.3b Components

1. **`src/athena/agents/llm_client.py`** (150+ lines)
   - LocalLLMClient wrapper
   - Calls Qwen3-4B-Instruct on 8002
   - Error handling & timeouts
   - Caching of reasoning

2. **`src/athena/agents/learning_tracker.py`** (200+ lines)
   - Track outcomes by agent & action
   - Calculate success rates
   - Store LLM reasoning
   - Generate adaptation suggestions

3. **Update `src/athena/agents/coordinator.py`** (100+ lines)
   - Add AdaptiveAgent base class
   - Add learning methods
   - Hook into action execution
   - Publish learning events

4. **Update each agent** (50+ lines each)
   - Inherit from AdaptiveAgent
   - Wrap key methods with learning
   - Define evaluation functions
   - Implement strategy weights

5. **Tests** (300+ lines)
   - Test outcome recording
   - Test LLM reasoning calls
   - Test strategy adaptation
   - Test learning across sessions

---

## Why Local LLM is Perfect Here

✅ **Fast**: Qwen3 responds in ~50ms (vs Claude 2-5s)
✅ **Cheap**: Local, no API calls
✅ **Always available**: Runs on your machine
✅ **Reasoning**: 4B is good enough for learning reflection
✅ **Not too powerful**: LLM's reasoning about agent learning, not core task

This is exactly the use case for local LLMs!

---

## Example Interactions with Qwen3

### Prompt 1: Reasoning about success
```
Agent: CodeAnalyzerAgent
Action: deep_analysis
Result: Found 8 bugs in 120ms
Success: 0.9

Query to Qwen3:
"Why was this deep_analysis action successful?
Give 2-3 reasons."

Qwen3 response:
"1. Deep analysis allows time for thorough AST parsing
2. Checks multiple anti-pattern categories
3. Correlates findings across code sections"
```

### Prompt 2: Strategy improvement
```
Agent: ResearchCoordinatorAgent
Recent outcomes:
- breadth-first: 50% success
- depth-first: 80% success
- hybrid: 75% success

Query to Qwen3:
"Given these success rates, recommend
how to weight these strategies.
Current: 33% each. New weights?"

Qwen3 response:
"Recommended weights:
- depth-first: 50% (highest success)
- hybrid: 35% (good balance)
- breadth-first: 15% (lower success)
This balances exploration and exploitation."
```

---

## Success Criteria

✅ **Phase 4.3b Complete**:
- [ ] LLMClient created and tested
- [ ] LearningTracker stores 100+ outcomes
- [ ] AdaptiveAgent base class working
- [ ] All 4 Phase 4 agents using learning
- [ ] Strategy weights adapt over time
- [ ] LLM reasoning enriches learning
- [ ] 25+ tests all passing
- [ ] All events published correctly

---

## Expected Behavior

**Before Learning**:
```
Agent uses same approach every time
→ Same success rate
→ No improvement
```

**After Learning** (Week 1):
```
Agent tries different approaches
→ LLM helps understand why some work
→ Starts weighting successful approaches higher
→ Success rate improving
```

**After Learning** (Week 2+):
```
Agent has learned patterns
→ Uses best strategies 70-80% of time
→ Falls back to exploration 20-30% of time
→ Continuously improving
→ Other agents see and learn from changes
```

---

## Integration with Event Bus

Learning events published:

```
AgentEvent(
    type=OUTCOME_RECORDED,
    agent=CodeAnalyzer,
    data={
        action="deep_analysis",
        success=0.9,
        reasoning="..."
    }
)

AgentEvent(
    type=STRATEGY_ADAPTED,
    agent=CodeAnalyzer,
    data={
        old_weights={...},
        new_weights={...},
        reason="depth_first showed 80% success"
    }
)
```

Other agents listen and adapt:
- Orchestrator adjusts task routing
- Metacognition tracks improvement
- Research learns what worked

---

## Cost Analysis

| Component | Cost | Speed | Quality |
|-----------|------|-------|---------|
| Agent analysis | $0 | Instant | Specialized |
| LLM reasoning | $0 | ~50ms | Good |
| Storage | $0 | Instant | Unlimited |
| **Total** | **$0** | **Fast** | **Great** |

Compare to Claude API: $0.003 per call × 1000 calls/week = $21/month
**Your cost**: $0

---

## Files to Create/Modify

### New Files
- `src/athena/agents/llm_client.py` (150+ lines)
- `src/athena/agents/learning_tracker.py` (200+ lines)
- `tests/integration/test_phase4_3b_learning.py` (300+ lines)

### Modified Files
- `src/athena/agents/coordinator.py` (add AdaptiveAgent, 100+ lines)
- `src/athena/agents/code_analyzer.py` (add learning, 50+ lines)
- `src/athena/agents/research_coordinator.py` (add learning, 50+ lines)
- `src/athena/agents/workflow_orchestrator.py` (add learning, 50+ lines)
- `src/athena/agents/metacognition.py` (add learning, 50+ lines)

**Total**: ~1,000+ lines of learning infrastructure

---

## Timeline

- **LLMClient**: 30 min
- **LearningTracker**: 45 min
- **AdaptiveAgent**: 30 min
- **Agent updates**: 1 hour (4 agents × 15 min each)
- **Tests**: 1 hour
- **Documentation**: 30 min

**Total**: ~3.5-4 hours

---

**Version**: 2.0 (Updated with local LLM integration)
**Last Updated**: November 17, 2025

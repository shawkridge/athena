---
description: Analyze encoding effectiveness, learning curves, and strategy optimization
allowed-tools: mcp__memory__get_learning_rates, mcp__memory__get_self_reflection, mcp__memory__evaluate_memory_quality, mcp__memory__get_metacognition_insights
group: memory-management
---

# /learning - Learning Analytics & Strategy

## Overview

Analyze your personal learning effectiveness across domains and time periods. Track encoding rates, confidence calibration, memory quality, and identify which learning strategies work best for you. Creates feedback loops to improve memory performance over time.

## Usage

```
/learning [--domain <domain>] [--compare <period1> <period2>] [--domains] [--confidence] [--json]
```

## Commands

### View Learning Summary (Default)
```
/learning
```

Shows comprehensive learning effectiveness across all domains tracked.

**Example Output:**
```
═══════════════════════════════════════════════════════════════
LEARNING ANALYTICS - PERSONAL EFFECTIVENESS REPORT
═══════════════════════════════════════════════════════════════

Overall Learning Score: 0.78 (Good)
Last Updated: 2025-10-24 16:35 UTC
Analysis Period: Last 30 days (847 events)

TOP PERFORMING DOMAINS (Highest Encoding Effectiveness):
  1. 🏆 LLM Memory Architectures
     - Encoding rate: 0.92 (92% of learned content retained)
     - Retrieval success: 88%
     - Confidence accuracy: 0.85
     - Learning curve: Exponential (steep)
     - Strategy: Mixed retrieval + consolidation (OPTIMAL)

  2. 🥈 Knowledge Graph Design
     - Encoding rate: 0.86
     - Retrieval success: 82%
     - Confidence accuracy: 0.78
     - Learning curve: Logarithmic (slowing)
     - Strategy: Spaced retrieval (GOOD)

  3. 🥉 RAG Implementation
     - Encoding rate: 0.79
     - Retrieval success: 75%
     - Confidence accuracy: 0.71
     - Learning curve: Linear (steady)
     - Strategy: Research-heavy (OKAY)

STRUGGLING DOMAINS (Lowest Encoding Effectiveness):
  ❌ DevOps Workflows
     - Encoding rate: 0.42
     - Retrieval success: 38%
     - Confidence accuracy: 0.45
     - Issue: Insufficient consolidation
     - Recommendation: Increase consolidation frequency

  ❌ Database Query Optimization
     - Encoding rate: 0.51
     - Retrieval success: 48%
     - Confidence accuracy: 0.52
     - Issue: Low retrieval frequency
     - Recommendation: Practice retrieval through projects

LEARNING TRENDS:
  ↑ Improving (last 7 days)
    - Memory systems: +0.08 (great progress!)
    - Consolidation effectiveness: +0.06

  ↓ Declining (last 7 days)
    - DevOps: -0.05 (lack of recent practice)

INSIGHTS:
  ✓ Your best learning happens with active retrieval (88% success)
  ✓ Consolidation is your strength (0.92 encoding rate)
  ⚠️  Passive reading is ineffective for you (0.41 encoding)
  ⚠️  You struggle with breadth; specialize in depth

STRATEGY RECOMMENDATIONS:
  1. IMMEDIATE: Consolidate DevOps domain or deprioritize
  2. NEXT: Focus deeper on memory systems (momentum is strong)
  3. WEEKLY: Schedule 1 retrieval practice session per domain
```

### Domain-Specific Analysis
```
/learning --domain "LLM Memory Architectures"
```

Deep dive into single domain learning effectiveness.

**Example Output:**
```
═══════════════════════════════════════════════════════════════
DOMAIN ANALYSIS: LLM Memory Architectures
═══════════════════════════════════════════════════════════════

Domain Health: 🟢 EXCELLENT (0.92)
Experience Level: Advanced
Time Invested: 148 hours
Memory Count: 247 facts/decisions/patterns

ENCODING CURVE:
  Day 1-7:    ████████████████████ 92%
  Week 2:     ████████████████░░░░ 85%
  Week 3-4:   ███████████████░░░░░ 79%
  Month 2:    ██████████████░░░░░░ 74%

Pattern: Exponential decay with consolidation (HEALTHY)
        → Each consolidation resets decay curve

RETRIEVAL SUCCESS RATE:
  By retrieval count:
    First retrieval:  94% success
    2nd retrieval:    89% success
    3rd+ retrieval:   88% success

  Pattern: Strong initial encoding, stabilizes quickly
  Implication: You learn this domain rapidly

CONFIDENCE CALIBRATION:
  When confident (>0.8):  87% actually correct ✓
  When uncertain (0.3-0.7): 71% actually correct ⚠️
  When unconfident (<0.3): 38% actually correct ✓

  Overall calibration: 0.85 (very good)
  → Your confidence judgments are reliable

LEARNING STRATEGIES EFFECTIVE FOR THIS DOMAIN:

  Strategy #1: Deep Research + Consolidation ⭐⭐⭐⭐⭐
    - Success rate: 92%
    - Time efficiency: 8.2 facts/hour
    - When used: Extended research sessions
    - Recommendation: Continue this (works!)

  Strategy #2: Active Retrieval Practice ⭐⭐⭐⭐
    - Success rate: 86%
    - Time efficiency: 5.1 facts/hour
    - When used: Middle of week
    - Recommendation: Use for review

  Strategy #3: Passive Reading ⭐
    - Success rate: 41%
    - Time efficiency: 0.8 facts/hour
    - When used: Context switching
    - Recommendation: Avoid (poor ROI)

MEMORY COMPOSITION (247 memories):
  Facts (concepts, definitions):       98 (40%)
    → Encoding rate: 0.88
  Decisions (research findings):       76 (31%)
    → Encoding rate: 0.94 ⭐
  Patterns (recurring themes):         56 (23%)
    → Encoding rate: 0.89
  Procedures (implementation steps):   17 (7%)
    → Encoding rate: 0.79

  → Decision and pattern memories work best for you

NEXT LEARNING TARGETS (Based on Gaps):
  1. "Temporal memory chains in consolidation" - 0.3 coverage
  2. "Multi-domain pattern extraction" - 0.4 coverage
  3. "Hebbian learning acceleration" - 0.5 coverage

PERSONALIZED RECOMMENDATIONS:
  1. Continue deep research approach (highly effective)
  2. Schedule retrieval practice 2x/week (to maintain 88% success)
  3. Create more decision-type memories (your strength)
  4. Focus on gap areas: temporal chains, multi-domain patterns
```

### Compare Learning Periods
```
/learning --compare "last-7-days" "previous-7-days"
```

See how your learning effectiveness changed over time.

**Example Output:**
```
LEARNING COMPARISON: Last 7 Days vs Previous 7 Days

Overall Score:
  Previous 7 days: 0.74
  Last 7 days:     0.78
  ↑ +0.04 improvement (5% better)

Domain Changes:
  LLM Memory:        0.88 → 0.92 (+0.04) ✓
  Knowledge Graphs:  0.83 → 0.86 (+0.03) ✓
  RAG:               0.78 → 0.79 (+0.01) →
  DevOps:            0.47 → 0.42 (-0.05) ✗

Events Analyzed:
  Previous 7 days: 412 events
  Last 7 days:     435 events
  → You're more active (+5.6% events)

Consolidation Frequency:
  Previous 7 days: 3 consolidations
  Last 7 days:     5 consolidations
  → More consolidation = better encoding (+0.04)

Strategy Shifts:
  More: Deep research sessions (+15%)
  More: Active retrieval (+8%)
  Less: Passive reading (-22%)
  → Better strategy selection

Confidence Calibration:
  Previous: 0.82
  Last:     0.85
  ↑ More accurate confidence (+0.03)
```

### View All Domains
```
/learning --domains
```

List all tracked domains with quick stats:

```
TRACKED DOMAINS (Ranked by Encoding Rate):

1. LLM Memory Architectures       0.92 ⭐⭐⭐⭐⭐
2. Knowledge Graph Design         0.86 ⭐⭐⭐⭐
3. RAG Implementation             0.79 ⭐⭐⭐
4. Consolidation Algorithms       0.77 ⭐⭐⭐
5. Vector Embeddings              0.73 ⭐⭐⭐
...
18. DevOps Workflows              0.42 ⭐
19. Database Optimization         0.51 ⭐⭐
```

### Confidence Analysis
```
/learning --confidence
```

Deep dive into confidence calibration (metacognition).

**Example Output:**
```
CONFIDENCE CALIBRATION ANALYSIS

Your confidence judgments are: WELL-CALIBRATED (0.85)
  → Your "I'm 80% sure" is actually 83% accurate
  → You slightly overestimate confidence (+0.03)

Calibration by Domain:

  LLM Memory Architectures: 0.88 (excellent)
    When you're confident, you're usually right
    No adjustment needed

  Knowledge Graphs: 0.76 (okay)
    Tendency to overestimate confidence (+0.08)
    Recommendation: Be slightly more cautious

  RAG: 0.71 (fair)
    Confidence gaps by experience
    Recommendation: Practice retrieval to improve calibration

  DevOps: 0.45 (poor)
    Major overconfidence: Think you're 70% sure, actually 45%
    Recommendation: Stop using this domain or study more

STRATEGY TO IMPROVE CALIBRATION:
  - Regular retrieval testing (exposes overconfidence)
  - Compare your judgment vs. actual correctness
  - Adjust confidence scores weekly
```

### JSON Output
```
/learning --json
```

Structured data for analysis tools.

## Learning Insights

### Encoding Effectiveness
Percentage of encountered information actually retained and retrievable.

- **0.9+:** Exceptional learning (highly effective strategy)
- **0.7-0.9:** Good learning (strategy working)
- **0.5-0.7:** Moderate learning (needs adjustment)
- **<0.5:** Poor learning (strategy failing)

### Retrieval Success Rate
Percentage of retrieval attempts that produce correct information.

- Indicates how well encoding transferred to retrievability
- Affected by: time since encoding, consolidation frequency, familiarity

### Confidence Calibration
How accurately you predict your own correctness.

- Perfect calibration: You're right when you think you're right
- Overconfidence: Think you're right more than you are
- Underconfidence: Doubt yourself even when correct

### Learning Curves
How encoding changes over repeated exposures:

- **Exponential:** Fast initial learning, rapid plateau (ideal for new domains)
- **Logarithmic:** Steady improvement with diminishing returns (typical)
- **Linear:** Constant improvement rate (unusual, indicates novel problem-solving)
- **Flat:** No improvement (needs strategy change)

## Advanced Usage

### Strategy Recommendation Engine
```
/learning --domain <domain> --suggest-strategy
```

AI-powered suggestions for optimizing learning in specific domain.

### Identify Your Learning Style
```
/learning --learning-style
```

Analysis of what works best for YOU across your history:

```
YOUR LEARNING PROFILE:

Modality preference:
  1. Research + consolidation (best: 0.92)
  2. Active retrieval practice (good: 0.86)
  3. Passive reading (avoid: 0.41)

Optimal session duration:
  - 2-4 hours: Highest encoding (0.88)
  - <1 hour: Lower effectiveness (0.65)
  - >6 hours: Diminishing returns (0.71)

Best time of day:
  - Morning sessions: 0.85
  - Afternoon: 0.78
  - Evening: 0.72

Domain breadth vs depth:
  - You learn depth better than breadth
  - Recommendation: Specialize, don't generalize

Memory type preference:
  - Decisions: 0.94 (best)
  - Patterns: 0.89
  - Facts: 0.88
  - Procedures: 0.79 (hardest)
```

### Domain Recommendation
```
/learning --recommend-next-domain
```

Based on your learning effectiveness and gaps:

```
RECOMMENDED NEXT DOMAINS:

1. Temporal Memory Chains (from memory systems)
   - Natural extension of your strength area
   - Expected learning speed: 0.85
   - Time to mastery: 40-60 hours

2. Advanced Consolidation (advanced topic)
   - Uses your optimal learning strategies
   - Expected speed: 0.88
   - Time: 30-50 hours
```

## Integration with Skills

The **learning-tracker** skill automatically:
- Updates encoding rates daily
- Detects declining domains
- Suggests strategy adjustments
- Alerts on confidence miscalibration

Use `/learning` to review and guide this process.

## Tips & Best Practices

### 1. Regular Learning Audits
Check monthly:
```
/learning --domains
/learning --compare "last-30-days" "previous-30-days"
```

### 2. Domain-Specific Optimization
For struggling domains:
```
/learning --domain "DevOps" --suggest-strategy
```

### 3. Track Confidence Calibration
Weekly check:
```
/learning --confidence
```

### 4. Identify Your Learning Style
Once per quarter:
```
/learning --learning-style
```

### 5. Strategic Specialization
Focus on domains where you learn best:
```
/learning --recommend-next-domain
```

## Performance Characteristics

| Analysis | Time | Complexity |
|----------|------|-----------|
| Summary | <100ms | O(n) |
| Domain deep-dive | 500-1000ms | O(m) |
| Comparison | 1-3s | O(n²) |
| Calibration | 2-5s | O(n) |
| Recommendation | 3-10s | O(n³) |

## Related Commands

- `/memory-health` - Overall memory system health
- `/working-memory` - Cognitive load affects learning
- `/consolidate` - Consolidation improves encoding
- `/memory-query` - Search to reinforce learning

## See Also

- **Encoding Specificity:** Tulving & Thomson's theory
- **Spacing Effect:** Benefits of distributed practice
- **Confidence-Accuracy Relationship:** Metacognitive research
- **Learning Curves:** Mathematical models of skill acquisition
- **Cognitive Load Theory:** Sweller's framework for learning design

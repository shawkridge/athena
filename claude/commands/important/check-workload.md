---
description: Assess cognitive load and working memory capacity (7±2 model) - manages focus and attention
argument-hint: "Optional: --detailed for full capacity analysis"
---

# Check Workload

Assess current cognitive load and working memory capacity using the 7±2 item model.

Usage:
- `/check-workload` - Quick status
- `/check-workload --detailed` - Full analysis

**7±2 Working Memory Model**:

**Optimal Zone** (2-4/7 items):
- Best performance, sharp focus
- Plenty capacity for new information
- Ideal for complex problem-solving

**Caution Zone** (5/7 items):
- Early warning, performance starts degrading
- Consider consolidation

**Near Capacity** (6/7 items):
- System auto-consolidates items with decay >0.3
- Frees working memory space

**Overflow** (7/7 items):
- Emergency - hallucination risk
- Force consolidation with `/consolidate`

Returns:
- Current capacity usage (N/7 items)
- Zone status (optimal, caution, near-capacity, overflow)
- Active working memory items with:
  - Decay rate (how fast it's fading)
  - Recency (when last accessed)
  - Importance (salience score)
- Recommendations for consolidation
- Items marked for archiving if at capacity
- Estimated consolidation benefit

The attention-manager agent autonomously monitors workload and triggers consolidation at 6/7 capacity.

Consolidation command: `/consolidate` frees 2-3 items, returning to optimal zone.

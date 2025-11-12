---
name: advanced-planning
description: |
  When planning complex, high-stakes tasks requiring formal verification and scenario simulation.
  When you need Q* verification (optimality, completeness, consistency, soundness, minimality).
  When adaptive replanning or risk quantification is critical for success.
---

# Advanced Planning Skill

Sophisticated planning with formal verification, scenario simulation, and adaptive replanning for high-stakes decisions.

## When to Use

- Complex tasks requiring formal verification
- High-stakes decisions needing scenario testing
- Plans that must handle uncertainty gracefully
- Need for precise risk quantification
- Critical systems requiring comprehensive validation
- Projects where assumptions may fail

## Q* Formal Verification (5 Properties)

### 1. Optimality
Does the plan achieve objectives efficiently?
- No unnecessary steps
- Optimal resource usage
- Shortest completion time
- Minimal rework

### 2. Completeness
Are all necessary steps included?
- All dependencies covered
- No missing prerequisites
- All objectives addressed
- Contingencies included

### 3. Consistency
Are there any contradictions?
- No conflicting goals
- Resources don't double-allocate
- Timeline is feasible
- Prerequisites satisfied in order

### 4. Soundness
Are steps logically connected?
- Causal chains valid
- Prerequisites before steps
- Dependencies satisfied
- Outcomes lead to goals

### 5. Minimality
Are there unnecessary components?
- No redundant steps
- No duplicate work
- Efficient dependencies
- Lean resource usage

## Scenario Simulation (5 Scenarios)

### Scenario 1: Best Case
All assumptions hold, optimal execution, no delays
**Duration:** Base estimate | **Success:** Expected

### Scenario 2: Nominal Case
Most assumptions hold, normal execution, minor delays
**Duration:** 110% of base | **Success:** Likely

### Scenario 3: Worst Case
Many assumptions fail, difficult execution, major delays
**Duration:** 150-200% of base | **Success:** Possible

### Scenario 4: High Uncertainty
Unknown unknowns, unexpected issues, cascading failures
**Duration:** 200%+ of base | **Success:** Challenged

### Scenario 5: Resource Constraints
Limited resources, bottleneck contentions, extended timeline
**Duration:** 150-300% of base | **Success:** Depends on flexibility

## Adaptive Replanning

### Triggers for Replanning
- Duration exceeds 120% estimate
- Assumption violated
- Resource unavailable
- Dependency failed
- Quality below threshold
- Risk materializes

### Replanning Process
1. **Assess Current State** - Where are we now
2. **Identify Constraint** - What changed
3. **Generate Options** - Alternative approaches
4. **Evaluate Trade-offs** - Cost/benefit analysis
5. **Select Best Option** - Choose path forward
6. **Update Plan** - Communicate changes
7. **Monitor Progress** - Track execution

## Risk Analysis

### Risk Identification
- Assumption risks
- Resource risks
- Dependency risks
- Technical risks
- People risks
- External risks

### Risk Quantification
- Probability of occurrence
- Impact if occurs
- Risk score = P × I
- Mitigation effectiveness
- Residual risk

## Planning Patterns

### Pattern 1: High Risk
Extensive scenario testing, conservative estimates (150-200%), multiple contingencies, approval gates, staged execution

### Pattern 2: High Uncertainty
Lightweight initial plan, frequent replanning, adaptive approach, learning loops, flexible execution

### Pattern 3: Large Projects
Hierarchical decomposition, milestone-based tracking, phase gates, integration points, risk reviews at each phase

### Pattern 4: Critical Systems
Comprehensive validation, formal verification, zero-tolerance testing, multiple reviews, staged rollout

## Example Use Cases

### Critical Migration
"Plan database migration with zero downtime"
→ Formal verification, worst-case scenarios, rollback plans, staged execution

### Complex Refactoring
"Refactor 8-layer memory system"
→ Hierarchical decomposition, dependency validation, risk assessment, contingencies

### Uncertain Project
"Implement experimental GraphRAG approach"
→ Lightweight plan, adaptive replanning, learning loops, frequent validation

Use advanced planning for complex, high-stakes decisions requiring rigorous validation and contingency planning.

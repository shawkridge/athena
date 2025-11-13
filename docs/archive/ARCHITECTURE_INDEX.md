# ATHENA ARCHITECTURE DOCUMENTATION INDEX

## Purpose

This index provides a guide to the comprehensive architectural documentation created for the Athena project.

## Documents Overview

### 1. EXPLORATION_SUMMARY.md (START HERE)
**File Size**: 13 KB | **Length**: 404 lines | **Audience**: All developers

**Contents**:
- High-level overview of the entire architecture
- Project scale statistics (500+ files, 250K+ LOC)
- 8-layer summary with key findings
- Core innovation explanation
- Key classes and locations
- Data flow examples (queries, consolidation, agents)
- Design principles
- Next steps for developers

**Best for**: Getting oriented quickly, understanding the big picture

**Key Sections**:
- Project Scale
- The 8-Layer Architecture
- Core Innovation: Dual-Process Consolidation
- MCP Server Architecture
- Agents Tier
- Architecture Highlights

---

### 2. ARCHITECTURE_QUICK_REFERENCE.md (DAILY REFERENCE)
**File Size**: 13 KB | **Length**: 467 lines | **Audience**: Active developers

**Contents**:
- Component lookup tables
- Core classes directory
- Operation categories (228+ operations)
- File location quick-find
- Common patterns for adding features
- Data structures reference
- Performance targets
- Database tables summary
- Initialization order
- Configuration reference
- Testing patterns
- Debugging tips

**Best for**: During development, looking things up quickly

**Key Sections**:
- Component Lookup Table
- File Location Quick Find
- Quick Patterns (new layer, agent, command, hook)
- Data Structures
- Performance Targets
- Database Tables

---

### 3. ARCHITECTURE_COMPLETE_OVERVIEW.md (DEEP DIVE)
**File Size**: 56 KB | **Length**: 2027 lines | **Audience**: Architects, advanced developers

**Contents**:
- Executive Summary
- All 8 layers in detail
  - Component breakdown
  - Key classes
  - Operations
  - Design decisions
  - Data flow
- MCP Server architecture (11K lines analysis)
- Agents tier with execution models
- Hooks system with safety mechanisms
- Skills system (15 total)
- Commands system (20+ total)
- Integration layer (25+ coordinators)
- Advanced systems (Safety, Rules, Research, Execution)
- Core infrastructure
- Data flow diagrams
- Database schema details
- Test organization
- Design principles & ADRs

**Best for**: Comprehensive understanding, writing new components

**Key Sections**:
- Part 1: Executive Summary
- Part 2: 8-Layer Memory Architecture
- Part 3: MCP Server Architecture
- Part 4: Agents Tier
- Part 5: Hooks System
- Part 6: Skills System
- Part 7: Commands System
- Part 8: Integration Layer
- Part 9: Advanced Systems
- Part 10: Core Infrastructure
- Part 11: Data Flow and Integration
- Part 12: Key File Locations
- Part 13: Database Schema
- Part 14: Test Organization
- Part 15: Design Principles

---

## Quick Navigation by Use Case

### "I'm new to the project"
1. Start with **EXPLORATION_SUMMARY.md** - Overview section
2. Read **ARCHITECTURE_QUICK_REFERENCE.md** - Component lookup
3. Explore actual code: `src/athena/manager.py` → `src/athena/episodic/store.py`

### "I need to add a new memory layer"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - Quick Patterns → Creating a New Memory Layer
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 2 → Layer 1 structure as template
3. Reference: `src/athena/episodic/` - Study the structure

### "I need to create a new agent"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - Quick Patterns → Creating a New Agent
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 4 → Agent Types
3. Reference: `src/athena/agents/base.py` - BaseAgent class

### "I'm troubleshooting a query"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - Key Files by Purpose → Understanding Query Flow
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 11 → Typical Query Flow diagram
3. Trace through: manager.py → operation_router.py → handlers_tools.py

### "I need to understand consolidation"
1. **EXPLORATION_SUMMARY.md** - Core Innovation section
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 2 → Layer 7 detailed explanation
3. **ARCHITECTURE_QUICK_REFERENCE.md** - Key Files by Purpose → Understanding Consolidation
4. Trace through: `src/athena/consolidation/system.py`

### "I need to debug a hook"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - Key Files by Purpose → Understanding Hooks
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 5 → Hooks System
3. Reference: `src/athena/hooks/dispatcher.py`

### "I'm looking for a specific file"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - File Location Quick Find
2. Or search the tables in **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 12

### "I want to understand the database"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - Database Tables section
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 13 → Database Schema
3. See actual schema: Check relevant store.py files

### "I need to understand MCP operations"
1. **ARCHITECTURE_QUICK_REFERENCE.md** - Operation Categories section
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** - Part 3 → MCP Server Architecture
3. Trace through: `src/athena/mcp/handlers.py` → `src/athena/mcp/operation_router.py`

---

## File Locations for Each System

### Memory Layers
```
Layer 1: src/athena/episodic/store.py       → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 2: src/athena/memory/store.py         → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 3: src/athena/procedural/store.py     → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 4: src/athena/prospective/store.py    → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 5: src/athena/graph/store.py          → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 6: src/athena/meta/store.py           → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 7: src/athena/consolidation/system.py → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
Layer 8: src/athena/rag/manager.py          → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 2
```

### MCP Server
```
src/athena/mcp/handlers.py              → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 3
src/athena/mcp/operation_router.py      → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 3
src/athena/mcp/handlers_*.py (30+ files) → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 3
```

### Agents
```
src/athena/agents/base.py               → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 4
src/athena/agents/orchestrator.py       → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 4
src/athena/agents/planner.py            → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 4
```

### Hooks
```
src/athena/hooks/dispatcher.py          → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 5
src/athena/hooks/lib/                   → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 5
```

### Skills
```
src/athena/skills/                      → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 6
claude/skills/                          → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 6
```

### Commands
```
claude/commands/                        → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 7
src/athena/mcp/handlers_slash_commands.py → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 7
```

### Integration
```
src/athena/integration/                 → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 8
```

### Database
```
src/athena/core/database.py             → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 10
src/athena/core/config.py               → Read ARCHITECTURE_COMPLETE_OVERVIEW Part 10
```

---

## Statistics Summary

| Metric | Value |
|--------|-------|
| Total Python Files | 500+ |
| Total Lines of Code | 250,000+ |
| Memory Layers | 8 |
| MCP Handlers | 40+ |
| MCP Operations | 228+ |
| Agent Types | 8 |
| Integration Coordinators | 25+ |
| Claude Skills | 15 |
| Slash Commands | 20+ |
| Database Tables | 80+ |
| Test Files | 50+ |
| Episodic Events in DB | 8,000+ |
| Extracted Procedures | 101+ |
| Code Coverage | 65% (90%+ core) |

---

## Key Architecture Principles

From **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 15:

1. **Layer Independence** - Each layer is swappable
2. **Graceful Degradation** - Works without optional components
3. **Local-First** - No cloud required
4. **Dual-Process** - System 1 (100ms) + System 2 (LLM)
5. **Observability** - Comprehensive logging
6. **Safety-First** - Verification gates
7. **Extensibility** - Clear patterns for additions
8. **Agentic Loop** - Continuous improvement

---

## Recommended Reading Order

### For New Developers
1. **EXPLORATION_SUMMARY.md** (30 min) - Get the big picture
2. **ARCHITECTURE_QUICK_REFERENCE.md** (20 min) - Quick facts and patterns
3. Read code: `src/athena/manager.py` (20 min)
4. Read code: `src/athena/episodic/store.py` (20 min)
5. Try running tests: `pytest tests/unit/test_episodic*.py -v` (20 min)
**Total time**: 2 hours

### For Deep Understanding
1. **EXPLORATION_SUMMARY.md** (30 min)
2. **ARCHITECTURE_QUICK_REFERENCE.md** (30 min)
3. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 1-5 (90 min)
4. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 6-10 (90 min)
5. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 11-15 (60 min)
6. Read core files: manager.py, handlers.py, consolidation/system.py (120 min)
**Total time**: 6+ hours

### For Architecture Review
1. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 1 & 15 (20 min)
2. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 2 (40 min)
3. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 11 (20 min)
4. **ARCHITECTURE_COMPLETE_OVERVIEW.md** Part 12-14 (30 min)
**Total time**: 2 hours

---

## Where to Find Things

| What | Where | Which Doc |
|------|-------|-----------|
| Entry point | `src/athena/manager.py` | QUICK_REFERENCE |
| MCP server | `src/athena/mcp/handlers.py` | COMPLETE_OVERVIEW Part 3 |
| 8 layers | `src/athena/[layer]/store.py` | COMPLETE_OVERVIEW Part 2 |
| Agents | `src/athena/agents/orchestrator.py` | COMPLETE_OVERVIEW Part 4 |
| Hooks | `src/athena/hooks/dispatcher.py` | COMPLETE_OVERVIEW Part 5 |
| Slash commands | `claude/commands/` | COMPLETE_OVERVIEW Part 7 |
| Database | `src/athena/core/database.py` | COMPLETE_OVERVIEW Part 10 |
| Tests | `tests/unit/`, `tests/integration/` | QUICK_REFERENCE Testing Patterns |
| Configuration | `src/athena/core/config.py` | QUICK_REFERENCE Configuration |

---

## Questions & Answers

**Q: What's the entry point for memory queries?**
A: `src/athena/manager.py` - UnifiedMemoryManager.retrieve()
See: EXPLORATION_SUMMARY.md section "Query Execution Flow"

**Q: How do the 8 layers work together?**
A: See EXPLORATION_SUMMARY.md section "The 8-Layer Architecture" or ARCHITECTURE_COMPLETE_OVERVIEW.md Part 2

**Q: How do I add a new memory layer?**
A: ARCHITECTURE_QUICK_REFERENCE.md - Quick Patterns section

**Q: What's unique about Athena's consolidation?**
A: Dual-process: System 1 (100ms) + System 2 (LLM). See EXPLORATION_SUMMARY.md "Core Innovation"

**Q: How do agents work?**
A: See ARCHITECTURE_COMPLETE_OVERVIEW.md Part 4 and EXPLORATION_SUMMARY.md "Agent Execution Flow"

**Q: What's the test coverage?**
A: 65% overall, 90%+ for core layers. See EXPLORATION_SUMMARY.md "Testing Infrastructure"

---

## Revision History

| Date | Author | Summary |
|------|--------|---------|
| Nov 10, 2025 | Architecture Analysis | Created comprehensive documentation package |

---

## Related Files in Project

- `/CLAUDE.md` - Project guidelines and development patterns
- `/README.md` - Project overview and quick start
- `/pyproject.toml` - Python project configuration
- `/src/athena/` - Main source code
- `/tests/` - Test suite
- `/claude/commands/` - Slash command definitions
- `/claude/skills/` - Claude skill definitions

---

## Support & Questions

For detailed explanations:
1. Check the appropriate documentation file above
2. Search for the specific section using keywords
3. Refer to the code references provided
4. Review the design principles in Part 15 of ARCHITECTURE_COMPLETE_OVERVIEW.md

For implementation help:
1. See ARCHITECTURE_QUICK_REFERENCE.md - Quick Patterns
2. Find similar code in existing layers
3. Reference the base classes (BaseStore, BaseAgent)

For performance questions:
1. See ARCHITECTURE_QUICK_REFERENCE.md - Performance Targets
2. See EXPLORATION_SUMMARY.md - Performance Metrics section

---

**Last Updated**: November 10, 2025
**Documentation Version**: 1.0
**Project Status**: Production-ready prototype


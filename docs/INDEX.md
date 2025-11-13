# Athena Documentation Index

Complete guide to all Athena documentation and where to find what you need.

## Quick Navigation

### For First-Time Users
1. **Start here**: [tutorials/getting-started.md](./tutorials/getting-started.md) (15 minutes)
2. **Understand the system**: [tutorials/memory-basics.md](./tutorials/memory-basics.md)
3. **Install locally**: [INSTALLATION.md](./INSTALLATION.md)

### For Developers
1. **Set up environment**: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
2. **Run tests**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
3. **Contribute code**: [CONTRIBUTING.md](./CONTRIBUTING.md)

### For Advanced Users
1. **Explore advanced patterns**: [tutorials/advanced-features.md](./tutorials/advanced-features.md)
2. **Deep technical dive**: [ARCHITECTURE.md](./ARCHITECTURE.md)
3. **Anthropic alignment**: [ANTHROPIC_ALIGNMENT.md](./ANTHROPIC_ALIGNMENT.md)

---

## Documentation Structure

### Core Documentation (docs/)

| File | Purpose | Audience | Length |
|------|---------|----------|--------|
| **Getting Started** | | | |
| [README.md](../README.md) | Project overview | Everyone | 5 min |
| [INSTALLATION.md](./INSTALLATION.md) | Installation steps | New users | 10 min |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute | Contributors | 10 min |
| **Architecture & Design** | | | |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Technical architecture | Engineers | 20 min |
| [ANTHROPIC_ALIGNMENT.md](./ANTHROPIC_ALIGNMENT.md) | Anthropic pattern implementation | Advanced | 15 min |
| [CLAUDE.md](./CLAUDE.md) | Claude Code integration | All developers | 30 min |
| **Development & Operations** | | | |
| [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) | Development setup | Developers | 15 min |
| [TESTING_GUIDE.md](./TESTING_GUIDE.md) | Testing strategy | Developers | 20 min |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment & config | Operators | 15 min |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | Production deployment | DevOps | 25 min |
| **Reference & Help** | | | |
| [API_REFERENCE.md](./API_REFERENCE.md) | MCP tools & operations | Developers | 30 min |
| [USAGE_GUIDE.md](./USAGE_GUIDE.md) | How to use memory ops | Users | 20 min |
| [EXAMPLES.md](./EXAMPLES.md) | Code examples & patterns | Developers | 25 min |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Common issues & fixes | Everyone | 15 min |
| [CHANGELOG.md](./CHANGELOG.md) | Version history | Everyone | Ongoing |
| [INDEX.md](./INDEX.md) | Documentation index | Everyone | 10 min |

### Tutorials (docs/tutorials/)

| File | Purpose | Audience | Duration |
|------|---------|----------|----------|
| [getting-started.md](./tutorials/getting-started.md) | Quick start guide | Beginners | 15 min |
| [memory-basics.md](./tutorials/memory-basics.md) | Understanding 8 layers | Intermediate | 30 min |
| [advanced-features.md](./tutorials/advanced-features.md) | Expert patterns & optimization | Advanced | 45 min |

### Temporary Working Documents (docs/tmp/)

Contains session-specific and in-progress documents. These are:
- Session resumé documents (SESSION_*.md)
- Progress reports (FEATURE_PROGRESS.md)
- Analysis and investigations
- Work-in-progress planning

**When complete**: Move to `docs/archive/`

### Historical Archive (docs/archive/)

Contains 368+ historical documents including:
- PHASE_*.md - Completed phase reports
- COMPLETION_*.md - Historical completion reports
- Other archived reference material

---

## Finding What You Need

### "I want to..."

#### ...get started quickly
→ [tutorials/getting-started.md](./tutorials/getting-started.md)

#### ...understand memory layers
→ [tutorials/memory-basics.md](./tutorials/memory-basics.md)

#### ...install on my machine
→ [INSTALLATION.md](./INSTALLATION.md)

#### ...set up development environment
→ [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)

#### ...run tests
→ [TESTING_GUIDE.md](./TESTING_GUIDE.md)

#### ...contribute code
→ [CONTRIBUTING.md](./CONTRIBUTING.md)

#### ...understand the architecture
→ [ARCHITECTURE.md](./ARCHITECTURE.md)

#### ...learn advanced patterns
→ [tutorials/advanced-features.md](./tutorials/advanced-features.md)

#### ...see what changed
→ [CHANGELOG.md](./CHANGELOG.md)

#### ...understand Anthropic alignment
→ [ANTHROPIC_ALIGNMENT.md](./ANTHROPIC_ALIGNMENT.md)

#### ...integrate with Claude Code
→ [CLAUDE.md](./CLAUDE.md)

#### ...see complete API reference
→ [API_REFERENCE.md](./API_REFERENCE.md)

#### ...see how to use memory operations
→ [USAGE_GUIDE.md](./USAGE_GUIDE.md)

#### ...find code examples
→ [EXAMPLES.md](./EXAMPLES.md)

#### ...troubleshoot issues
→ [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

#### ...configure Athena
→ [CONFIGURATION.md](./CONFIGURATION.md)

#### ...deploy to production
→ [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

---

## Documentation Standards

### File Organization

**Standard Documentation** (`docs/`)
- Maintained regularly
- Part of project deliverables
- Include in releases
- Audience: Users, developers, contributors

**Temporary Documents** (`docs/tmp/`)
- Session working documents
- Progress reports
- Temporary analysis
- Cleaned up quarterly

**Historical Documents** (`docs/archive/`)
- Completed phases and reports
- Reference material
- Not actively maintained
- Audience: Historical context

### Content Guidelines

#### When to Create in `docs/`

Create new standard documentation for:
- Architecture decisions (ARCHITECTURE.md)
- Development workflows (DEVELOPMENT_GUIDE.md)
- Setup and installation (INSTALLATION.md)
- Testing strategies (TESTING_GUIDE.md)
- Contribution guidelines (CONTRIBUTING.md)
- Version history (CHANGELOG.md)

#### When to Create in `docs/tmp/`

Create temporary documents for:
- Session summaries (SESSION_N_COMPLETE.md)
- Progress reports (FEATURE_PROGRESS.md)
- Investigation findings
- Analysis and planning
- Work-in-progress items

#### Move to `docs/archive/` when:
- Session is complete
- Work is superseded by standard docs
- Investigation is finished
- Analysis is historical reference

### Updates and Maintenance

| Document | Update Frequency | Triggers |
|----------|------------------|----------|
| CLAUDE.md | Quarterly | Pattern changes, major features |
| ARCHITECTURE.md | As-needed | Major refactors, new layers |
| CHANGELOG.md | With each commit | Any code changes |
| DEVELOPMENT_GUIDE.md | Quarterly | Workflow changes |
| TESTING_GUIDE.md | As-needed | Test structure changes |
| CONTRIBUTING.md | Quarterly | Contribution process changes |
| Tutorials | As-needed | API changes, new features |
| docs/tmp/ | Every session | Session-specific documents |
| docs/archive/ | Quarterly | Move completed work |

---

## Key Features by Documentation

### Episodic Memory (Layer 1)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-1-episodic-memory)
- API: [API_REFERENCE.md](./API_REFERENCE.md) (store_event, get_event, search_events_by_tag)
- Usage: [USAGE_GUIDE.md](./USAGE_GUIDE.md#layer-1-episodic-events)
- Example: [tutorials/getting-started.md](./tutorials/getting-started.md#1-store-an-event-episodic-memory)

### Semantic Memory (Layer 2)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-2-semantic-memory)
- API: [API_REFERENCE.md](./API_REFERENCE.md) (store_memory, search_semantic, update_importance)
- Usage: [USAGE_GUIDE.md](./USAGE_GUIDE.md#layer-2-semantic-knowledge)
- Advanced: [tutorials/advanced-features.md](./tutorials/advanced-features.md#advanced-rag-strategies)

### Procedural Memory (Layer 3)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-3-procedural-memory)
- Usage: [tutorials/getting-started.md](./tutorials/getting-started.md#6-extract-procedures-learn-workflows)

### Prospective Memory (Layer 4)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-4-prospective-memory)
- Usage: [tutorials/getting-started.md](./tutorials/getting-started.md#7-set-goals-prospective-memory)

### Knowledge Graph (Layer 5)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-5-knowledge-graph)
- Advanced: [tutorials/advanced-features.md](./tutorials/advanced-features.md#knowledge-graph-operations)

### Meta-Memory (Layer 6)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-6-meta-memory)

### Consolidation (Layer 7)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-7-consolidation)
- Advanced: [tutorials/advanced-features.md](./tutorials/advanced-features.md#consolidation-strategies)

### Supporting Systems (Layer 8)
- See: [tutorials/memory-basics.md](./tutorials/memory-basics.md#layer-8-supporting-infrastructure)
- Advanced: [tutorials/advanced-features.md](./tutorials/advanced-features.md)

---

## Development Workflow

### Starting a New Feature

1. **Check architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Set up environment**: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
3. **Understand testing**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
4. **Follow guidelines**: [CONTRIBUTING.md](./CONTRIBUTING.md)
5. **Create session doc**: `docs/tmp/FEATURE_PROGRESS.md`

### During Development

1. **Update progress**: `docs/tmp/FEATURE_PROGRESS.md`
2. **Commit frequently**: Follow [CONTRIBUTING.md](./CONTRIBUTING.md)
3. **Run tests**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
4. **Check style**: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md#code-quality)

### Completing a Feature

1. **Update CHANGELOG.md** with summary
2. **Update relevant standard docs** (ARCHITECTURE.md, etc.)
3. **Move session doc** to docs/archive/
4. **Create pull request** per [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## Common Documentation Tasks

### I'm a maintainer, how do I...

#### ...update standard docs?
Edit files in `docs/` directory. Follow update frequency in Standards section above.

#### ...archive old session docs?
Move from `docs/tmp/` to `docs/archive/` when session is complete.

#### ...clean up documentation?
Review `docs/archive/` quarterly and consolidate outdated files.

#### ...create new documentation?
1. Determine if it's standard, temporary, or historical
2. Follow format of existing docs in that category
3. Add to appropriate directory
4. Link from INDEX.md if standard doc

### I'm a contributor, how do I...

#### ...understand the project?
1. Read [tutorials/getting-started.md](./tutorials/getting-started.md)
2. Study [ARCHITECTURE.md](./ARCHITECTURE.md)
3. Follow [CONTRIBUTING.md](./CONTRIBUTING.md)

#### ...find development help?
→ [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)

#### ...understand the testing approach?
→ [TESTING_GUIDE.md](./TESTING_GUIDE.md)

#### ...ask a question?
See [CONTRIBUTING.md](./CONTRIBUTING.md) for support channels.

---

## Version Information

| Metric | Value |
|--------|-------|
| Documentation Version | 1.0 |
| Last Updated | November 13, 2025 |
| Total Standard Docs | 15 |
| Total Tutorials | 3 |
| Total Temporary Docs | 11 |
| Total Archived Docs | 368+ |
| Total Documentation Files | 397+ |
| Project Status | Production-ready (95%) |

---

## Navigation Shortcuts

- 📖 **Tutorials**: [tutorials/](./tutorials/)
- 🏗️ **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 💻 **Development**: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
- 🧪 **Testing**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- 🤝 **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md)
- 📦 **Installation**: [INSTALLATION.md](./INSTALLATION.md)
- ✍️ **Claude Integration**: [CLAUDE.md](./CLAUDE.md)
- 🔄 **Versions**: [CHANGELOG.md](./CHANGELOG.md)
- 📚 **Archive**: [archive/](./archive/)
- 🔨 **Session Work**: [tmp/](./tmp/)

---

**Last Updated**: November 13, 2025
**Maintained By**: Athena Documentation Team
**Quality Status**: ✅ Complete

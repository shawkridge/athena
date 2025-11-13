# Changelog

All notable changes to Athena are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentation structure reorganization (Session 6)
- `docs/tmp/` for temporary working documents
- Standard documentation files (CONTRIBUTING, CHANGELOG, etc.)

### Changed
- Moved session/resume docs to `docs/tmp/`
- Updated CLAUDE.md with documentation guidance

## [0.9.0] - 2025-11-13

### Added
- Initial 8-layer memory system (Layers 1-8)
- MCP interface with 27 tools and 228+ operations
- PostgreSQL backend with async connection pooling
- Dual-process consolidation (System 1 + System 2)
- Knowledge graph with Leiden community detection
- Working memory (7±2 cognitive limit)
- Advanced RAG strategies (HyDE, reranking, reflective)
- Comprehensive test suite (94/94 tests passing)
- 8,128 migrated episodic events
- 101 learned procedures from pattern extraction

### Changed
- Handler refactoring: 12,363 → 1,270 lines in main handlers.py
- Extracted 11 domain-organized handler modules
- Improved code organization and maintainability

### Fixed
- Version consistency across pyproject.toml and __init__.py
- Database configuration clarity (PostgreSQL only)
- Handler method organization and discoverability

## [0.8.0] - Previous Version

For historical information, see `/docs/archive/`.

---

## Guidelines for Updating CHANGELOG

### When to Update
- Add entry after each commit that adds features or fixes bugs
- Update in each PR with summary of changes
- Include section at release time with final version

### Entry Format
```markdown
### Added
- New feature description

### Changed
- Modified feature description

### Fixed
- Bug fix description

### Deprecated
- Soon-to-be removed feature

### Removed
- Removed feature
```

### Semantic Versioning
- **MAJOR**: Breaking changes (e.g., API changes, database schema changes)
- **MINOR**: New features backward compatible
- **PATCH**: Bug fixes

---

**Unreleased changes should remain at the top of the file.**

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to submit changes.

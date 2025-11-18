# Specifications

This directory contains specifications that define system behavior.

## Supported Formats

- **OpenAPI** (.yaml, .json) - REST API specifications
- **GraphQL** (.graphql) - GraphQL schemas
- **TLA+** (.tla) - Formal specifications
- **Alloy** (.als) - Structural models
- **Prisma** (.prisma) - Database schemas
- **AsyncAPI** (.yaml) - Event-driven API specs
- **Markdown** (.md) - General specifications

## Version Control

All specs are tracked in git. Use semantic versioning (MAJOR.MINOR.PATCH).

## Workflow

1. Write spec (intent as source of truth)
2. Validate spec (automated validation)
3. Generate code from spec (AI-assisted)
4. Verify generated code matches spec
5. Track accuracy metrics

For more info, see: docs/SPEC_DRIVEN_DEVELOPMENT.md

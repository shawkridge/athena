---
description: Advanced - Discover natural communities in knowledge graph using GraphRAG
argument-hint: "Optional: community level (0=granular, 1=intermediate, 2=global)"
---

# Find Communities

Advanced GraphRAG analysis: discover natural concept communities, identify bridge entities, and analyze connections.

Usage:
- `/find-communities` - Multi-level community analysis
- `/find-communities 0` - Granular level (individual concepts)
- `/find-communities 1` - Intermediate level (concept groups)
- `/find-communities 2` - Global level (major domains)

Features:
- **Community Detection**: Leiden clustering algorithm (scalable, high modularity)
- **Multi-Level Analysis**: Granular → Intermediate → Global
- **Bridge Entities**: Concepts connecting different communities
- **Density Metrics**: How tightly communities are connected
- **Evolution Tracking**: How communities change over time

Returns:
- Detected communities with member entities
- Community characteristics (size, density, centrality)
- Bridge entities connecting communities
- Relationship strength analysis
- Temporal evolution (if applicable)
- Visualization data (community graphs)

Example output:
```
Community Detection Results:
─────────────────────────────

Level 0 - Granular:
  Community "Auth": {AuthManager, JWT, OAuth2, SessionHandler, TokenValidator}
    Density: 0.92 (tightly connected)
    Size: 5 entities

  Community "API": {Endpoints, Middleware, RequestHandler, ResponseFormatter}
    Density: 0.87
    Size: 4 entities

Level 1 - Intermediate:
  Community "Security": {Auth, TokenValidation, Encryption, Audit}
    Density: 0.71
    Size: 12 entities
    Connections: 3 to other communities

Level 2 - Global:
  Domain "Core Infrastructure"
  Domain "Application Logic"
  Domain "Security & Compliance"

Bridge Entities (connecting communities):
  - AuthManager (connects Auth ↔ API) (bridge strength: 0.84)
  - Database (connects all communities) (bridge strength: 0.95)
```

Advanced feature: for understanding knowledge organization and finding improvement opportunities. Requires GraphRAG analysis.

---
description: Deep codebase analysis with spatial hierarchy and dependency detection
argument-hint: "$1 = focus area (optional: class name, module, function)"
---

# Analyze Code

Perform deep codebase analysis with spatial hierarchy, dependency detection, and impact assessment.

Usage:
- `/analyze-code` - Full codebase overview
- `/analyze-code "AuthenticationManager"` - Analyze specific class
- `/analyze-code "src/auth/"` - Analyze directory

Features:
- **Spatial Hierarchy**: File/module/class/function structure
- **Dependency Graph**: Import chains and circular dependencies
- **Change Impact**: Which components affected by code change
- **Code Metrics**: Complexity, coverage, dead code
- **Relationships**: Method calls, inheritance, composition

Returns:
- Code structure overview
- Dependency graph visualization
- Top N complex functions (cyclomatic complexity)
- Unused code and dead branches
- Import chains and circular dependencies
- Change impact analysis
- Code organization insights

Example output:
```
Codebase Structure:
└── src/
    ├── auth/
    │   ├── AuthenticationManager (350 LOC, complexity 8)
    │   ├── TokenValidator (120 LOC, complexity 3)
    │   └── SessionHandler (200 LOC, complexity 5)
    └── api/
        ├── endpoints.py (400 LOC)
        └── middleware.py (150 LOC)

Dependencies:
  AuthenticationManager → TokenValidator ✓
  AuthenticationManager → Database ✓
  SessionHandler → AuthenticationManager ✓
  (No circular dependencies detected)

Impact Analysis (if updating AuthenticationManager):
  Affected: SessionHandler, 5 API endpoints, 2 test modules
  Risk: Medium (used by 7 components)
```

The code-analyzer agent autonomously invokes this for change impact analysis.

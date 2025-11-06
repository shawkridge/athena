---
name: codebase-understanding
description: |
  Analyze codebase structure with spatial hierarchies and dependency graphs.
  Use when understanding code organization, finding change impacts, or planning refactoring.
  Provides file structure, import chains, relationships, complexity metrics.
---

# Codebase Understanding Skill

Analyze code structure and dependencies to understand organization and impacts.

## When to Use

- Understanding code organization
- Finding what will be impacted by changes
- Planning refactoring or restructuring
- Analyzing code complexity and relationships
- Identifying dead code or unused modules

## Analysis

- **Spatial Hierarchy**: File/module/class/function structure
- **Dependency Graph**: Import chains and relationships
- **Complexity Metrics**: Cyclomatic complexity, LOC
- **Change Impact**: Components affected by changes
- **Dead Code**: Unused functions and classes
- **Circular Dependencies**: Import loops

## Returns

- Code structure overview
- Dependency visualization
- Top complex functions
- Unused code areas
- Import chains
- Change impact analysis
- Organization insights

## Examples

- Analyze a specific class: "AuthenticationManager"
- Analyze a directory: "src/auth/"
- Full codebase overview: overall structure

The codebase-understanding skill activates when analyzing code structure and impacts.

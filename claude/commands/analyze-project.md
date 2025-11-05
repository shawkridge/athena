# /analyze-project

**Analyze project structure and build memory about your codebase**

Comprehensive project analyzer that scans your project and stores findings in memory for improved context, planning, and decision-making.

## Usage

```bash
/analyze-project [project_path]
```

### Parameters

- `project_path` (optional): Path to project root. If not provided, uses current working directory.

## What It Does

The analyzer:

1. **Scans File Structure** - Identifies all code files, counts lines, estimates complexity
2. **Identifies Components** - Groups files into logical components/modules
3. **Extracts Patterns** - Finds coding patterns (async/await, type hints, error handling, etc.)
4. **Analyzes Dependencies** - Maps internal and external dependencies
5. **Calculates Metrics** - Complexity, test coverage, documentation scores
6. **Generates Insights** - Identifies strengths and weaknesses
7. **Stores in Memory** - Saves findings to semantic memory + knowledge graph

## Output

```json
{
  "project_name": "memory-mcp",
  "total_files": 45,
  "total_lines": 12500,
  "languages": {
    "python": 45
  },
  "components": [
    {
      "name": "core",
      "files": 8,
      "complexity": 0.62,
      "test_coverage": 0.25
    }
  ],
  "metrics": {
    "avg_complexity": 0.58,
    "test_file_ratio": 0.22,
    "documentation_score": 0.85
  },
  "insights": [
    "Primary language: Python (45 files)",
    "Project organized into 5 components",
    "Good test coverage ratio: 22.2%",
    "Medium-sized project (12k+ lines)"
  ],
  "recommendations": [
    "Consider breaking project into more distinct components",
    "Expand test file coverage (current: 22%, target: >30%)"
  ]
}
```

## Examples

### Analyze current project
```bash
/analyze-project
# Analyzes working directory
# Stores findings in memory system
```

### Analyze specific project
```bash
/analyze-project /home/user/projects/myapp
# Analyzes /home/user/projects/myapp
# Stores findings under "myapp" project context
```

### After Analysis

Once analyzed, you can:

**Query insights about project:**
```bash
/memory-query "myapp components"
# Returns identified components and their roles
```

**Get recommendations:**
```bash
/memory-query "myapp recommendations"
# Returns improvement recommendations
```

**Understand patterns:**
```bash
/memory-query "what patterns does myapp use"
# Returns coding patterns found in project
```

**Plan changes based on structure:**
```bash
/plan build "refactor myapp"
# Plan now includes project knowledge
# Better risk detection and optimization
```

## Detected Components

The analyzer identifies components by directory structure:

```
project/
├── core/           → Component: core
├── api/            → Component: api
├── utils/          → Component: utils
├── tests/          → Test files (tracked separately)
└── config/         → Configuration files
```

## Detected Patterns

Automatically finds:
- **async/await** - Async function patterns
- **type_hints** - Type annotation usage
- **decorators** - Decorator patterns
- **context_managers** - with statement usage
- **error_handling** - Try/except patterns
- **docstrings** - Documentation patterns

## Quality Metrics

### Complexity (0.0-1.0)
- < 0.3: Simple, well-structured
- 0.3-0.6: Moderate complexity
- 0.6-0.8: High complexity (refactor opportunities)
- > 0.8: Very high complexity (significant issues)

### Test Coverage
- Ratio of test files to total files
- Target: > 20% test files
- Indicates code quality and maintainability

### Documentation Score
- Estimated from docstrings and comments
- Target: > 75%
- Affects onboarding and maintenance

## Memory Storage

Findings are stored as:

1. **Semantic Memory**
   - Project overview with statistics
   - Insights and recommendations
   - Metrics and quality assessment

2. **Knowledge Graph Entities**
   - Each component as entity
   - Patterns as entities
   - With properties and relationships

3. **Knowledge Graph Relations**
   - Component dependencies
   - Pattern occurrences
   - Quality indicators

## Tips

### Get maximum benefit:

1. **Analyze early** - Run at project start or when joining
2. **Re-analyze periodically** - Every 2-4 weeks to track changes
3. **Use insights** - Reference findings when planning features
4. **Act on recommendations** - Address top recommendations first
5. **Share findings** - Use stored memories to onboard team members

### Combine with other tools:

```bash
# 1. Analyze project
/analyze-project

# 2. Plan new feature using project knowledge
/plan build "add authentication"

# 3. Execute with confidence (plan considers project structure)

# 4. After completion, insights help with testing, docs, etc.
```

## Integration with Memory System

The analyzer stores findings so they're available to:

- **Plan generation** - Uses component knowledge for better planning
- **Estimation** - Considers project complexity in time estimates
- **Risk detection** - Identifies patterns that could affect changes
- **Documentation** - Knows what patterns to document
- **Refactoring** - Suggests improvements based on analysis

## Troubleshooting

### "Project not found"
Check the path is correct and readable:
```bash
/analyze-project ~/my-project
# Make sure ~/my-project exists
```

### "Analysis took too long"
Large projects may take 1-2 minutes. For faster analysis, exclude directories:
- Automatically skips: node_modules, vendor, .venv, dist, build
- If still slow: run on project subdirectory

### "Found few components"
Small projects may have just 1-2 components. This is normal and is noted in insights.

## See Also

- `/memory-query` - Search project findings
- `/plan build` - Plan changes using project knowledge
- `/memory-health` - See memory system status
- `/consolidate` - Extract patterns from memories

---

**Powered by Memory MCP Project Analysis System**

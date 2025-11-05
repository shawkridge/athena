---
description: Create, find, and track reusable workflows and procedures
group: Workflows & Procedures
aliases: ["/procedure", "/workflow-library", "/templates"]
---

# /workflow

Discover, create, and execute reusable workflows. Track success rates and learnings.

## Usage

```bash
/workflow search "auth"         # Find workflows
/workflow create               # Create new workflow
/workflow execute NAME         # Run workflow
/workflow stats                # Success rate analysis
```

## Categories

- `git` - Version control workflows
- `code_template` - Code generation templates
- `refactoring` - Refactoring procedures
- `debugging` - Debugging strategies
- `deployment` - Deployment pipelines
- `testing` - Testing procedures

## Example Output

```
WORKFLOW LIBRARY
═══════════════════════════════════════════

Workflows Found: 23
Total Executions: 187
Overall Success Rate: 91%

Most Used Workflows:
  1. jwt-token-implementation (executions: 12, success: 100%)
  2. database-migration (executions: 8, success: 88%)
  3. error-handling-pattern (executions: 7, success: 86%)

Recommended Workflows:
  • express-middleware-setup (success: 100%, templates: 4)
  • react-component-pattern (success: 93%, templates: 8)
  • git-rebase-flow (success: 89%, templates: 3)

Recent Workflows:
  • JWT token implementation (executed 2h ago, success)
  • Database cleanup script (executed 5h ago, success)
  • Component refactoring (executed 1d ago, partial)
```

## Commands

```bash
# Find workflows
/workflow search "deployment"
/workflow search --category git
/workflow list --sorted success  # By success rate

# Create workflow
/workflow create
→ Guided step-by-step creation
→ Name, description, steps, trigger pattern
→ Auto-save and version

# Execute workflow
/workflow execute jwt-token-implementation
→ Shows steps
→ Prompts for parameters
→ Records execution + outcome

# Analyze
/workflow stats
/workflow stats --category testing
/workflow stats --workflow jwt-implementation
```

## Integration

Works with:
- `/consolidate` - Extract new workflows from patterns
- `/memory-query` - Find related workflows
- `/task-create` - Link tasks to workflows
- `/project-status` - Show workflow effectiveness

## Related Tools

- `create_procedure` - Create workflow
- `find_procedures` - Search workflows
- `record_execution` - Track execution
- `consolidation_system` - Extract from patterns

## Tips

1. **Review high-success workflows** - Learn from what works
2. **Document as you discover** - Capture patterns early
3. **Link to tasks** - Reuse for similar work
4. **Track execution** - Build success history
5. **Extract from consolidation** - Use `/consolidate` to find patterns

## See Also

- `/consolidate` - Extract patterns into workflows
- `/memory-query` - Find related procedures
- `/project-status` - Link to project tasks

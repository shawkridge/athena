# /plan - Planning Assistant

Use Phase 7 planning features for AI-assisted task execution planning.

## Usage

### ⚡ Quick Planning (All-in-One) - RECOMMENDED
```
/plan build "<description>"    Generate + optimize + estimate in one command
/plan build "coding mcp"       See example below
```

### Detailed Step-by-Step
```
/plan generate <task_id>       Create structured execution plan
/plan optimize <task_id>       Get optimization suggestions
/plan resources <task_id>      Estimate required resources
```

## Examples

### Quick (Recommended)
```
/plan build "Implement user authentication"
/plan build "Fix database migration bug"
/plan build "Refactor API endpoint handlers"
/plan build "coding mcp"
```

### Detailed
```
/plan generate 5
/plan optimize 5
/plan resources 5
```

## What It Does

### Build (All-in-One)
Executes the complete planning workflow in sequence:
1. **Generate**: Parse description → create structured plan
2. **Optimize**: Analyze for parallelization, risks, improvements
3. **Resources**: Estimate time, expertise, dependencies
4. Returns: Complete, ready-to-execute plan with all details

**Time**: 5-10 minutes
**Recommended for**: Most planning tasks

### Generate
- Parses task description into structured steps
- Estimates duration for each step
- Identifies required expertise level
- Detects external dependencies
- Returns: sequential list of steps with durations

### Optimize
- Identifies steps that can run in parallel
- Flags potential risks and blockers
- Suggests missing steps or considerations
- Recommends alternative approaches
- Returns: optimization suggestions with impact analysis

### Resources
- Estimates total time required (in hours)
- Identifies expertise level needed
- Lists required tools/dependencies
- Calculates resource availability conflicts
- Returns: comprehensive resource requirements

## When to Use
- Creating complex tasks (>4 steps)
- Uncertain about approach
- Before entering execution phase
- Weekly sprint planning
- Blocked task resolution

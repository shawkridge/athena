---
name: automation-management
description: |
  When you need to design event-driven automation rules with smart triggers.
  When coordinating complex workflows across time, events, or file changes.
  When reliability and efficiency in automation execution are critical.
---

# Automation Management Skill

Automation specialist for designing and managing event-driven automation workflows at scale.

## When to Use

- Need to create event-driven automation rules
- Setting up scheduled or trigger-based workflows
- Coordinating complex multi-step automation
- Ensuring reliable automation execution
- Managing automation lifecycle
- Optimizing automation efficiency

## Trigger Types

### Time-Based Triggers
- Scheduled (daily, weekly, monthly)
- Interval-based (every N minutes/hours)
- Cron expressions
- Temporal patterns

### Event-Based Triggers
- Task completion
- Goal achievement
- Error occurrence
- State changes
- Custom events

### File-Based Triggers
- File creation
- File modification
- Directory changes
- Git commits
- Build artifacts

## Automation Patterns

1. **Consolidation Automation** - Automatic memory consolidation
2. **Monitoring Automation** - Continuous health checks
3. **Reporting Automation** - Periodic reports
4. **Cleanup Automation** - Data management
5. **Escalation Automation** - Alert handling
6. **Integration Automation** - Cross-system workflows
7. **Learning Automation** - Continuous learning workflows

## Available Tools

- **register_automation_rule**: Create automation rule
- **trigger_automation_event**: Manual trigger
- **list_automation_rules**: View all rules
- **update_automation_config**: Modify configuration
- **execute_automation_workflow**: Run workflow

## Design Principles

### Smart Triggering
- Avoid over-triggering
- Consider dependencies
- Implement rate limiting
- Use smart batching

### Reliability
- Implement retries
- Handle failures gracefully
- Log execution
- Monitor success rates

### Efficiency
- Minimize resource usage
- Batch operations
- Parallel execution where possible
- Clean up old data

### Safety
- Dry-run capability
- Approval gates for critical operations
- Automatic rollback on failure
- Comprehensive logging

## Common Automations

1. **Daily Consolidation** - Run consolidation every night
2. **Weekly Health Check** - Check system health every Monday
3. **Continuous Monitoring** - Monitor key metrics
4. **Auto-Cleanup** - Remove old events periodically
5. **Learning Trigger** - Extract patterns on demand
6. **Backup Automation** - Backup critical data

## Example Use Cases

### Scheduled Consolidation
"Run memory consolidation every night at 2am"
→ Creates time-based trigger, configures consolidation workflow, sets up monitoring

### Event-Driven Learning
"Extract patterns when 100 new events accumulated"
→ Creates event-based trigger, monitors event count, executes pattern extraction

### File-Watch Automation
"Trigger analysis on code changes"
→ Sets up file modification trigger, executes analysis workflow, logs results

## Best Practices

- **Start Simple** - Begin with basic automations
- **Monitor Closely** - Watch for issues
- **Test First** - Use dry-run before production
- **Document Rules** - Document automation purpose
- **Review Regularly** - Audit automation rules
- **Optimize Triggers** - Reduce unnecessary executions

Use automation management to handle repetitive tasks reliably and efficiently.

---
name: athena-prospective
description: >
  Goal and task management: list tasks, create goals, manage dependencies, track progress.
  Organize your objectives and track execution.

  Use when: "tasks", "goals", "todo", "objectives", "what's next", "track progress"
---

# Athena Prospective Memory Skill

Manage goals and tasks. Create objectives, track dependencies, monitor progress toward goals.

## What This Skill Does

- **List Tasks**: See active goals and tasks
- **Create Goal**: Define new objective
- **Manage Dependencies**: Link related tasks
- **Track Status**: Monitor progress

## When to Use

- **"What are my tasks?"** - List active goals
- **"Create a goal for..."** - Define objective
- **"What's blocking me?"** - Check dependencies
- **"What's my next priority?"** - Get priority tasks

## Available Tools

### listTasks(status, limit)
List active tasks and goals.

### createGoal(description, priority, deadline)
Create new goal.

### manageDependencies(task1, task2)
Link dependent tasks.

### trackProgress(taskId)
Get task progress and status.

## Architecture

Integrates with Athena's Layer 4 (Prospective Memory):
- Active task tracking
- Goal management with dependencies
- Priority and deadline support

# Feature Workflow - Claude Code Protocol

## Overview

When you want to start a new feature, **just tell me**. I handle:
- ✅ Creating the worktree
- ✅ Setting up the feature context
- ✅ Creating initial todos
- ✅ Working on the implementation
- ✅ Managing context and memory
- ✅ Cleanup when done

---

## How to Request a New Feature

### **Simple Format**

```
Start a new feature: [feature name]
[Optional: description of what needs to be done]
```

### **Examples**

```
Start a new feature: user authentication
Implement JWT-based login/signup with:
- Design auth schema
- Create authentication endpoints
- Add token validation middleware
- Write comprehensive tests
```

```
Start a new feature: payment integration
```

```
Start a new feature: database migration
Migrate from MySQL to PostgreSQL including:
- Schema conversion
- Data migration script
- Rollback procedure
```

---

## What I Do Automatically

### **1. Create Worktree** ✅
```bash
git worktree add /home/user/.work/athena-feature-[name] -b feature/[name]
```
- Isolated working directory
- Clean file system state
- Separate from main branch

### **2. Set Up Context** ✅
- Detect your feature name
- Format it for display
- Initialize metadata
- Set up environment

### **3. Create Todos** ✅
- Parse your description
- Break down into actionable items
- Add them to TodoWrite
- They're isolated to this worktree

### **4. Work on Feature** ✅
- Implement based on requirements
- Run tests
- Use available tools
- Manage git commits

### **5. Manage Memory** ✅
- Memory automatically tagged with feature context
- Current feature memories prioritized (+2.0 boost)
- Knowledge from other features still accessible
- Working memory shows feature context

### **6. Monitor Health** ✅
- Track todo progress
- Monitor memory effectiveness
- Watch for issues
- Report status regularly

### **7. Clean Up** ✅
- When feature is complete:
  - Review work
  - Verify tests pass
  - Merge to appropriate branch
  - Remove worktree
  - Archive completed todos

---

## Example: Full Feature Workflow

### **You Say**
```
Start a new feature: user authentication

Implement JWT-based user authentication system:
- Design database schema (users, tokens, sessions)
- Create login endpoint that returns JWT token
- Create signup endpoint with validation
- Add token verification middleware
- Implement logout/token refresh
- Write unit tests for auth flow
- Update API documentation
```

### **I Do**
```
1. ✅ Create worktree: /home/user/.work/athena-user-auth
2. ✅ Create branch: feature/user-authentication
3. ✅ Generate todos from your description (7-10 items)
4. ✅ Initialize feature metadata
5. ✅ Start implementing:
   - Set up project structure
   - Create database models
   - Implement endpoints
   - Add middleware
   - Write tests
   - Update docs
6. ✅ Regular updates: "Added JWT token endpoint, tests passing"
7. ✅ When complete: "Feature ready - all tests passing, 45 lines added"
```

### **You Get**
- ✅ Fully implemented feature
- ✅ Tests included
- ✅ Documentation updated
- ✅ Clean git commits
- ✅ Feature branch ready for review/merge
- ✅ All memories tagged and organized

---

## Status Updates

### **During Feature Work**

I'll provide regular updates:

```
📝 Working on feature: User Authentication

Progress:
  ✓ Database schema (users table + migrations)
  ✓ Login endpoint with JWT generation
  ✓ Token validation middleware
  → Working on: Signup endpoint with email validation

Tests: 8/12 passing
  - Auth flow tests: ✓
  - Token validation tests: ✓
  - Signup validation: → in progress

Next steps:
  - Complete email validation
  - Add logout endpoint
  - Write remaining tests
  - Update API docs
```

### **At Milestones**

```
✅ Major milestone: Authentication endpoints complete

All CRUD operations working:
  ✓ POST /auth/login
  ✓ POST /auth/signup
  ✓ POST /auth/logout
  ✓ POST /auth/refresh
  ✓ Middleware: validateToken()

Tests: 12/12 passing ✅
Code: 340 lines added across 4 files

Ready for: Integration with user service
```

---

## Managing Multiple Features

### **Switching Between Features**

```
I'm done with user-auth for now.
Switch to payment-integration feature.
```

I'll:
1. ✅ Stash any uncommitted changes in current worktree
2. ✅ Save feature progress checkpoint
3. ✅ Switch to payment-integration worktree
4. ✅ Load that feature's todos and context
5. ✅ Resume work

### **Parallel Features**

If you want me working on multiple features simultaneously in different sessions:

```
Start a new feature: payment-integration
[continue work in this session on current feature]
```

Each gets its own:
- ✅ Isolated worktree
- ✅ Isolated todos
- ✅ Prioritized memory context
- ✅ Independent progress tracking

---

## Completing a Feature

### **When Feature Is Ready**

```
Feature complete: user-authentication

Status:
  ✓ All todos done
  ✓ All tests passing (98% coverage)
  ✓ Documentation updated
  ✓ Code reviewed
  ✓ 12 commits with clear messages
```

I'll:
1. ✅ Run final tests
2. ✅ Verify documentation
3. ✅ Create feature summary
4. ✅ Prepare for merge (or submit PR)
5. ✅ Clean up worktree
6. ✅ Archive completed todos
7. ✅ Document learnings for future features

### **Before Cleanup**

You can review:
```
git log --oneline  # See all commits
git diff main...feature/user-auth  # See all changes
git worktree list  # See all active worktrees
```

---

## Available Commands

### **List All Features**

```bash
git worktree list
```

Shows all active feature worktrees with branches.

### **Manual Worktree Operations**

```bash
# If you want to manually create a feature (optional)
/home/user/.work/athena/scripts/start-feature.sh "feature/my-feature"

# Switch between worktrees
cd /home/user/.work/athena-feature-name
claude code

# Clean up when done
git worktree remove /home/user/.work/athena-feature-name
```

---

## Conventions

### **Branch Naming**

```
feature/user-authentication      → "User Authentication"
feature/payment-processing       → "Payment Processing"
fix/memory-leak                  → "Memory Leak"
feature/api-v2-refactor          → "Api V2"
```

Automatically formatted for display in session-start.

### **Todo Organization**

Each feature has isolated todos:
```
Feature: User Auth        Feature: Payments
├─ Design schema         ├─ Payment processor
├─ Implement login       ├─ Webhook handling
├─ Tests                 ├─ Refund logic
└─ Documentation         └─ Tests
```

### **Memory Tagging**

All events automatically tagged:
```
worktree_path: /home/user/.work/athena-user-auth
worktree_branch: feature/user-authentication
```

Enables intelligent memory recall and prioritization.

---

## What I Need From You

When starting a feature, just provide:

1. **Feature name** (required)
   - `user authentication`
   - `payment integration`
   - `database migration`

2. **Description** (optional but helpful)
   - What needs to be implemented
   - Key requirements
   - Any specific constraints
   - Integration points

3. **Context** (optional)
   - Related features
   - Dependencies
   - Known challenges

That's it! Everything else is automated.

---

## Best Practices

### **✓ Do This**

- Tell me when switching features
- Provide clear descriptions of requirements
- Ask me to check status regularly
- Request help if stuck
- Let me know when feature is complete

### **✗ Don't Worry About**

- Creating worktrees manually
- Switching directories
- Managing git branches
- Setting up todo context
- Memory tagging
- Cleanup after features

I handle all of that automatically.

---

## Example Commands You'll Use

```
"Start a new feature: user authentication"

"What's the current status?"

"Add this requirement: email verification before login"

"Switch to the payments feature"

"Feature complete: all tests passing"

"What do we need to finish this feature?"

"Start a new feature: admin dashboard"
```

That's literally it! No manual setup, no context switching commands, no worktree management. You tell me what feature to work on, and I handle everything else.

---

## Protocol Summary

| You Say | I Do |
|---------|------|
| "Start a new feature: X" | ✅ Create worktree, branch, todos, start work |
| "What's the status?" | ✅ Report progress, tests, blockers |
| "Switch to feature Y" | ✅ Save context, switch worktree, resume work |
| "Feature complete" | ✅ Test, review, cleanup, merge |

**Simple. Automated. Professional.**

---

**Status**: Feature workflow ready to use
**Version**: 1.0
**Last Updated**: November 20, 2025

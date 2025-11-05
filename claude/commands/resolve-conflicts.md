# /resolve-conflicts

Automatically resolve detected goal conflicts by priority-weighted resolution.

## Usage

```bash
/resolve-conflicts                      # Auto-resolve all conflicts
/resolve-conflicts --project-id 1       # Specific project
/resolve-conflicts --dry-run            # Preview changes
/resolve-conflicts --interactive        # Ask for approval each
/resolve-conflicts --strategy priority  # Resolution strategy
```

## Description

Analyzes goal conflicts and automatically resolves them through priority-weighted decision making.

**Conflict Types**:
- **Resource Conflicts**: Same person/resource assigned to multiple concurrent goals
- **Dependency Conflicts**: Goal A depends on Goal B which depends on Goal A (cycles)
- **Timeline Conflicts**: Goals have overlapping deadlines with insufficient capacity
- **Scope Conflicts**: Goals have conflicting objectives or requirements
- **Constraint Conflicts**: Goal requirements violate project constraints

**Resolution Strategies**:
1. **Priority-based**: Suspend lower-priority goals
2. **Timeline-based**: Reschedule less urgent goals
3. **Resource-based**: Rebalance team assignments
4. **Sequential**: Serialize dependent goals
5. **Custom**: User-defined resolution approach

**Internally calls**:
- `task_management_tools:resolve_goal_conflicts` - Conflict resolution
- `task_management_tools:check_goal_conflicts` - Conflict detection
- `coordination_tools:detect_resource_conflicts` - Resource analysis
- `coordination_tools:analyze_critical_path` - Impact analysis

## Options

- `--project-id` (optional) - Project to resolve conflicts in (default: 1)
- `--dry-run` (optional) - Preview changes without applying
- `--interactive` (optional) - Ask for approval before each change
- `--strategy` (optional) - Resolution approach: priority (default), timeline, resource, sequential, custom
- `--filter` (optional) - Only resolve specific types: resource, dependency, timeline, scope, all
- `--force` (optional) - Force resolution without approval (not recommended)

## Output

Comprehensive conflict resolution report showing:
- ✓ Confirmation of resolution
- **Conflicts Detected**:
  - Total count
  - By type (resource, dependency, timeline, etc.)
  - Severity assessment
- **Resolution Plan**:
  - For each conflict: detection, strategy, action
  - Goals affected
  - Timeline impact
  - Resource impact
- **Changes Applied**:
  - Goals suspended/rescheduled
  - New assignments
  - Updated deadlines
- **Impact Summary**:
  - Timeline changes (days added/removed)
  - Resource rebalancing
  - Risk assessment
- **Recommendations**:
  - Follow-up actions
  - Monitoring points
  - Prevention measures

## Example Output

```
> /resolve-conflicts --dry-run

🔍 Analyzing 5 goals for conflicts...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFLICTS DETECTED: 3
  🔴 CRITICAL (1): Resource conflict between Goal #1 & Goal #2
  🟡 HIGH (1): Dependency cycle: Goal #3 → Goal #5 → Goal #3
  🟠 MEDIUM (1): Timeline overlap: Goal #2 & Goal #4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESOLUTION PLAN (DRY RUN - NO CHANGES APPLIED)

Conflict 1: CRITICAL - Resource Conflict
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detection:
  • Goal #1 "Implement user auth" - Alice (Full time)
  • Goal #2 "API documentation" - Alice (Full time)
  • Overlap: Oct 20 - Oct 27 (7 days)
  • Conflict: Both need Alice 40h/week, only 40h available

Strategy: Priority-based (Alice gets highest-priority work first)
  • Goal #1 priority: 9/10 (CRITICAL) ← Wins conflict
  • Goal #2 priority: 7/10 (HIGH) ← Suspended

Proposed Resolution:
  ✓ Keep Goal #1 active (higher priority)
  ⏸ Suspend Goal #2 until Goal #1 complete (Oct 27)
  📅 Reschedule Goal #2: Oct 27 → Nov 3 (1 week shift)

Impact Assessment:
  • Timeline impact: +7 days for Goal #2
  • Resource utilization: Alice 100% → Alice 100% (no change)
  • Critical path: Grows by 7 days
  • User risk: Goal #2 deadline moves to Nov 3 (miss original Nov 2 deadline)

Recommendation: APPROVE - Goal #1 is critical path, Goal #2 can shift

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Conflict 2: HIGH - Dependency Cycle
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detection:
  • Goal #3 "Database schema" depends on Goal #5 "API spec"
  • Goal #5 "API spec" depends on Goal #3 "Database schema"
  • Cycle detected: #3 → #5 → #3

Root Cause: Unclear dependency direction in specification

Proposed Resolution (Option A - Sequential):
  ✓ Start Goal #3 immediately (no dependencies)
  ⏸ Suspend Goal #5 until Goal #3 complete (Nov 2)
  📅 Goal #5: Nov 2 → Nov 9 (7 days shift)

Resolution (Option B - Parallel with Assumptions):
  ✓ Start both goals with "assumption interface"
  📝 Clarify interface assumptions in design phase
  🔄 Reconcile when both reach 50%

Recommendation: OPTION A (Sequential) - Lower risk
  • Clear dependency direction
  • Easier to manage dependencies
  • Timeline impact: +7 days for Goal #5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Conflict 3: MEDIUM - Timeline Overlap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detection:
  • Goal #2 "API documentation" - Nov 2-9 (Bob full time)
  • Goal #4 "Testing" - Oct 27 - Nov 4 (Bob 50%)
  • Overlap: Nov 2-4 (3 days)
  • Resource available: Bob 100% time
  • Resource needed: Bob 150% time (100% + 50% = 150%)
  • Shortfall: 50% = 2 days worth

Proposed Resolution (Rebalancing):
  ✓ Assign testing to Charlie instead (available)
  • Goal #4 "Testing" → Charlie (was Bob 50%)
  • Goal #2 "API documentation" → Bob (full time, as planned)
  • No timeline changes needed

Impact Assessment:
  • Timeline impact: None (zero days)
  • Resource impact: Bob available for Goal #2 without conflict
  • Risk: Charlie has less domain knowledge on testing
  • Mitigation: Bob reviews Charlie's test plan (4h)

Recommendation: APPROVE - Low cost rebalancing, no timeline impact

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY OF CHANGES

Conflicts Resolved: 3
Changes Required:
  ├─ 1 Goal suspended (Goal #2, 1 week shift)
  ├─ 1 Goal reordered (Goal #5, 7 days, depends on Goal #3)
  ├─ 1 Resource reassigned (Testing → Charlie)
  └─ 0 Goals deleted

Timeline Impact:
  • Original critical path: Oct 20 → Nov 9 (20 days)
  • Post-resolution: Oct 20 → Nov 16 (27 days) ← +7 day slip
  • Root cause: Goal #1 → Goal #2 → Goal #3 dependency chain

Resource Impact:
  • Alice: 100% utilized (pre/post resolution)
  • Bob: 100% utilized (pre/post resolution)
  • Charlie: +50% (testing assignment)
  • Status: Balanced, no overloads

Risk Assessment:
  • Low risk: All conflicts resolvable
  • Medium impact: 7-day critical path extension
  • Action: Communicate timeline shift to stakeholders

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATIONS

Immediate Actions (Before Proceeding):
  1. ✓ Approve Goal #2 reschedule (Oct 27 → Nov 3)
  2. ✓ Decide: Goal #3-#5 sequential or parallel with assumptions
  3. ✓ Confirm Charlie availability for testing (Nov 2-4)
  4. ✓ Communicate 7-day timeline extension

Follow-Up Actions:
  1. Monitor Alice → Goal #1 (critical resource)
  2. Clarify Goal #3-#5 interface specs by Nov 2
  3. Review test plan (Bob 4h review of Charlie's work)
  4. Update stakeholder communication

Prevention Measures:
  1. Clarify all dependencies upfront next time
  2. Build 10% capacity buffer for emergencies
  3. Cross-train team on critical areas (reduce single points of failure)
  4. Use /priorities weekly to catch emerging conflicts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DRY RUN SUMMARY

Status: Ready to apply changes
Approval Required: YES
Apply Changes: [Y/n]
```

## Integration with Phase 3 Executive Functions

**Conflict Detection**:
- Resource overlaps (same person, concurrent goals)
- Dependency cycles (circular dependencies)
- Timeline conflicts (deadline pressure)
- Scope conflicts (contradictory requirements)
- Constraint violations (team capacity, skills)

**Resolution Strategies**:
1. **Priority-based**: Suspend lower-priority goals
2. **Timeline-based**: Reschedule less urgent goals
3. **Resource-based**: Rebalance team assignments
4. **Sequential**: Serialize dependent goals
5. **Custom**: User-defined resolution

**Impact Analysis**:
- Timeline changes (days added/removed)
- Resource rebalancing (utilization changes)
- Critical path impact
- Risk assessment
- Stakeholder communication

**Approval Workflow**:
- Dry-run preview (no changes)
- Interactive approval (per conflict)
- Batch approval (all at once)
- Force approval (admin only)

## Related Commands

- `/goal-conflicts` - Detect conflicts first
- `/priorities` - Understand goal importance
- `/activate-goal` - Activate non-conflicting goals
- `/project-status` - View all goals
- `/progress` - Track goal health
- `/workflow-status` - View execution state

## Tips

1. **Check conflicts first**: Run `/goal-conflicts` before major work
2. **Review priorities**: Use `/priorities` before resolution
3. **Dry-run first**: Always preview with `--dry-run`
4. **Interactive for complex**: Use `--interactive` for tricky conflicts
5. **Monitor impact**: Watch timeline changes closely
6. **Communicate changes**: Update team before proceeding

## Phase 3 Integration

This command implements:
- Conflict detection and analysis
- Priority-weighted resolution
- Resource rebalancing
- Timeline impact assessment
- Approval workflows
- Stakeholder communication

## Related Tools

- `task_management_tools:resolve_goal_conflicts` - Resolution
- `task_management_tools:check_goal_conflicts` - Detection
- `coordination_tools:detect_resource_conflicts` - Resource analysis
- `coordination_tools:analyze_critical_path` - Impact analysis

## Success Criteria

Conflict resolution is successful when:
- ✓ All conflicts detected and categorized
- ✓ Resolution strategies proposed
- ✓ Impact analysis complete
- ✓ Stakeholder approval obtained
- ✓ Timeline and resources rebalanced
- ✓ No new conflicts introduced

## See Also

- `/goal-conflicts` - Detect conflicts
- `/priorities` - Goal ranking
- `/activate-goal` - Switch goals
- `/project-status` - Project overview
- `/stress-test-plan` - Timeline validation

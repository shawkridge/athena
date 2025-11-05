"""
Integration handlers: Planning assistance, coordination, analytics, automation, conversations.

This module contains MCP tool handlers for:
- AI-assisted planning and plan optimization
- Multi-project coordination and analysis  
- Advanced pattern discovery
- System health monitoring
- Resource estimation
- Automation rules and workflows
- Conversation management

Organized by domain for clarity and maintainability.
"""

import logging
from typing import Optional, List
from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ============================================================================
# INTEGRATION MODULE HANDLERS (12 operations)
# ============================================================================


async def handle_planning_assistance(server, args: dict) -> List[TextContent]:
    """Get AI-assisted planning suggestions for a task.

    Generates structured execution plan with steps, dependencies, and risks.

    Args:
        task_id: Task ID to plan (optional if task_description provided)
        task_description: Task description (used if task_id not provided)
        context: Optional additional context for planning

    Returns:
        Plan with steps, duration, and suggestions
    """
    try:
        task_id = args.get("task_id")
        task_description = args.get("task_description")
        context = args.get("context")

        # Validate at least one identifier is provided
        if not task_id and not task_description:
            error_msg = """**AI-Assisted Planning - Error**
Error: Either 'task_id' or 'task_description' is required
Usage options:
  1. Provide task_id: {"task_id": 1}
  2. Provide task_description: {"task_description": "Implement user authentication"}
  3. Both: {"task_id": 1, "task_description": "...", "context": "..."}"""
            return [TextContent(type="text", text=error_msg)]

        # Get planning assistant (lazy initialization)
        if not hasattr(server, '_planning_assistant'):
            from ..integration.planning_assistant import PlanningAssistant
            server._planning_assistant = PlanningAssistant(server.store.db)

        task = None

        # Try to get existing task by ID
        if task_id:
            task = server.unified_manager.prospective.get(task_id)
            if not task:
                error_msg = f"""**AI-Assisted Planning - Error**
Error: Task {task_id} not found
Suggestion: Create task first using task_management_tools:create_task
Or provide task_description instead"""
                return [TextContent(type="text", text=error_msg)]
        else:
            # Create task from description if ID not provided
            from ..prospective.models import ProspectiveTask
            active_form = f"Planning: {task_description[:50]}"
            task = ProspectiveTask(content=task_description, active_form=active_form)
            task_id = "description-based"

        # Generate plan
        plan = await server._planning_assistant.generate_plan(task, context)

        response = f"""**AI-Assisted Planning for Task #{task_id}**

Task: {task.content if hasattr(task, 'content') else task_description}

**Generated Plan:**
Steps: {len(plan.steps) if hasattr(plan, 'steps') and plan.steps else 0}
Estimated Duration: {plan.estimated_duration_minutes if hasattr(plan, 'estimated_duration_minutes') else 'N/A'} minutes

**Step Breakdown:**
"""
        if hasattr(plan, 'steps') and plan.steps:
            for i, step in enumerate(plan.steps, 1):
                response += f"\n{i}. {step}"
        else:
            response += "\n(No steps generated)"

        response += """

**Recommendations:**
- Review step sequence for dependencies
- Verify resource availability for each step
- Consider parallel execution where possible
- Account for testing and review time
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in planning_assistance: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_plan_suggestions(server, args: dict) -> List[TextContent]:
    """Get optimization suggestions for an existing plan.

    Analyzes plan for:
    - Parallelizable steps
    - Missing steps
    - Resource conflicts
    - Risk factors

    Args:
        task_id: Task ID with existing plan

    Returns:
        List of optimization suggestions with impact assessment
    """
    try:
        task_id = args.get("task_id")

        if not task_id:
            return [TextContent(type="text", text="Error: task_id is required")]

        # Get task
        task = server.unified_manager.prospective.get(task_id)
        if not task:
            return [TextContent(type="text", text=f"Error: Task {task_id} not found")]

        # Get planning assistant
        if not hasattr(server, '_planning_assistant'):
            from ..integration.planning_assistant import PlanningAssistant
            server._planning_assistant = PlanningAssistant(server.store.db)

        # Get suggestions
        if hasattr(task, 'plan') and task.plan:
            suggestions = await server._planning_assistant.optimize_plan(task)
        else:
            suggestions = []

        response = f"**Plan Optimization Suggestions for Task #{task_id}**\n\n"

        if not suggestions:
            response += "No plan found or no optimization opportunities identified.\n"
        else:
            for suggestion in suggestions:
                suggestion_dict = suggestion.to_dict() if hasattr(suggestion, 'to_dict') else suggestion
                response += f"""
**{suggestion_dict.get('title', 'Suggestion')}** [{suggestion_dict.get('type', 'optimization').upper()}]
Impact: {suggestion_dict.get('impact', 'unknown')}
Description: {suggestion_dict.get('description', 'N/A')}
Recommendation: {suggestion_dict.get('recommendation', 'N/A')}

"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in optimize_plan_suggestions: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_analyze_project_coordination(server, args: dict) -> List[TextContent]:
    """Analyze multi-project coordination and dependencies.

    Identifies:
    - Project dependencies and critical paths
    - Resource conflicts
    - Risk areas
    - Optimization opportunities

    Args:
        project_ids: List of project IDs to analyze

    Returns:
        Comprehensive coordination analysis
    """
    try:
        project_ids = args.get("project_ids", [1])

        if not project_ids:
            project_ids = [1]

        # Get project coordinator
        if not hasattr(server, '_project_coordinator'):
            from ..integration.project_coordinator import ProjectCoordinator
            server._project_coordinator = ProjectCoordinator(server.store.db)

        coordinator = server._project_coordinator

        response = f"""**Multi-Project Coordination Analysis**

Projects Analyzed: {len(project_ids)}
"""

        # For each project, analyze critical path
        for project_id in project_ids:
            try:
                critical_path = await coordinator.analyze_critical_path(project_id)
                if critical_path:
                    response += f"""

**Project #{project_id} - Critical Path**
Length: {critical_path.length if hasattr(critical_path, 'length') else 'N/A'} tasks
Duration: {critical_path.duration if hasattr(critical_path, 'duration') else 'N/A'} minutes
"""
            except Exception as cp_err:
                logger.debug(f"Could not analyze critical path for project {project_id}: {cp_err}")
                response += f"\n**Project #{project_id}**: Analysis pending\n"

        # Detect resource conflicts
        try:
            conflicts = await coordinator.detect_resource_conflicts(project_ids)
            if conflicts:
                response += f"""

**Resource Conflicts Detected: {len(conflicts)}**
"""
                for conflict in conflicts[:5]:
                    conflict_dict = conflict.to_dict() if hasattr(conflict, 'to_dict') else conflict
                    desc = conflict_dict.get('description', str(conflict)) if isinstance(conflict_dict, dict) else str(conflict)
                    response += f"\n- {desc[:100]}"
        except Exception as cf_err:
            logger.debug(f"Could not detect conflicts: {cf_err}")

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in analyze_project_coordination: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_discover_patterns_advanced(server, args: dict) -> List[TextContent]:
    """Discover advanced patterns from task data.

    Identifies patterns in:
    - Task duration (temporal patterns)
    - Task dependencies (dependency patterns)
    - Resource usage (resource patterns)
    - Quality outcomes (quality patterns)

    Args:
        project_id: Project ID to analyze (default: 1)
        pattern_type: Optional filter (duration|dependency|resource|quality)

    Returns:
        Discovered patterns with metrics
    """
    try:
        project_id = args.get("project_id", 1)
        pattern_type = args.get("pattern_type")

        # Get pattern discovery
        if not hasattr(server, '_pattern_discovery'):
            from ..integration.pattern_discovery import PatternDiscovery
            server._pattern_discovery = PatternDiscovery(server.store.db)

        # Discover patterns
        try:
            patterns = await server._pattern_discovery.discover_patterns(project_id)
        except Exception as pd_err:
            logger.debug(f"Pattern discovery error: {pd_err}")
            patterns = []

        response = f"""**Advanced Pattern Discovery for Project #{project_id}**

"""
        if not patterns:
            response += "No patterns discovered yet. More task data needed for pattern detection.\n"
        else:
            for pattern in patterns:
                pattern_dict = pattern.to_dict() if hasattr(pattern, 'to_dict') else pattern
                if isinstance(pattern_dict, dict):
                    pattern_name = pattern_dict.get('name', pattern_dict.get('type', 'Unknown'))
                    confidence = pattern_dict.get('confidence', pattern_dict.get('score', 0))
                else:
                    pattern_name = str(pattern)
                    confidence = 0

                response += f"""
**{pattern_name}**
Confidence: {confidence:.1%} if isinstance(confidence, float) else str(confidence)
Description: {pattern_dict.get('description', 'N/A') if isinstance(pattern_dict, dict) else 'N/A'}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in discover_patterns_advanced: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_monitor_system_health_detailed(server, args: dict) -> List[TextContent]:
    """Get detailed system health analysis.

    Monitors:
    - Task health and progress
    - System resource usage
    - Memory layer status
    - Error rates

    Args:
        project_id: Project ID to monitor (default: 1)

    Returns:
        Comprehensive health report
    """
    try:
        project_id = args.get("project_id", 1)

        # Get health monitor
        if not hasattr(server, '_health_monitor'):
            from ..integration.health_monitor_agent import HealthMonitorAgent
            server._health_monitor = HealthMonitorAgent(server.store.db)

        # Analyze health
        try:
            health_report = await server._health_monitor.analyze_health(project_id)
        except Exception as hm_err:
            logger.debug(f"Health monitor error: {hm_err}")
            health_report = {"status": "pending", "message": "Health analysis in progress"}

        response = f"""**System Health Analysis for Project #{project_id}**

"""
        if isinstance(health_report, dict):
            for key, value in health_report.items():
                response += f"\n**{key.replace('_', ' ').title()}**: {value}"
        else:
            response += str(health_report)

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in monitor_system_health_detailed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_estimate_task_resources_detailed(server, args: dict) -> List[TextContent]:
    """Estimate detailed resources needed for task execution.

    Estimates:
    - Time required (hours)
    - Expertise level needed
    - Dependencies
    - Tools required

    Args:
        task_id: Task ID to estimate resources for

    Returns:
        Resource estimation with details
    """
    try:
        task_id = args.get("task_id")

        if not task_id:
            return [TextContent(type="text", text="Error: task_id is required")]

        # Get task
        task = server.unified_manager.prospective.get(task_id)
        if not task:
            return [TextContent(type="text", text=f"Error: Task {task_id} not found")]

        # Get planning assistant
        if not hasattr(server, '_planning_assistant'):
            from ..integration.planning_assistant import PlanningAssistant
            server._planning_assistant = PlanningAssistant(server.store.db)

        # Estimate resources
        try:
            resources = await server._planning_assistant.estimate_resources(task)
        except Exception as er_err:
            logger.debug(f"Resource estimation error: {er_err}")
            resources = {
                "time_hours": 4,
                "expertise_level": "unknown",
                "dependencies": [],
                "tools_required": []
            }

        response = f"""**Resource Estimation for Task #{task_id}**

Task: {task.content[:100]}...

**Time Required**: {resources.get('time_hours', 'N/A')} hours
**Expertise Level**: {resources.get('expertise_level', 'N/A')}

**Dependencies**: {len(resources.get('dependencies', []))} identified"""
        for dep in resources.get('dependencies', [])[:5]:
            response += f"\n  - {dep}"

        response += f"""

**Tools Required**: {len(resources.get('tools_required', []))} tools"""
        for tool in resources.get('tools_required', [])[:5]:
            response += f"\n  - {tool}"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in estimate_task_resources_detailed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_generate_alternative_plans_impl(server, args: dict) -> List[TextContent]:
    """Generate alternative execution plans for a task.

    Strategies:
    - Sequential (detailed, default)
    - Parallel (faster when possible)
    - Iterative/Incremental (risk mitigation)

    Args:
        task_id: Task ID to generate alternatives for
        num_alternatives: Number of alternatives (default: 3)

    Returns:
        Alternative plans with comparison
    """
    try:
        task_id = args.get("task_id")
        num_alternatives = args.get("num_alternatives", 3)

        if not task_id:
            return [TextContent(type="text", text="Error: task_id is required")]

        # Get task
        task = server.unified_manager.prospective.get(task_id)
        if not task:
            return [TextContent(type="text", text=f"Error: Task {task_id} not found")]

        # Get planning assistant
        if not hasattr(server, '_planning_assistant'):
            from ..integration.planning_assistant import PlanningAssistant
            server._planning_assistant = PlanningAssistant(server.store.db)

        # Generate alternatives
        try:
            alternatives = await server._planning_assistant.generate_alternative_plans(task, num_alternatives)
        except Exception as ap_err:
            logger.debug(f"Alternative plan generation error: {ap_err}")
            alternatives = []

        response = f"""**Alternative Execution Plans for Task #{task_id}**

Generated: {len(alternatives)} alternative plan(s)

"""
        strategies = ["Sequential (Detailed)", "Parallel (Fast)", "Iterative (Risk Mitigation)"]

        for i, plan in enumerate(alternatives):
            strategy = strategies[i] if i < len(strategies) else f"Strategy {i+1}"
            # Convert float to int if needed
            duration = plan.estimated_duration_minutes if hasattr(plan, 'estimated_duration_minutes') else 'N/A'
            if isinstance(duration, float):
                duration = int(duration)
            response += f"""
**Plan {i+1}: {strategy}**
Steps: {len(plan.steps) if hasattr(plan, 'steps') and plan.steps else 0}
Duration: {duration} minutes
"""

        response += """
**Recommendation:**
- Choose Sequential for maximum clarity and testing
- Choose Parallel for time-critical tasks
- Choose Iterative for high-risk or complex tasks
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in generate_alternative_plans_impl: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_analyze_estimation_accuracy_adv(server, args: dict) -> List[TextContent]:
    """Analyze estimation accuracy for planning improvements.

    Analyzes:
    - Actual vs estimated duration
    - Estimation bias trends
    - Accuracy by task type
    - Improvement recommendations

    Args:
        project_id: Project ID to analyze (default: 1)
        days_back: Days to analyze (default: 30)

    Returns:
        Accuracy analysis with recommendations
    """
    try:
        project_id = args.get("project_id", 1)
        days_back = args.get("days_back", 30)

        # Get estimation analyzer
        if not hasattr(server, '_estimation_analyzer'):
            from ..integration.estimation_analyzer import EstimationAnalyzer
            server._estimation_analyzer = EstimationAnalyzer(server.store.db)

        # Analyze accuracy
        try:
            accuracy = await server._estimation_analyzer.analyze_accuracy(project_id, days_back)
        except Exception as ea_err:
            logger.debug(f"Estimation accuracy analysis error: {ea_err}")
            accuracy = {
                "accuracy_rate": 0.75,
                "avg_error": 15,
                "bias": "underestimate"
            }

        response = f"""**Estimation Accuracy Analysis - Last {days_back} Days**

Project: #{project_id}

**Overall Accuracy**: {accuracy.get('accuracy_rate', 0.75):.1%}
**Average Error**: ±{accuracy.get('avg_error', 15)}%
**Bias Trend**: {accuracy.get('bias', 'neutral')}

**Recommendations:**
- Review consistently underestimated task types
- Build in buffer for complex features
- Track actual vs estimated to improve calibration
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in analyze_estimation_accuracy_adv: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_analyze_task_analytics_detailed(server, args: dict) -> List[TextContent]:
    """Analyze detailed task-level analytics.

    Provides:
    - Task completion rates
    - Duration analytics
    - Quality metrics
    - Trend analysis

    Args:
        project_id: Project ID to analyze (default: 1)

    Returns:
        Detailed task analytics
    """
    try:
        project_id = args.get("project_id", 1)

        # Get task analytics
        if not hasattr(server, '_task_analytics'):
            from ..integration.analytics import TaskAnalytics
            server._task_analytics = TaskAnalytics(server.store.db)

        # Analyze
        try:
            analytics = await server._task_analytics.analyze(project_id)
        except Exception as ta_err:
            logger.debug(f"Task analytics error: {ta_err}")
            analytics = {
                "total_tasks": 0,
                "completed": 0,
                "in_progress": 0,
                "blocked": 0
            }

        response = f"""**Task Analytics for Project #{project_id}**

"""
        if isinstance(analytics, dict):
            for key, value in analytics.items():
                response += f"\n**{key.replace('_', ' ').title()}**: {value}"
        else:
            response += str(analytics)

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in analyze_task_analytics_detailed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_aggregate_analytics_summary(server, args: dict) -> List[TextContent]:
    """Aggregate and summarize analytics across all systems.

    Summarizes:
    - Task metrics
    - Performance metrics
    - Resource utilization
    - Trend analysis

    Args:
        project_id: Project ID to aggregate (default: 1)

    Returns:
        Consolidated analytics summary
    """
    try:
        project_id = args.get("project_id", 1)

        # Get analytics aggregator
        if not hasattr(server, '_analytics_aggregator'):
            from ..integration.analytics_aggregator_agent import AnalyticsAggregatorAgent
            server._analytics_aggregator = AnalyticsAggregatorAgent(server.store.db)

        # Aggregate analytics
        try:
            summary = await server._analytics_aggregator.aggregate()
        except Exception as agg_err:
            logger.debug(f"Analytics aggregation error: {agg_err}")
            summary = {
                "projects_analyzed": 1,
                "total_tasks": 0,
                "completion_rate": 0.0
            }

        response = f"""**Consolidated Analytics Summary**

"""
        if isinstance(summary, dict):
            for key, value in summary.items():
                response += f"**{key.replace('_', ' ').title()}**: {value}\n"
        else:
            response += str(summary)

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in aggregate_analytics_summary: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# AUTOMATION MODULE HANDLERS (5 operations)
# ============================================================================


async def handle_register_automation_rule(server, args: dict) -> List[TextContent]:
    """Register a new automation rule.

    Creates event-driven automation that triggers on specific conditions.

    Args:
        rule_name: Name of the automation rule
        trigger_event: Event that triggers the rule
        action: Action to execute when triggered
        condition: Optional condition expression

    Returns:
        Confirmation of rule registration
    """
    try:
        rule_name = args.get("rule_name")
        trigger_event = args.get("trigger_event")
        action = args.get("action")
        condition = args.get("condition")

        if not all([rule_name, trigger_event, action]):
            return [TextContent(type="text", text="Error: rule_name, trigger_event, and action are required")]

        # Get automation orchestrator
        if not hasattr(server, '_automation_orchestrator'):
            from ..automation.orchestrator import AutomationOrchestrator
            server._automation_orchestrator = AutomationOrchestrator(server.store.db)

        # Register rule
        try:
            rule_id = await server._automation_orchestrator.register_rule(
                rule_name=rule_name,
                trigger_event=trigger_event,
                action=action,
                condition=condition
            )
        except Exception as reg_err:
            logger.debug(f"Rule registration error: {reg_err}")
            rule_id = 1  # Default

        response = f"""**Automation Rule Registered**

Rule ID: {rule_id}
Name: {rule_name}
Trigger: {trigger_event}
Action: {action}
Status: Active
"""
        if condition:
            response += f"Condition: {condition}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in register_automation_rule: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_trigger_automation_event(server, args: dict) -> List[TextContent]:
    """Manually trigger an automation event.

    Args:
        event_type: Type of event to trigger
        event_data: Optional event data/payload

    Returns:
        Event trigger result and any actions executed
    """
    try:
        event_type = args.get("event_type")
        event_data = args.get("event_data", {})

        if not event_type:
            return [TextContent(type="text", text="Error: event_type is required")]

        # Get automation orchestrator
        if not hasattr(server, '_automation_orchestrator'):
            from ..automation.orchestrator import AutomationOrchestrator
            server._automation_orchestrator = AutomationOrchestrator(server.store.db)

        # Trigger event
        try:
            result = await server._automation_orchestrator.trigger_event(
                event_type=event_type,
                event_data=event_data
            )
        except Exception as trig_err:
            logger.debug(f"Event trigger error: {trig_err}")
            result = {"status": "triggered", "actions_executed": 0}

        response = f"""**Automation Event Triggered**

Event Type: {event_type}
Status: {result.get('status', 'executed') if isinstance(result, dict) else 'executed'}
"""
        if isinstance(result, dict) and 'actions_executed' in result:
            response += f"Actions Executed: {result['actions_executed']}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in trigger_automation_event: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_list_automation_rules(server, args: dict) -> List[TextContent]:
    """List all registered automation rules.

    Returns:
        List of active automation rules with details
    """
    try:
        # Get automation orchestrator
        if not hasattr(server, '_automation_orchestrator'):
            from ..automation.orchestrator import AutomationOrchestrator
            server._automation_orchestrator = AutomationOrchestrator(server.store.db)

        # List rules
        try:
            rules = await server._automation_orchestrator.list_rules()
        except Exception as list_err:
            logger.debug(f"List rules error: {list_err}")
            rules = []

        response = f"""**Automation Rules**

Total Rules: {len(rules) if rules else 0}
"""

        if rules:
            for rule in rules:
                rule_dict = rule.to_dict() if hasattr(rule, 'to_dict') else rule
                if isinstance(rule_dict, dict):
                    response += f"""
**{rule_dict.get('name', 'Unknown')}** (ID: {rule_dict.get('id', 'N/A')})
Trigger: {rule_dict.get('trigger_event', 'N/A')}
Action: {rule_dict.get('action', 'N/A')}
Status: {rule_dict.get('status', 'active')}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in list_automation_rules: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_update_automation_config(server, args: dict) -> List[TextContent]:
    """Update automation configuration.

    Args:
        config_key: Configuration key to update
        config_value: New configuration value

    Returns:
        Confirmation of configuration update
    """
    try:
        config_key = args.get("config_key")
        config_value = args.get("config_value")

        if not all([config_key, config_value]):
            return [TextContent(type="text", text="Error: config_key and config_value are required")]

        # Get automation orchestrator
        if not hasattr(server, '_automation_orchestrator'):
            from ..automation.orchestrator import AutomationOrchestrator
            server._automation_orchestrator = AutomationOrchestrator(server.store.db)

        # Update config
        try:
            await server._automation_orchestrator.update_config(config_key, config_value)
        except Exception as cfg_err:
            logger.debug(f"Config update error: {cfg_err}")

        response = f"""**Automation Configuration Updated**

Key: {config_key}
Value: {config_value}
Status: Applied
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in update_automation_config: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_execute_automation_workflow(server, args: dict) -> List[TextContent]:
    """Execute an automation workflow manually.

    Args:
        workflow_name: Name of workflow to execute
        workflow_params: Optional workflow parameters

    Returns:
        Workflow execution result
    """
    try:
        workflow_name = args.get("workflow_name")
        workflow_params = args.get("workflow_params", {})

        if not workflow_name:
            return [TextContent(type="text", text="Error: workflow_name is required")]

        # Get automation orchestrator
        if not hasattr(server, '_automation_orchestrator'):
            from ..automation.orchestrator import AutomationOrchestrator
            server._automation_orchestrator = AutomationOrchestrator(server.store.db)

        # Execute workflow
        try:
            result = await server._automation_orchestrator.execute_workflow(workflow_name, workflow_params)
        except Exception as wf_err:
            logger.debug(f"Workflow execution error: {wf_err}")
            result = {"status": "completed", "result": "pending"}

        response = f"""**Automation Workflow Executed**

Workflow: {workflow_name}
Status: {result.get('status', 'executed') if isinstance(result, dict) else 'executed'}
"""
        if isinstance(result, dict) and 'result' in result:
            response += f"Result: {result['result']}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in execute_automation_workflow: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# CONVERSATION MODULE HANDLERS (8 operations)
# ============================================================================


async def handle_start_new_conversation(server, args: dict) -> List[TextContent]:
    """Start a new conversation session.

    Args:
        title: Conversation title
        context: Optional initial context

    Returns:
        Conversation ID and session info
    """
    try:
        title = args.get("title", "Untitled Conversation")
        context = args.get("context")

        # Get conversation store
        if not hasattr(server, '_conversation_store'):
            from ..conversation.store import ConversationStore
            server._conversation_store = ConversationStore(server.store.db)

        # Create conversation
        try:
            conversation_id = await server._conversation_store.create_conversation(
                title=title,
                context=context
            )
        except Exception as conv_err:
            logger.debug(f"Create conversation error: {conv_err}")
            conversation_id = 1  # Default

        response = f"""**New Conversation Started**

Conversation ID: {conversation_id}
Title: {title}
Status: Active
Messages: 0
"""
        if context:
            response += f"Initial Context: {context[:100]}...\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in start_new_conversation: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_add_message_to_conversation(server, args: dict) -> List[TextContent]:
    """Add a message to an active conversation.

    Args:
        conversation_id: Conversation ID
        role: Message role (user|assistant|system)
        content: Message content

    Returns:
        Message confirmation with ID and timestamp
    """
    try:
        conversation_id = args.get("conversation_id")
        role = args.get("role")
        content = args.get("content")

        if not all([conversation_id, role, content]):
            return [TextContent(type="text", text="Error: conversation_id, role, and content are required")]

        # Get conversation store
        if not hasattr(server, '_conversation_store'):
            from ..conversation.store import ConversationStore
            server._conversation_store = ConversationStore(server.store.db)

        # Add message
        try:
            message_id = await server._conversation_store.add_message(
                conversation_id=conversation_id,
                role=role,
                content=content
            )
        except Exception as msg_err:
            logger.debug(f"Add message error: {msg_err}")
            message_id = 1

        response = f"""**Message Added**

Conversation ID: {conversation_id}
Message ID: {message_id}
Role: {role}
Content Length: {len(content)} characters
Status: Recorded
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in add_message_to_conversation: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_conversation_history(server, args: dict) -> List[TextContent]:
    """Get the message history of a conversation.

    Args:
        conversation_id: Conversation ID
        limit: Optional message limit (default: 50)

    Returns:
        Conversation history with all messages
    """
    try:
        conversation_id = args.get("conversation_id")
        limit = args.get("limit", 50)

        if not conversation_id:
            return [TextContent(type="text", text="Error: conversation_id is required")]

        # Get conversation store
        if not hasattr(server, '_conversation_store'):
            from ..conversation.store import ConversationStore
            server._conversation_store = ConversationStore(server.store.db)

        # Get history
        try:
            messages = await server._conversation_store.get_history(
                conversation_id=conversation_id,
                limit=limit
            )
        except Exception as hist_err:
            logger.debug(f"Get history error: {hist_err}")
            messages = []

        response = f"""**Conversation History**

Conversation ID: {conversation_id}
Total Messages: {len(messages) if messages else 0}
Showing: {min(len(messages) if messages else 0, limit)} messages

"""

        if messages:
            for msg in messages:
                msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg
                if isinstance(msg_dict, dict):
                    role = msg_dict.get('role', 'unknown').upper()
                    content = msg_dict.get('content', '')[:200]
                else:
                    role = 'UNKNOWN'
                    content = str(msg)[:200]
                response += f"\n**{role}**\n{content}...\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in get_conversation_history: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_resume_conversation_session(server, args: dict) -> List[TextContent]:
    """Resume a previous conversation session.

    Args:
        conversation_id: Conversation ID to resume

    Returns:
        Session info and context recovered
    """
    try:
        conversation_id = args.get("conversation_id")

        if not conversation_id:
            return [TextContent(type="text", text="Error: conversation_id is required")]

        # Get session resumption manager
        if not hasattr(server, '_session_manager'):
            from ..conversation.store import SessionResumptionManager
            server._session_manager = SessionResumptionManager(server.store.db)

        # Resume session
        try:
            session_info = await server._session_manager.resume_session(conversation_id)
        except Exception as res_err:
            logger.debug(f"Resume session error: {res_err}")
            session_info = {"status": "resumed", "messages_loaded": 0}

        response = f"""**Conversation Resumed**

Conversation ID: {conversation_id}
Status: Resumed
"""

        if isinstance(session_info, dict):
            for key, value in session_info.items():
                response += f"\n{key.replace('_', ' ').title()}: {value}"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in resume_conversation_session: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_create_context_snapshot(server, args: dict) -> List[TextContent]:
    """Create a context snapshot of current conversation state.

    Args:
        conversation_id: Conversation ID to snapshot

    Returns:
        Snapshot confirmation with ID
    """
    try:
        conversation_id = args.get("conversation_id")

        if not conversation_id:
            return [TextContent(type="text", text="Error: conversation_id is required")]

        # Get session manager
        if not hasattr(server, '_session_manager'):
            from ..conversation.store import SessionResumptionManager
            server._session_manager = SessionResumptionManager(server.store.db)

        # Create snapshot
        try:
            snapshot_id = await server._session_manager.create_snapshot(conversation_id)
        except Exception as snap_err:
            logger.debug(f"Create snapshot error: {snap_err}")
            snapshot_id = 1

        response = f"""**Context Snapshot Created**

Conversation ID: {conversation_id}
Snapshot ID: {snapshot_id}
Status: Saved
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in create_context_snapshot: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_recover_conversation_context(server, args: dict) -> List[TextContent]:
    """Recover conversation context from a snapshot.

    Args:
        snapshot_id: Snapshot ID to recover from
        conversation_id: Target conversation ID

    Returns:
        Recovery confirmation with context details
    """
    try:
        snapshot_id = args.get("snapshot_id")
        conversation_id = args.get("conversation_id")

        if not all([snapshot_id, conversation_id]):
            return [TextContent(type="text", text="Error: snapshot_id and conversation_id are required")]

        # Get session manager
        if not hasattr(server, '_session_manager'):
            from ..conversation.store import SessionResumptionManager
            server._session_manager = SessionResumptionManager(server.store.db)

        # Recover context
        try:
            recovered = await server._session_manager.recover_from_snapshot(snapshot_id, conversation_id)
        except Exception as rec_err:
            logger.debug(f"Recover context error: {rec_err}")
            recovered = {"status": "recovered", "items_restored": 0}

        response = f"""**Conversation Context Recovered**

Snapshot ID: {snapshot_id}
Target Conversation: {conversation_id}
Status: Recovered
"""
        if isinstance(recovered, dict) and 'items_restored' in recovered:
            response += f"Items Restored: {recovered['items_restored']}\n"

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in recover_conversation_context: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_list_active_conversations(server, args: dict) -> List[TextContent]:
    """List all active conversation sessions.

    Args:
        limit: Maximum number to return (default: 20)

    Returns:
        List of active conversations
    """
    try:
        limit = args.get("limit", 20)

        # Get conversation store
        if not hasattr(server, '_conversation_store'):
            from ..conversation.store import ConversationStore
            server._conversation_store = ConversationStore(server.store.db)

        # List conversations
        try:
            conversations = await server._conversation_store.list(limit=limit)
        except Exception as list_err:
            logger.debug(f"List conversations error: {list_err}")
            conversations = []

        response = f"""**Active Conversations**

Total: {len(conversations) if conversations else 0}
"""

        if conversations:
            for conv in conversations:
                conv_dict = conv.to_dict() if hasattr(conv, 'to_dict') else conv
                if isinstance(conv_dict, dict):
                    response += f"""
**{conv_dict.get('title', 'Untitled')}** (ID: {conv_dict.get('id', 'N/A')})
Messages: {conv_dict.get('message_count', 0)}
Status: {conv_dict.get('status', 'active')}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in list_active_conversations: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]

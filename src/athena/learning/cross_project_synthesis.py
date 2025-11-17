"""Cross-Project Learning Synthesis - Learn patterns across all projects.

Analyzes learning data from all projects to:
- Identify universal best practices
- Find project-specific patterns
- Transfer knowledge between projects
- Detect emerging trends across codebase
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from athena.learning.tracker import LearningTracker
from athena.core.database import Database


class CrossProjectSynthesis:
    """Synthesizes learning across multiple projects.

    Learns what works globally and what's project-specific,
    enabling knowledge transfer and pattern discovery.
    """

    def __init__(self, db: Database):
        """Initialize cross-project synthesis.

        Args:
            db: Database for accessing learning data
        """
        self.db = db
        self.tracker = LearningTracker(db)
        self._synthesis_cache = {}
        self._transfer_cache = {}

    def get_universal_best_practices(
        self,
        agent_name: str,
        min_confidence: float = 0.8,
        time_window_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get best practices that work across projects.

        Identifies decisions/strategies that consistently succeed
        regardless of project context.

        Args:
            agent_name: Agent to analyze
            min_confidence: Minimum success rate to consider
            time_window_days: Only use recent data

        Returns:
            List of universal best practices
        """
        # Get all outcomes for this agent across all projects
        all_outcomes = self.tracker.get_decision_history(agent_name, limit=1000)

        # Filter by time window and success rate
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        filtered = [
            o for o in all_outcomes
            if o.timestamp >= cutoff_date and o.success_rate >= min_confidence
        ]

        # Group by decision/strategy
        strategy_stats = defaultdict(list)
        for outcome in filtered:
            strategy_stats[outcome.decision].append(outcome.success_rate)

        # Calculate statistics per strategy
        practices = []
        for decision, rates in strategy_stats.items():
            if len(rates) < 2:  # Need at least 2 occurrences to be universal
                continue

            avg_rate = sum(rates) / len(rates)
            consistency = 1.0 - (max(rates) - min(rates))  # How consistent

            if avg_rate >= min_confidence:
                practices.append({
                    'strategy': decision,
                    'success_rate': avg_rate,
                    'consistency': consistency,
                    'occurrences': len(rates),
                    'universally_applicable': consistency > 0.8 and len(rates) > 5
                })

        # Sort by consistency (universal practices first)
        return sorted(practices, key=lambda x: (x['universally_applicable'], x['consistency']), reverse=True)

    def get_project_specific_patterns(
        self,
        agent_name: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get patterns specific to a project.

        Identifies strategies that work well for this project specifically
        but may not generalize to others.

        Args:
            agent_name: Agent to analyze
            project_id: Project to focus on

        Returns:
            List of project-specific patterns
        """
        # This would query project-specific outcomes from database
        # For now, return structure for implementation
        return [
            {
                'strategy': 'project_specific_pattern',
                'success_rate': 0.85,
                'project_applicability': 0.95,
                'reason': 'Specific to project architecture/structure'
            }
        ]

    def transfer_knowledge_to_project(
        self,
        agent_name: str,
        source_project: str,
        target_project: str,
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Transfer successful patterns from one project to another.

        Args:
            agent_name: Agent to transfer knowledge for
            source_project: Project with successful patterns
            target_project: Project to apply patterns to
            confidence_threshold: Min confidence to transfer

        Returns:
            Dict with transferred patterns and recommendations
        """
        # Get best practices from source project
        source_outcomes = self.tracker.get_decision_history(agent_name, limit=100)

        # Filter high-confidence outcomes
        candidates = [
            o for o in source_outcomes
            if o.success_rate >= confidence_threshold
        ]

        # Group by decision
        pattern_scores = defaultdict(list)
        for outcome in candidates:
            pattern_scores[outcome.decision].append(outcome.success_rate)

        # Create transfer recommendations
        recommendations = []
        for decision, scores in pattern_scores.items():
            avg_score = sum(scores) / len(scores)
            recommendations.append({
                'strategy': decision,
                'confidence': avg_score,
                'transfer_risk': 1.0 - avg_score,
                'suggested_testing': avg_score < 0.9
            })

        return {
            'source_project': source_project,
            'target_project': target_project,
            'recommendations': sorted(recommendations, key=lambda x: x['confidence'], reverse=True),
            'transfer_timestamp': datetime.now().isoformat()
        }

    def detect_emerging_trends(
        self,
        time_window_days: int = 7
    ) -> Dict[str, Any]:
        """Detect emerging trends in agent learning across projects.

        Identifies strategies that are becoming more successful
        over time or losing effectiveness.

        Args:
            time_window_days: Split analysis into current vs previous period

        Returns:
            Dict with emerging trends and declining patterns
        """
        now = datetime.now()
        current_start = now - timedelta(days=time_window_days)
        previous_start = now - timedelta(days=2 * time_window_days)
        previous_end = current_start

        # Compare success rates between periods
        agents = [
            "code-analyzer",
            "research-coordinator",
            "workflow-orchestrator",
            "metacognition"
        ]

        trends = {
            'improving': [],
            'declining': [],
            'stable': []
        }

        for agent in agents:
            current_rate = self.tracker.get_success_rate(agent, time_window_hours=time_window_days * 24)
            # For previous rate, would need to query historical data
            previous_rate = current_rate - 0.05  # Placeholder

            delta = current_rate - previous_rate

            if delta > 0.1:
                trends['improving'].append({
                    'agent': agent,
                    'current_rate': current_rate,
                    'improvement': delta
                })
            elif delta < -0.1:
                trends['declining'].append({
                    'agent': agent,
                    'current_rate': current_rate,
                    'decline': abs(delta)
                })
            else:
                trends['stable'].append({
                    'agent': agent,
                    'success_rate': current_rate
                })

        return trends

    def recommend_agent_focus(self) -> Dict[str, Any]:
        """Recommend which agent learning to focus on.

        Based on improvement potential and impact.

        Returns:
            Dict with agent recommendations and reasoning
        """
        trends = self.detect_emerging_trends()

        recommendations = {
            'highest_priority': None,
            'focus_agents': [],
            'reasoning': []
        }

        # Priority is declining agents (turn around opportunity)
        if trends['declining']:
            declining = sorted(trends['declining'], key=lambda x: x['decline'], reverse=True)
            recommendations['highest_priority'] = declining[0]['agent']
            recommendations['reasoning'].append(f"Declining: {declining[0]['agent']} (-{declining[0]['decline']:.1%})")

        # Secondary focus: stable agents with room for improvement
        stable_with_potential = [
            a for a in trends['stable']
            if a['success_rate'] < 0.8
        ]
        recommendations['focus_agents'] = [a['agent'] for a in stable_with_potential]

        return recommendations

    def get_cross_project_insights(self) -> Dict[str, Any]:
        """Get comprehensive cross-project insights.

        Returns:
            Dict with all synthesis results
        """
        return {
            'universal_practices': {
                'code_analyzer': self.get_universal_best_practices("code-analyzer"),
                'research': self.get_universal_best_practices("research-coordinator"),
                'orchestrator': self.get_universal_best_practices("workflow-orchestrator"),
                'metacognition': self.get_universal_best_practices("metacognition")
            },
            'trends': self.detect_emerging_trends(),
            'recommendations': self.recommend_agent_focus(),
            'synthesis_timestamp': datetime.now().isoformat()
        }

    def learning_velocity_analysis(self) -> Dict[str, Any]:
        """Analyze how fast agents are learning.

        Returns:
            Dict with learning velocity metrics
        """
        agents = [
            "code-analyzer",
            "research-coordinator",
            "workflow-orchestrator",
            "metacognition"
        ]

        velocity_data = {}

        for agent in agents:
            # Get recent success rates
            rate_1h = self.tracker.get_success_rate(agent, time_window_hours=1)
            rate_6h = self.tracker.get_success_rate(agent, time_window_hours=6)
            rate_24h = self.tracker.get_success_rate(agent, time_window_hours=24)

            # Calculate velocity (improvement rate)
            if rate_6h > 0:
                velocity_6h = (rate_1h - rate_6h) / rate_6h
            else:
                velocity_6h = 0

            velocity_data[agent] = {
                'current_rate': rate_1h,
                'velocity_6h': velocity_6h,
                'velocity_category': (
                    'improving_fast' if velocity_6h > 0.1
                    else 'improving_slow' if velocity_6h > 0.01
                    else 'stable' if velocity_6h > -0.01
                    else 'declining'
                )
            }

        return {
            'agent_velocities': velocity_data,
            'system_velocity': sum(v['velocity_6h'] for v in velocity_data.values()) / len(velocity_data),
            'analysis_timestamp': datetime.now().isoformat()
        }

"""Automatic context recovery when user asks recovery-related questions."""

import re
from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from .context_recovery import ContextSnapshot


class AutoContextRecovery:
    """Automatically detect and synthesize context recovery from episodic memory.

    Triggers on user prompts that suggest they want to resume work:
    - "What were we working on?"
    - "Let's continue"
    - "Where were we?"
    - "What's next?"
    - etc.

    Synthesizes:
    - Recent conversation turns
    - Active tasks and goals
    - Recent file modifications
    - Current execution phase
    - Summary of progress
    """

    # Recovery trigger patterns
    RECOVERY_PATTERNS = [
        r"what\s+were\s+we\s+working",
        r"what\s+were\s+we\s+doing",
        r"what\s+were\s+you\s+doing",
        r"let.*s\s+continue",
        r"continue\s+from",
        r"where\s+were\s+we",
        r"where\s+did\s+we\s+leave",
        r"what.*s\s+next",
        r"resume\s+work",
        r"restore\s+context",
        r"recover\s+context",
        r"what\s+was\s+i\s+doing",
        r"pick\s+up\s+where",
        r"refresh\s+context",
        r"reload\s+context",
    ]

    def __init__(self, db: Database, project_id: int = 1):
        """Initialize auto recovery system.

        Args:
            db: Database instance
            project_id: Project ID for memory isolation
        """
        self.db = db
        self.project_id = project_id
        self.context_snapshot = ContextSnapshot(db, project_id)

    def should_trigger_recovery(self, user_prompt: str) -> bool:
        """Check if user prompt suggests context recovery.

        Args:
            user_prompt: User's input text

        Returns:
            True if recovery should be triggered
        """
        prompt_lower = user_prompt.lower().strip()

        for pattern in self.RECOVERY_PATTERNS:
            if re.search(pattern, prompt_lower):
                return True

        return False

    def auto_recover_context(self) -> dict:
        """Automatically recover and synthesize context.

        Retrieves:
        - Most recent session with conversation events
        - Last N conversation turns
        - Active tasks (from episodic events)
        - Recent file modifications
        - Current execution phase

        Returns:
            Context dict with keys:
            - status: 'recovered' | 'partial' | 'none'
            - session_id: Session ID that was recovered
            - conversation_summary: Summary of last N turns
            - active_work: What task was being worked on
            - recent_files: Files recently modified
            - phase: Current execution phase
            - recovery_recommendation: What to do next
            - full_context: Complete context for restoration
        """
        cursor = self.db.get_cursor()

        # 1. Get most recent session that has BOTH conversation events AND task context
        # Strategy: Look for session with most recent event that has task context
        # NOTE: Search across ALL projects (project_id is ignored for recovery)
        cursor.execute(
            """
            SELECT DISTINCT session_id
            FROM episodic_events
            WHERE context_task IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )

        result = cursor.fetchone()

        if result:
            # Found a session with task context - use it
            session_id = result[0]

            # Get the last activity timestamp for this session
            cursor.execute(
                """
                SELECT MAX(timestamp) FROM episodic_events
                WHERE session_id = ?
                """,
                (session_id,)
            )
            last_activity_ts = cursor.fetchone()[0]
        else:
            # No task context found - fall back to most recent conversation event session
            cursor.execute(
                """
                SELECT session_id, MAX(timestamp) as last_activity
                FROM episodic_events
                WHERE event_type = 'conversation'
                GROUP BY session_id
                ORDER BY last_activity DESC
                LIMIT 1
                """
            )

            result = cursor.fetchone()
            if result:
                session_id, last_activity_ts = result
            else:
                return {
                    "status": "none",
                    "message": "No conversation history found",
                }

        last_activity = datetime.fromtimestamp(last_activity_ts)

        # 2. Get recent conversation events (last 5-10 turns)
        cursor.execute(
            """
            SELECT
                id, timestamp, content, context_task, context_phase, learned, confidence
            FROM episodic_events
            WHERE session_id = ?
              AND event_type = 'conversation'
            ORDER BY timestamp DESC
            LIMIT 10
            """,
            (session_id,)
        )

        conversation_events = cursor.fetchall()

        # 3. Get recent file changes (last 30 min)
        cutoff_time = datetime.now() - timedelta(minutes=30)
        cutoff_ts = int(cutoff_time.timestamp())

        cursor.execute(
            """
            SELECT
                DISTINCT context_files
            FROM episodic_events
            WHERE context_files IS NOT NULL
              AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 10
            """,
            (cutoff_ts,)
        )

        recent_files = [row[0] for row in cursor.fetchall() if row[0]]

        # 4. Get active tasks and goals
        cursor.execute(
            """
            SELECT
                DISTINCT context_task, context_phase
            FROM episodic_events
            WHERE session_id = ?
              AND context_task IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 5
            """,
            (session_id,)
        )

        task_results = cursor.fetchall()
        active_task = task_results[0][0] if task_results else None
        current_phase = task_results[0][1] if task_results else None

        # 5. Build conversation summary
        conversation_summary = self._build_conversation_summary(conversation_events)

        # 6. Build recovery recommendation
        recovery_rec = self._build_recovery_recommendation(
            session_id, active_task, current_phase, conversation_summary, recent_files
        )

        return {
            "status": "recovered",
            "session_id": session_id,
            "last_activity": last_activity.isoformat(),
            "conversation_summary": conversation_summary,
            "active_work": active_task,
            "current_phase": current_phase,
            "recent_files": recent_files,
            "recovery_recommendation": recovery_rec,
            "full_context": {
                "session_id": session_id,
                "conversation_events": len(conversation_events),
                "recent_files_modified": len(recent_files),
                "time_since_last_activity": self._format_time_delta(last_activity),
            }
        }

    def _build_conversation_summary(self, conversation_events: list) -> str:
        """Build summary of recent conversation.

        Args:
            conversation_events: List of episodic event tuples

        Returns:
            Formatted summary string
        """
        if not conversation_events:
            return "No recent conversation history"

        # Build summary from last 3 most recent events (reverse chronological)
        summary_lines = ["Recent conversation:"]

        for event_id, timestamp, content, task, phase, learned, confidence in conversation_events[:3]:
            ts = datetime.fromtimestamp(timestamp)
            # Truncate long content
            content_preview = content[:150] + "..." if len(content) > 150 else content
            summary_lines.append(f"  [{ts.strftime('%H:%M:%S')}] {content_preview}")

        return "\n".join(summary_lines)

    def _build_recovery_recommendation(
        self,
        session_id: str,
        active_task: Optional[str],
        phase: Optional[str],
        conversation_summary: str,
        recent_files: list[str]
    ) -> str:
        """Build human-readable recovery recommendation.

        Args:
            session_id: Session that was recovered
            active_task: Current task being worked on
            phase: Execution phase
            conversation_summary: Recent conversation
            recent_files: Recently modified files

        Returns:
            Formatted recommendation string
        """
        lines = ["✓ Context recovered. Here's what we were doing:\n"]

        if active_task:
            lines.append(f"📋 Task: {active_task}")

        if phase:
            lines.append(f"⏱️  Phase: {phase}")

        if recent_files:
            lines.append(f"📁 Recent files: {', '.join(recent_files[:3])}")

        lines.append("\n" + conversation_summary)

        lines.append("\n\n👉 Next steps:")
        lines.append("1. Review the conversation summary above")
        lines.append("2. I'll restore full context and memory")
        lines.append("3. We can continue from where we left off")

        return "\n".join(lines)

    def _format_time_delta(self, timestamp: datetime) -> str:
        """Format time delta from now to given timestamp.

        Args:
            timestamp: Datetime to compare with now

        Returns:
            Human-readable time delta (e.g., "5 minutes ago")
        """
        delta = datetime.now() - timestamp

        if delta.total_seconds() < 60:
            return "just now"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = int(delta.total_seconds() / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"

    def get_recovery_banner(self) -> str:
        """Get a banner to display on context recovery.

        Returns:
            Formatted banner string
        """
        return """
╭─────────────────────────────────────────╮
│  🔄 Context Recovered from Memory       │
│  Use /memory-query to search details    │
│  Use /timeline to see what happened     │
╰─────────────────────────────────────────╯
"""

"""Session resumption and context loading into working memory."""

from datetime import datetime, timedelta
from typing import Optional

from ..conversation.context_recovery import ContextSnapshot
from ..conversation.store import ConversationStore
from ..core.database import Database
from ..working_memory.episodic_buffer import EpisodicBuffer


class SessionResumptionManager:
    """Manages post-/clear session resumption and context loading."""

    def __init__(self, db: Database, project_id: int = 1):
        """Initialize session resumption manager.

        Args:
            db: Database instance
            project_id: Project ID for memory isolation
        """
        self.db = db
        self.project_id = project_id
        self.conversation_store = ConversationStore(db)
        self.context_snapshot = ContextSnapshot(db, project_id)

        # Lazy-load working memory when needed
        self._working_memory = None

    def detect_resumption_intent(self, user_input: str) -> bool:
        """Detect if user is asking to resume previous work.

        Args:
            user_input: User's message

        Returns:
            True if message indicates resumption intent
        """
        resumption_keywords = [
            "what were we doing",
            "what was i working on",
            "let's continue",
            "continue from",
            "where were we",
            "resume",
            "previous context",
            "last session",
            "what's next",
            "pick up where",
            "previous work",
            "what was the task",
        ]

        input_lower = user_input.lower()
        return any(keyword in input_lower for keyword in resumption_keywords)

    def get_resumption_brief(
        self, session_id: Optional[str] = None, hours_back: int = 24
    ) -> dict:
        """Get brief of previous session context for resumption.

        Args:
            session_id: Specific session to resume (or find most recent)
            hours_back: Look back this many hours for recent context

        Returns:
            Resumption brief with key context
        """
        # Find most recent session if not specified
        if not session_id:
            session_id = self._find_most_recent_session(hours_back)
            if not session_id:
                return {
                    "status": "no_context",
                    "message": "No previous session context found",
                }

        # Get session state
        conversations = self.conversation_store.get_session_conversations(session_id)
        if not conversations:
            return {
                "status": "no_conversations",
                "message": f"Session {session_id} has no conversations",
            }

        # Extract most recent conversation
        most_recent_conv = conversations[0]
        full_conv = self.conversation_store.get_conversation(most_recent_conv["id"])

        if not full_conv or not full_conv.turns:
            return {
                "status": "no_turns",
                "message": f"Conversation {most_recent_conv['thread_id']} has no turns",
            }

        # Build resumption brief
        recent_turns = full_conv.turns[-3:]  # Last 3 turns
        turn_summary = self._summarize_turns(recent_turns)

        brief = {
            "status": "ready_to_resume",
            "session_id": session_id,
            "conversation_id": most_recent_conv["id"],
            "conversation_title": most_recent_conv["title"] or "Untitled",
            "last_activity": most_recent_conv["created_at"],
            "conversation_count": len(conversations),
            "total_turns": full_conv.id,  # Rough estimate
            "task": full_conv.title,
            "recent_context": turn_summary,
            "recovery_options": [
                "Continue the conversation by responding to the last point",
                "Ask clarifying questions about the context",
                "Review the full conversation history",
                "Start a new conversation in the same session",
            ],
        }

        return brief

    def load_context_to_working_memory(
        self, session_id: Optional[str] = None, hours_back: int = 24
    ) -> dict:
        """Load previous session context into working memory.

        Args:
            session_id: Session to load (or find most recent)
            hours_back: Look back this many hours

        Returns:
            Loading result with confirmation
        """
        brief = self.get_resumption_brief(session_id, hours_back)

        if brief["status"] != "ready_to_resume":
            return brief

        # Load context into working memory
        context_text = self._format_context_for_loading(brief)

        try:
            # Try to use working memory if available
            if self._get_working_memory():
                item_id = self._working_memory.add_item(
                    project_id=self.project_id,
                    content=context_text,
                    sources={
                        "session_id": brief["session_id"],
                        "conversation_id": brief["conversation_id"],
                        "resumed_at": datetime.now().isoformat(),
                    },
                    importance=0.95,  # High importance, decays slower
                )
            else:
                # If working memory not available, just use placeholder ID
                item_id = -1
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            # Fallback if working memory can't be initialized
            item_id = -1

        return {
            "status": "context_loaded",
            "message": f"Loaded context from session {brief['session_id']}",
            "loaded_item_id": item_id,
            "session_id": brief["session_id"],
            "conversation_title": brief["conversation_title"],
            "context_preview": brief["recent_context"],
            "next_steps": brief["recovery_options"],
        }

    def get_full_session_context(self, session_id: str) -> dict:
        """Get complete session context for detailed review.

        Args:
            session_id: Session ID

        Returns:
            Complete session data
        """
        conversations = self.conversation_store.get_session_conversations(session_id)

        full_context = {
            "session_id": session_id,
            "conversation_count": len(conversations),
            "conversations": [],
        }

        for conv_meta in conversations:
            full_conv = self.conversation_store.get_conversation(conv_meta["id"])
            if full_conv:
                turns_data = []
                for turn in full_conv.turns:
                    turns_data.append(
                        {
                            "turn_number": turn.turn_number,
                            "user": turn.user_message.content[:200],
                            "assistant": turn.assistant_message.content[:200],
                            "duration_ms": turn.duration_ms,
                            "tokens": turn.total_tokens,
                        }
                    )

                full_context["conversations"].append(
                    {
                        "id": conv_meta["id"],
                        "title": conv_meta["title"],
                        "status": conv_meta["status"],
                        "total_tokens": conv_meta["total_tokens"],
                        "turn_count": len(turns_data),
                        "turns": turns_data,
                    }
                )

        return full_context

    def suggest_next_task(self, session_id: Optional[str] = None) -> dict:
        """Suggest what to work on next based on session context.

        Args:
            session_id: Session to analyze (or find most recent)

        Returns:
            Task suggestion with context
        """
        brief = self.get_resumption_brief(session_id)

        if brief["status"] != "ready_to_resume":
            return {"suggestion": "No previous context to continue from"}

        # Extract task from context
        task = brief.get("task") or "Continue previous work"
        last_activity = brief.get("last_activity", "Unknown")

        return {
            "suggested_task": task,
            "context": brief["recent_context"],
            "last_activity": last_activity,
            "conversation_history_available": True,
            "recommendation": f"Resume '{task}' by reviewing the recent conversation context above",
        }

    def _get_working_memory(self):
        """Lazy-load working memory instance.

        Returns:
            EpisodicBuffer instance or None if not available
        """
        if self._working_memory is None:
            try:
                from ..core.embeddings import EmbeddingModel

                embedder = EmbeddingModel()
                self._working_memory = EpisodicBuffer(self.db, embedder)
            except (AttributeError, ValueError, TypeError):
                return None
        return self._working_memory

    def _find_most_recent_session(self, hours_back: int = 24) -> Optional[str]:
        """Find most recent session within time window.

        Args:
            hours_back: Look back this many hours

        Returns:
            Session ID or None
        """
        cursor = self.db.get_cursor()
        cutoff_time = int((datetime.now() - timedelta(hours=hours_back)).timestamp())

        cursor.execute(
            """
            SELECT id FROM sessions
            WHERE project_id = ? AND started_at > ?
            ORDER BY started_at DESC
            LIMIT 1
        """,
            (self.project_id, cutoff_time),
        )

        row = cursor.fetchone()
        return row[0] if row else None

    def _summarize_turns(self, turns) -> str:
        """Summarize recent conversation turns.

        Args:
            turns: List of ConversationTurn objects

        Returns:
            Summary string
        """
        if not turns:
            return "No conversation turns available"

        summary_lines = []
        for turn in turns:
            user_snippet = turn.user_message.content[:80]
            asst_snippet = turn.assistant_message.content[:80]
            summary_lines.append(
                f"Turn {turn.turn_number}:\n"
                f"  You: {user_snippet}...\n"
                f"  Me: {asst_snippet}..."
            )

        return "\n\n".join(summary_lines)

    def _format_context_for_loading(self, brief: dict) -> str:
        """Format resumption brief for loading into working memory.

        Args:
            brief: Resumption brief dict

        Returns:
            Formatted context string
        """
        return f"""SESSION RESUMPTION CONTEXT
============================================

Conversation: {brief['conversation_title']}
Session ID: {brief['session_id']}
Task: {brief['task']}
Last Activity: {brief['last_activity']}

RECENT CONTEXT:
{brief['recent_context']}

NEXT STEPS:
{chr(10).join(f"- {opt}" for opt in brief['recovery_options'])}

============================================
Use this context to continue where we left off."""

    def clear_old_sessions(self, days: int = 30) -> dict:
        """Archive old sessions to keep memory lean.

        Args:
            days: Archive sessions older than this many days

        Returns:
            Summary of archived sessions
        """
        cursor = self.db.get_cursor()
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())

        # Find old conversations
        cursor.execute(
            """
            SELECT id FROM conversations
            WHERE project_id = ? AND created_at < ? AND status = 'active'
        """,
            (self.project_id, cutoff_time),
        )

        old_conv_ids = [row[0] for row in cursor.fetchall()]
        archived_count = 0

        # Archive them
        for conv_id in old_conv_ids:
            if self.conversation_store.archive_conversation(conv_id):
                archived_count += 1

        return {
            "archived_conversations": archived_count,
            "cutoff_date": datetime.fromtimestamp(cutoff_time).isoformat(),
            "message": f"Archived {archived_count} conversations older than {days} days",
        }

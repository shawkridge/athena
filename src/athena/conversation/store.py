"""Conversation storage and query operations."""

import json
from datetime import datetime
from typing import Any, Optional

from ..core.database import Database
from .models import Conversation, ConversationTurn, Message, MessageRole


class ConversationStore:
    """Manages conversation storage and queries."""

    def __init__(self, db: Database):
        """Initialize conversation store.

        Args:
            db: Database instance
        """
        self.db = db

    # ==================== HELPER METHODS ====================

    def execute(
        self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False
    ) -> Any:
        """Execute SQL query with consistent error handling.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return first row only
            fetch_all: Return all rows as list

        Returns:
            Query result (row, list, or cursor based on parameters)
        """
        cursor = self.db.get_cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor

        except Exception:
            # rollback handled by cursor context
            raise

    def commit(self):
        """Commit database transaction."""
        # commit handled by cursor context

    @staticmethod
    def serialize_json(obj: Any) -> Optional[str]:
        """Safely serialize object to JSON.

        Args:
            obj: Object to serialize

        Returns:
            JSON string or None
        """
        return json.dumps(obj) if obj is not None else None

    @staticmethod
    def deserialize_json(json_str: str, default=None):
        """Safely deserialize JSON string.

        Args:
            json_str: JSON string to deserialize
            default: Default value if deserialization fails

        Returns:
            Deserialized object or default
        """
        if not json_str:
            return default
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def now_timestamp() -> int:
        """Get current Unix timestamp.

        Returns:
            Unix timestamp
        """
        return int(datetime.now().timestamp())

    @staticmethod
    def from_timestamp(ts: Optional[int]) -> Optional[datetime]:
        """Convert timestamp to datetime.

        Args:
            ts: Unix timestamp (or None)

        Returns:
            Datetime object or None
        """
        if ts is None:
            return None
        return datetime.fromtimestamp(ts)

    def _ensure_schema(self):
        """Ensure conversation tables exist."""
        cursor = self.db.get_cursor()

        # Sessions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                started_at INTEGER NOT NULL,
                ended_at INTEGER,
                context TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """
        )

        # Conversations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                thread_id TEXT UNIQUE NOT NULL,
                title TEXT,
                status TEXT DEFAULT 'active',
                created_at INTEGER NOT NULL,
                last_message_at INTEGER NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """
        )

        # Messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens_estimate INTEGER DEFAULT 0,
                model TEXT,
                metadata TEXT,
                created_at INTEGER NOT NULL
            )
        """
        )

        # Conversation turns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,
                user_message_id INTEGER,
                assistant_message_id INTEGER,
                duration_ms INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE SET NULL,
                FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE SET NULL
            )
        """
        )

        # Conversation metadata table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_metadata (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                turn_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                avg_turn_duration_ms REAL DEFAULT 0.0,
                topics TEXT,
                quality_score REAL DEFAULT 0.5,
                is_useful INTEGER DEFAULT 1,
                notes TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """
        )

        # Indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id, started_at DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_id, created_at DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_turns_conversation ON conversation_turns(conversation_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role)")

        # commit handled by cursor context

    def create_session(self, session_id: str, project_id: int) -> str:
        """Create new session.

        Args:
            session_id: Unique session identifier
            project_id: Project ID

        Returns:
            Session ID
        """
        self.execute(
            """
            INSERT OR IGNORE INTO sessions (id, project_id, started_at)
            VALUES (?, ?, ?)
        """,
            (session_id, project_id, self.now_timestamp()),
        )
        self.commit()
        return session_id

    def end_session(self, session_id: str) -> bool:
        """Mark session as ended.

        Args:
            session_id: Session identifier

        Returns:
            True if updated, False if session not found
        """
        cursor = self.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (self.now_timestamp(), session_id),
        )
        self.commit()
        return cursor.rowcount > 0

    def create_conversation(self, conversation: Conversation) -> int:
        """Create new conversation.

        Args:
            conversation: Conversation to create

        Returns:
            Conversation ID
        """
        now = self.now_timestamp()
        cursor = self.execute(
            """
            INSERT INTO conversations
            (project_id, session_id, thread_id, title, status, created_at, last_message_at, total_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                conversation.project_id,
                conversation.session_id,
                conversation.thread_id,
                conversation.title,
                conversation.status,
                now,
                now,
                conversation.total_tokens,
            ),
        )
        conversation_id = cursor.lastrowid
        self.commit()
        return conversation_id

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation with all turns.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation object or None
        """
        # Get conversation
        row = self.execute(
            """
            SELECT id, project_id, session_id, thread_id, title, status,
                   created_at, last_message_at, total_tokens
            FROM conversations
            WHERE id = ?
        """,
            (conversation_id,),
            fetch_one=True,
        )

        if not row:
            return None

        (
            conv_id,
            project_id,
            session_id,
            thread_id,
            title,
            status,
            created_at,
            last_message_at,
            total_tokens,
        ) = row

        # Get turns
        turns = self._get_conversation_turns(conversation_id)

        return Conversation(
            id=conv_id,
            project_id=project_id,
            session_id=session_id,
            thread_id=thread_id,
            title=title,
            status=status,
            turns=turns,
            created_at=self.from_timestamp(created_at),
            last_message_at=self.from_timestamp(last_message_at),
            total_tokens=total_tokens,
        )

    def _get_conversation_turns(self, conversation_id: int) -> list[ConversationTurn]:
        """Get all turns for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of ConversationTurn objects
        """
        rows = self.execute(
            """
            SELECT id, turn_number, user_message_id, assistant_message_id,
                   duration_ms, total_tokens, created_at
            FROM conversation_turns
            WHERE conversation_id = ?
            ORDER BY turn_number
        """,
            (conversation_id,),
            fetch_all=True,
        )

        turns = []
        for row in rows or []:
            (
                turn_id,
                turn_number,
                user_msg_id,
                asst_msg_id,
                duration_ms,
                total_tokens,
                created_at,
            ) = row

            user_msg = self._get_message(user_msg_id) if user_msg_id else None
            asst_msg = self._get_message(asst_msg_id) if asst_msg_id else None

            if user_msg and asst_msg:
                turns.append(
                    ConversationTurn(
                        id=turn_id,
                        turn_number=turn_number,
                        user_message=user_msg,
                        assistant_message=asst_msg,
                        duration_ms=duration_ms,
                        total_tokens=total_tokens,
                        created_at=self.from_timestamp(created_at),
                    )
                )

        return turns

    def _get_message(self, message_id: int) -> Optional[Message]:
        """Get message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message object or None
        """
        row = self.execute(
            """
            SELECT id, role, content, tokens_estimate, model, metadata, created_at
            FROM messages
            WHERE id = ?
        """,
            (message_id,),
            fetch_one=True,
        )

        if not row:
            return None

        msg_id, role, content, tokens, model, metadata_json, created_at = row
        metadata = self.deserialize_json(metadata_json)

        return Message(
            id=msg_id,
            role=MessageRole(role),
            content=content,
            tokens_estimate=tokens,
            model=model,
            metadata=metadata,
            timestamp=self.from_timestamp(created_at),
        )

    def add_turn(
        self,
        conversation_id: int,
        turn_number: int,
        user_message: Message,
        assistant_message: Message,
        duration_ms: int = 0,
    ) -> int:
        """Add turn to conversation.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number (sequential)
            user_message: User message
            assistant_message: Assistant message
            duration_ms: Duration of turn in milliseconds

        Returns:
            Turn ID
        """
        # Store messages (reuse existing method that uses raw cursor)
        cursor = self.db.get_cursor()
        user_msg_id = self._store_message(cursor, user_message)
        asst_msg_id = self._store_message(cursor, assistant_message)

        total_tokens = (user_message.tokens_estimate or 0) + (
            assistant_message.tokens_estimate or 0
        )

        now = self.now_timestamp()

        # Store turn
        cursor.execute(
            """
            INSERT INTO conversation_turns
            (conversation_id, turn_number, user_message_id, assistant_message_id,
             duration_ms, total_tokens, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                conversation_id,
                turn_number,
                user_msg_id,
                asst_msg_id,
                duration_ms,
                total_tokens,
                now,
            ),
        )

        turn_id = cursor.lastrowid

        # Update conversation last_message_at and total_tokens
        cursor.execute(
            """
            UPDATE conversations
            SET last_message_at = ?, total_tokens = total_tokens + ?
            WHERE id = ?
        """,
            (now, total_tokens, conversation_id),
        )

        self.commit()
        return turn_id

    def _store_message(self, cursor, message: Message) -> int:
        """Store message in database.

        Args:
            cursor: Database cursor
            message: Message to store

        Returns:
            Message ID
        """
        metadata_json = self.serialize_json(message.metadata)
        timestamp = int(message.timestamp.timestamp())

        # Handle role as enum or string (Pydantic uses_enum_values = True)
        role_value = message.role.value if hasattr(message.role, "value") else message.role

        cursor.execute(
            """
            INSERT INTO messages
            (role, content, tokens_estimate, model, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                role_value,
                message.content,
                message.tokens_estimate,
                message.model,
                metadata_json,
                timestamp,
            ),
        )

        return cursor.lastrowid

    def search_conversations(self, project_id: int, query: str, limit: int = 20) -> list[dict]:
        """Search conversations by content.

        Args:
            project_id: Project ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching conversations
        """
        # Build keyword search
        keywords = query.lower().split()
        where_conditions = []
        params = [project_id]

        for keyword in keywords:
            if len(keyword) >= 3:
                where_conditions.append("LOWER(c.title) LIKE ? OR LOWER(m.content) LIKE ?")
                params.extend([f"%{keyword}%", f"%{keyword}%"])

        if not where_conditions:
            where_conditions = ["1=1"]

        where_clause = " OR ".join(where_conditions)

        sql = f"""
            SELECT DISTINCT c.id, c.thread_id, c.title, c.created_at, c.status
            FROM conversations c
            LEFT JOIN conversation_turns t ON c.id = t.conversation_id
            LEFT JOIN messages m ON (t.user_message_id = m.id OR t.assistant_message_id = m.id)
            WHERE c.project_id = ? AND ({where_clause})
            ORDER BY c.created_at DESC
            LIMIT ?
        """

        rows = self.execute(sql, params + [limit], fetch_all=True)

        results = []
        for row in rows or []:
            conv_id, thread_id, title, created_at, status = row
            results.append(
                {
                    "id": conv_id,
                    "thread_id": thread_id,
                    "title": title,
                    "created_at": self.from_timestamp(created_at).isoformat(),
                    "status": status,
                }
            )

        return results

    def get_recent_conversations(self, project_id: int, limit: int = 10) -> list[dict]:
        """Get recent conversations.

        Args:
            project_id: Project ID
            limit: Maximum results

        Returns:
            List of recent conversations
        """
        rows = self.execute(
            """
            SELECT id, thread_id, title, created_at, status, total_tokens
            FROM conversations
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (project_id, limit),
            fetch_all=True,
        )

        results = []
        for row in rows or []:
            conv_id, thread_id, title, created_at, status, total_tokens = row
            results.append(
                {
                    "id": conv_id,
                    "thread_id": thread_id,
                    "title": title,
                    "created_at": self.from_timestamp(created_at).isoformat(),
                    "status": status,
                    "total_tokens": total_tokens,
                }
            )

        return results

    def archive_conversation(self, conversation_id: int) -> bool:
        """Archive conversation (soft-delete).

        Args:
            conversation_id: Conversation ID

        Returns:
            True if updated, False if not found
        """
        cursor = self.execute(
            "UPDATE conversations SET status = 'archived' WHERE id = ?",
            (conversation_id,),
        )
        self.commit()
        return cursor.rowcount > 0

    def get_session_conversations(self, session_id: str) -> list[dict]:
        """Get all conversations in a session.

        Args:
            session_id: Session ID

        Returns:
            List of conversations
        """
        rows = self.execute(
            """
            SELECT id, thread_id, title, created_at, status, total_tokens
            FROM conversations
            WHERE session_id = ?
            ORDER BY created_at DESC
        """,
            (session_id,),
            fetch_all=True,
        )

        results = []
        for row in rows or []:
            conv_id, thread_id, title, created_at, status, total_tokens = row
            results.append(
                {
                    "id": conv_id,
                    "thread_id": thread_id,
                    "title": title,
                    "created_at": self.from_timestamp(created_at).isoformat(),
                    "status": status,
                    "total_tokens": total_tokens,
                }
            )

        return results

    def update_conversation_metadata(
        self, conversation_id: int, title: Optional[str] = None
    ) -> bool:
        """Update conversation metadata.

        Args:
            conversation_id: Conversation ID
            title: New title (optional)

        Returns:
            True if updated
        """
        if title:
            cursor = self.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title, conversation_id),
            )
            self.commit()
            return cursor.rowcount > 0
        return False


class SessionResumptionManager:
    """Manages conversation session resumption and recovery."""

    def __init__(self, db: Database):
        """Initialize session resumption manager.

        Args:
            db: Database instance
        """
        self.db = db
        self.store = ConversationStore(db)

    async def resume_session(self, conversation_id: int) -> dict[str, Any]:
        """Resume a previous conversation session.

        Args:
            conversation_id: ID of conversation to resume

        Returns:
            Session info with recovered context and messages
        """
        try:
            # Get conversation
            convo = self.store.get_conversation(conversation_id)
            if not convo:
                return {"status": "not_found", "messages_loaded": 0}

            # Get messages from conversation
            cursor = self.db.get_cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            )
            messages = cursor.fetchall()
            message_count = len(messages) if messages else 0

            # Calculate context recovery info
            return {
                "status": "resumed",
                "messages_loaded": message_count,
                "conversation_title": (
                    convo.get("title", "Untitled")
                    if isinstance(convo, dict)
                    else getattr(convo, "title", "Untitled")
                ),
                "recovery_success": message_count > 0,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "messages_loaded": 0,
                "recovery_success": False,
            }

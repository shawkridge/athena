"""Data models for conversation capture."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Single message in conversation."""

    id: Optional[int] = None
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_estimate: int = 0
    model: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        use_enum_values = True


class ConversationTurn(BaseModel):
    """Single turn in conversation (user message + assistant response)."""

    id: Optional[int] = None
    turn_number: int
    user_message: Message
    assistant_message: Message
    duration_ms: int = 0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    """Complete conversation thread."""

    id: Optional[int] = None
    project_id: int
    session_id: str
    thread_id: str
    title: Optional[str] = None
    turns: list[ConversationTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_message_at: datetime = Field(default_factory=datetime.now)
    total_tokens: int = 0
    status: str = "active"  # active|archived|deleted


class ConversationMetadata(BaseModel):
    """Metadata about conversation quality and metrics."""

    conversation_id: int
    turn_count: int
    total_tokens: int
    avg_turn_duration_ms: float
    topics: list[str] = Field(default_factory=list)
    quality_score: float = 0.5  # 0-1 scale
    is_useful: bool = True
    notes: Optional[str] = None

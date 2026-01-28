"""
SQLAlchemy ORM Models - Based on Database Diagram
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

from app.core.database import Base


# Enums
class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AnalysisType(str, enum.Enum):
    ARGUMENT = "argument"
    RECOMMENDATION = "recommendation"
    GRAMMAR = "grammar"
    EVOLUTION = "evolution"


class ComponentType(str, enum.Enum):
    PREMISE = "premise"
    CONCLUSION = "conclusion"
    OTHER = "other"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    profession = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sessions = relationship("SessionToken", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class SessionToken(Base):
    """Session tokens for authentication"""
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


class Conversation(Base):
    """Conversations with the system"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Usuario obligatorio
    title = Column(String(255), nullable=False, default="Nueva Conversación")  # Título obligatorio con default
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Messages within a conversation"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    analyses = relationship("Analysis", back_populates="message", cascade="all, delete-orphan")


class Analysis(Base):
    """Analysis results for messages"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    spec = Column(Text, nullable=True)  # JSON completo del análisis
    total_premises = Column(Integer, default=0, nullable=False)
    total_conclusions = Column(Integer, default=0, nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = relationship("Message", back_populates="analyses")
    components = relationship("ArgumentComponent", back_populates="analysis", cascade="all, delete-orphan")
    llm_communications = relationship("LLMCommunication", back_populates="analysis", cascade="all, delete-orphan")


class ArgumentComponent(Base):
    """Individual argument components (premises, conclusions)"""
    __tablename__ = "argument_components"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    component_type = Column(Enum(ComponentType), nullable=False)  # premise, conclusion, other
    text = Column(Text, nullable=False)  # El texto del componente
    tokens = Column(Text, nullable=False)  # JSON array de tokens
    start_pos = Column(Integer, nullable=False)  # Posición inicial en el texto original
    end_pos = Column(Integer, nullable=False)  # Posición final en el texto original
    sequence_order = Column(Integer, nullable=False, default=0)  # Orden de aparición
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="components")
    suggestions = relationship("LLMCommunication", back_populates="component", cascade="all, delete-orphan")


class LLMCommunication(Base):
    """LLM communication logs and suggestions"""
    __tablename__ = "llm_communications"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(Integer, ForeignKey("argument_components.id", ondelete="CASCADE"), nullable=True)
    suggestion_text = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    original_text = Column(Text, nullable=True)
    applied = Column(Boolean, default=False, nullable=False)
    llm_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="llm_communications")
    component = relationship("ArgumentComponent", back_populates="suggestions")

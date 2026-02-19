"""
Pydantic schemas for request/response validation - Based on new database schema
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums
class MessageRoleEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AnalysisTypeEnum(str, Enum):
    ARGUMENT = "argument"
    RECOMMENDATION = "recommendation"
    GRAMMAR = "grammar"
    EVOLUTION = "evolution"


class ComponentTypeEnum(str, Enum):
    PREMISE = "premise"
    CONCLUSION = "conclusion"
    OTHER = "other"


# ==================== USER SCHEMAS ====================
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None


# ==================== SESSION SCHEMAS ====================
class SessionTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True


# ==================== CONVERSATION SCHEMAS ====================
class ConversationBase(BaseModel):
    title: str = Field(default="Nueva Conversación", description="Title of the conversation")


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== MESSAGE SCHEMAS ====================
class MessageBase(BaseModel):
    role: MessageRoleEnum
    content: str


class MessageCreate(MessageBase):
    conversation_id: int


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== ANALYSIS SCHEMAS ====================
class ArgumentComponentBase(BaseModel):
    """Base schema for argument components"""
    component_type: ComponentTypeEnum
    text: str
    tokens: List[str]
    start_pos: int
    end_pos: int
    sequence_order: int = 0


class ArgumentComponentCreate(ArgumentComponentBase):
    analysis_id: int


class ArgumentComponentResponse(ArgumentComponentBase):
    id: int
    analysis_id: int
    created_at: datetime

    @field_validator('tokens', mode='before')
    @classmethod
    def parse_tokens(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True


class AnalysisBase(BaseModel):
    spec: Optional[str] = None  # JSON completo del análisis
    total_premises: int = 0
    total_conclusions: int = 0


class AnalysisCreate(AnalysisBase):
    message_id: int


class AnalysisResponse(AnalysisBase):
    id: int
    message_id: int
    analyzed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ParagraphAnalysisResponse(BaseModel):
    """Response schema for stored paragraph analysis"""
    id: int
    analysis_id: int
    text: str
    strength: str
    premises_count: int
    conclusions_count: int
    word_count: int
    density: float
    strength_score: int
    recommendation: Optional[str] = None
    sequence_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisWithComponents(AnalysisResponse):
    """Analysis with its components and suggestions"""
    components: List[ArgumentComponentResponse] = []
    paragraphs: List[ParagraphAnalysisResponse] = []
    suggestions: List['LLMSuggestionResponse'] = Field(default=[], alias='llm_communications')
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ==================== LLM COMMUNICATION SCHEMAS ====================
class LLMSuggestionBase(BaseModel):
    """Base schema for LLM suggestions"""
    suggestion_text: str
    explanation: str
    original_text: Optional[str] = None
    applied: bool = False
    llm_model: Optional[str] = None


class LLMSuggestionCreate(LLMSuggestionBase):
    analysis_id: int
    component_id: Optional[int] = None
    prompt_id: Optional[int] = None


class LLMSuggestionResponse(LLMSuggestionBase):
    id: int
    analysis_id: int
    component_id: Optional[int] = None
    created_at: datetime
    component_type: Optional[str] = None

    class Config:
        from_attributes = True


class LLMCommunicationBase(BaseModel):
    prompt_id: Optional[int] = None
    suggestion_text: Optional[str] = None
    explanation: Optional[str] = None
    original_text: Optional[str] = None
    applied: bool = False
    llm_model: Optional[str] = None


class LLMCommunicationCreate(LLMCommunicationBase):
    analysis_id: int
    component_id: Optional[int] = None


class LLMCommunicationResponse(LLMCommunicationBase):
    id: int
    analysis_id: int
    component_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== COMBINED SCHEMAS ====================
class ConversationWithMessages(ConversationResponse):
    messages: List[MessageResponse] = []


class MessageWithAnalysis(MessageResponse):
    analyses: List[AnalysisResponse] = []


# ==================== LEGACY COMPATIBILITY (for backward compatibility) ====================
class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to analyze")
    conversation_id: Optional[int] = None


class AnalysisResponseLegacy(BaseModel):
    analysis: str
    message_id: Optional[int] = None
    analysis_id: Optional[int] = None


class RecommendationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to get recommendations for")
    conversation_id: Optional[int] = None


class RecommendationResponse(BaseModel):
    recommendations: str
    message_id: Optional[int] = None
    analysis_id: Optional[int] = None


# ==================== NEW ARGUMENT ANALYSIS SCHEMAS ====================
class ArgumentComponent(BaseModel):
    """Represents a premise or conclusion identified in the text"""
    type: str  # "premise" or "conclusion"
    text: str
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    tokens: Optional[List[str]] = None


class ArgumentSuggestion(BaseModel):
    """Represents a suggestion to improve a premise or conclusion"""
    component_type: str  # "premise" or "conclusion"
    original_text: str
    suggestion: str
    explanation: str
    applied: bool = False


class ParagraphAnalysis(BaseModel):
    """Analysis of a single paragraph"""
    text: str
    strength: str  # "muy fuerte" | "fuerte" | "moderada" | "débil"
    premises_count: int
    conclusions_count: int
    word_count: int
    density: float
    strength_score: int
    recommendation: Optional[str] = None


class CompleteAnalysisResponse(BaseModel):
    """Complete analysis response with components and suggestions"""
    premises: List[ArgumentComponent]
    conclusions: List[ArgumentComponent]
    suggestions: List[ArgumentSuggestion]
    paragraph_analysis: Optional[List[ParagraphAnalysis]] = None
    message_id: Optional[int] = None
    analysis_id: Optional[int] = None
    analyzed_at: Optional[datetime] = None
    total_premises: int
    total_conclusions: int


# Generic response
class MessageResponseGeneric(BaseModel):
    message: str
    success: bool = True

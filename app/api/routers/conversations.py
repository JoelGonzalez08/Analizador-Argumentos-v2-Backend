"""
Conversation management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Conversation, Message, Analysis, ArgumentComponent, LLMCommunication
from app.schemas.schemas import (
    ConversationCreate, 
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessages,
    MessageResponse,
    AnalysisWithComponents,
    ArgumentComponentResponse,
    LLMSuggestionResponse
)
from app.api.routers.users import get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new conversation"""
    new_conversation = Conversation(
        user_id=current_user.id,
        title=conversation.title or "Nueva Conversación",
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all conversations for current user"""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(
        Conversation.updated_at.desc()
    ).offset(skip).limit(limit).all()
    
    return conversations


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a conversation with its messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update conversation (mainly title)"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if conversation_update.title is not None:
        conversation.title = conversation_update.title
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a conversation and all related data (cascade)"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get all messages in this conversation
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).all()
    
    # For each message, delete its analyses and related data
    for message in messages:
        # Get all analyses for this message
        analyses = db.query(Analysis).filter(
            Analysis.message_id == message.id
        ).all()
        
        for analysis in analyses:
            # Delete LLM communications (suggestions) for this analysis
            db.query(LLMCommunication).filter(
                LLMCommunication.analysis_id == analysis.id
            ).delete(synchronize_session=False)
            
            # Delete argument components for this analysis
            db.query(ArgumentComponent).filter(
                ArgumentComponent.analysis_id == analysis.id
            ).delete(synchronize_session=False)
            
            # Delete the analysis itself
            db.delete(analysis)
        
        # Delete the message
        db.delete(message)
    
    # Finally, delete the conversation
    db.delete(conversation)
    db.commit()
    return None


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all messages in a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return messages


@router.get("/{conversation_id}/analyses", response_model=List[AnalysisWithComponents])
async def get_conversation_analyses(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all analyses for a conversation with their components and suggestions"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get all analyses from messages in this conversation
    analyses = db.query(Analysis).join(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Analysis.created_at.desc()).all()
    
    # Build response manually to ensure suggestions are included
    result = []
    for analysis in analyses:
        # Enrich suggestions with component_type
        suggestions_data = []
        for suggestion in analysis.llm_communications:
            suggestion_dict = {
                'id': suggestion.id,
                'analysis_id': suggestion.analysis_id,
                'component_id': suggestion.component_id,
                'suggestion_text': suggestion.suggestion_text,
                'explanation': suggestion.explanation,
                'original_text': suggestion.original_text,
                'applied': suggestion.applied,
                'llm_model': suggestion.llm_model,
                'created_at': suggestion.created_at,
                'component_type': None
            }
            
            if suggestion.component_id:
                component = db.query(ArgumentComponent).filter(
                    ArgumentComponent.id == suggestion.component_id
                ).first()
                if component:
                    suggestion_dict['component_type'] = component.component_type.value.lower()
            
            suggestions_data.append(suggestion_dict)
        
        analysis_dict = {
            'id': analysis.id,
            'message_id': analysis.message_id,
            'spec': analysis.spec,
            'total_premises': analysis.total_premises,
            'total_conclusions': analysis.total_conclusions,
            'analyzed_at': analysis.analyzed_at,
            'created_at': analysis.created_at,
            'components': analysis.components,
            'suggestions': suggestions_data
        }
        result.append(analysis_dict)
    
    return result

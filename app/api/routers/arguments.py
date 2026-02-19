"""
Arguments router - endpoints for argument analysis (Updated for new schema)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import traceback
from openai import OpenAI
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.models import (
    Message, Analysis, Conversation, MessageRole,
    ArgumentComponent as ArgumentComponentDB,
    ComponentType,
    LLMCommunication
)
from app.api.routers.users import get_current_user
from app.schemas.schemas import (
    AnalysisRequest,
    AnalysisResponseLegacy,
    RecommendationRequest,
    RecommendationResponse,
    ConversationResponse,
    MessageResponse,
    CompleteAnalysisResponse,
    ArgumentComponent,
    ArgumentSuggestion,
    ParagraphAnalysis,
    AnalysisWithComponents,
)
from app.services.argument_service import argument_service
from app.services.paragraph_service import analyze_paragraphs
from app.services.llm_service import LLMService
from app.repositories.analysis_repository import AnalysisRepository

# Load environment variables
load_dotenv()

# Initialize services
API_KEY = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
llm_service = LLMService(api_key=API_KEY)

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponseLegacy)
async def analyze_argument(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze argumentative text to identify premises and conclusions using CRF model.
    Requires authentication. Creates a conversation, message, and analysis.
    """
    try:
        # Initialize repository
        repo = AnalysisRepository(db)
        
        texto = request.text.strip()
        if not texto:
            raise HTTPException(400, "El campo 'text' no puede estar vacío.")

        # Extract components using service
        premises_list, conclusions_list = argument_service.extract_simple_components(texto)
        
        # Format analysis result
        analysis_result = "Análisis del texto:\n\n"
        if premises_list:
            analysis_result += "Premisas identificadas:\n"
            for i, p in enumerate(premises_list, 1):
                analysis_result += f"{i}. {p}\n"
        else:
            analysis_result += "No se identificaron premisas claras.\n"
        
        analysis_result += "\n"
        if conclusions_list:
            analysis_result += "Conclusiones identificadas:\n"
            for i, c in enumerate(conclusions_list, 1):
                analysis_result += f"{i}. {c}\n"
        else:
            analysis_result += "No se identificaron conclusiones claras.\n"
        
        # Create or get conversation
        if request.conversation_id:
            conversation = repo.get_conversation(request.conversation_id, current_user.id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = repo.create_conversation(
                user_id=current_user.id,
                title=f"Análisis: {texto[:30]}..."
            )
        
        # Create message and analysis
        message = repo.create_message(conversation.id, texto)
        analysis = repo.create_simple_analysis(message.id, analysis_result)
        
        repo.commit()
        repo.refresh(analysis)
        
        return AnalysisResponseLegacy(
            analysis=analysis_result,
            message_id=message.id,
            analysis_id=analysis.id
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in analyze_argument: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing text: {str(e)}"
        )


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate recommendations to improve argumentative text using OpenAI.
    Requires authentication. First analyzes with CRF, then generates recommendations.
    """
    try:
        # Initialize repository
        repo = AnalysisRepository(db)
        
        texto = request.text.strip()
        if not texto:
            raise HTTPException(400, "El campo 'text' no puede estar vacío.")
        
        # Extract components using service
        premises, conclusions = argument_service.extract_simple_components(texto)
        
        # Generate recommendations using LLM service
        recommendations_text = llm_service.generate_general_recommendations(premises, conclusions)
        
        # Create or get conversation
        if request.conversation_id:
            conversation = repo.get_conversation(request.conversation_id, current_user.id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = repo.create_conversation(
                user_id=current_user.id,
                title=f"Recomendaciones: {texto[:30]}..."
            )
        
        # Create message and analysis
        message = repo.create_message(conversation.id, texto)
        analysis = repo.create_simple_analysis(message.id, recommendations_text)
        
        repo.commit()
        repo.refresh(analysis)
        
        return RecommendationResponse(
            recommendations=recommendations_text,
            message_id=message.id,
            analysis_id=analysis.id
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in get_recommendations: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.get("/history", response_model=List[ConversationResponse])
async def get_conversations_history(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get list of conversations (replaces old arguments history)"""
    conversations = db.query(Conversation).order_by(
        Conversation.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return conversations


@router.get("/conversation/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Get all messages in a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
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


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}


@router.post("/complete-analysis", response_model=CompleteAnalysisResponse)
async def complete_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Complete argument analysis: CRF extraction + OpenAI suggestions + Paragraph analysis.
    Returns structured premises, conclusions, suggestions, and paragraph analysis.
    """
    try:
        from datetime import datetime
        
        # Initialize repository
        repo = AnalysisRepository(db)
        
        texto = request.text.strip()
        if not texto:
            raise HTTPException(400, "El campo 'text' no puede estar vacío.")

        # Step 1: Extract premises and conclusions using service
        premises, conclusions = argument_service.extract_components(texto)
        
        # Step 2: Generate suggestions using LLM service
        suggestions = llm_service.generate_suggestions_for_components(premises, conclusions)
        
        # Step 3: Analyze text by paragraphs using service
        paragraph_analysis = analyze_paragraphs(texto, premises, conclusions)
        
        # Step 4: Save to database
        if request.conversation_id:
            conversation = repo.get_conversation(request.conversation_id, current_user.id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = repo.create_conversation(
                user_id=current_user.id,
                title=f"Análisis: {texto[:30]}..."
            )
        
        # Create message and analysis
        message = repo.create_message(conversation.id, texto)
        analysis = repo.create_analysis(
            message_id=message.id,
            premises=premises,
            conclusions=conclusions,
            suggestions=suggestions,
            paragraph_analysis=paragraph_analysis
        )
        
        # Save components and suggestions
        repo.save_components(analysis.id, premises, conclusions)
        if suggestions:
            repo.save_suggestions(analysis.id, suggestions)
        if paragraph_analysis:
            repo.save_paragraph_analysis(analysis.id, paragraph_analysis)
        
        repo.commit()
        repo.refresh(analysis)
        
        return CompleteAnalysisResponse(
            premises=premises,
            conclusions=conclusions,
            suggestions=suggestions,
            paragraph_analysis=paragraph_analysis,
            message_id=message.id,
            analysis_id=analysis.id,
            analyzed_at=datetime.utcnow(),
            total_premises=len(premises),
            total_conclusions=len(conclusions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in complete_analysis: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing text: {str(e)}"
        )


@router.post("/analyze-paragraphs", response_model=CompleteAnalysisResponse)
async def analyze_text_by_paragraphs(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Specialized endpoint for paragraph-level analysis.
    Analyzes text by paragraphs and classifies each based on argumentative components.
    Includes strength scoring, density metrics, and recommendations.
    """
    try:
        from datetime import datetime
        
        # Initialize repository
        repo = AnalysisRepository(db)
        
        texto = request.text.strip()
        if not texto:
            raise HTTPException(400, "El campo 'text' no puede estar vacío.")

        # Step 1: Extract premises and conclusions using service
        premises, conclusions = argument_service.extract_components(texto)
        
        # Step 2: Analyze text by paragraphs using service
        paragraph_analysis = analyze_paragraphs(texto, premises, conclusions)
        
        # Step 3: Save to database
        if request.conversation_id:
            conversation = repo.get_conversation(request.conversation_id, current_user.id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = repo.create_conversation(
                user_id=current_user.id,
                title=f"Análisis por párrafos: {texto[:30]}..."
            )
        
        # Create message and analysis
        message = repo.create_message(conversation.id, texto)
        analysis = repo.create_analysis(
            message_id=message.id,
            premises=premises,
            conclusions=conclusions,
            paragraph_analysis=paragraph_analysis
        )
        
        # Save components
        repo.save_components(analysis.id, premises, conclusions)
        if paragraph_analysis:
            repo.save_paragraph_analysis(analysis.id, paragraph_analysis)
        
        repo.commit()
        repo.refresh(analysis)
        
        return CompleteAnalysisResponse(
            premises=premises,
            conclusions=conclusions,
            suggestions=[],  # No suggestions in this endpoint
            paragraph_analysis=paragraph_analysis,
            message_id=message.id,
            analysis_id=analysis.id,
            analyzed_at=datetime.utcnow(),
            total_premises=len(premises),
            total_conclusions=len(conclusions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in analyze_text_by_paragraphs: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing text by paragraphs: {str(e)}"
        )


@router.get("/analysis/{analysis_id}", response_model=AnalysisWithComponents)
async def get_analysis_by_id(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Retrieve a complete analysis by ID including components, paragraphs, and suggestions.
    This allows restoring the analysis data with all paragraph-level metrics.
    """
    try:
        # Query analysis with all relationships
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Verify user has access to this analysis
        message = db.query(Message).filter(Message.id == analysis.message_id).first()
        if message:
            conversation = db.query(Conversation).filter(
                Conversation.id == message.conversation_id
            ).first()
            if conversation and conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this analysis"
                )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving analysis: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis: {str(e)}"
        )


@router.get("/message/{message_id}/analysis", response_model=AnalysisWithComponents)
async def get_analysis_by_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Retrieve the most recent analysis for a message including all components and paragraphs.
    Useful for restoring analysis data when viewing message history.
    """
    try:
        # Get message
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Verify user has access
        conversation = db.query(Conversation).filter(
            Conversation.id == message.conversation_id
        ).first()
        if conversation and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this message"
            )
        
        # Get most recent analysis for this message
        analysis = db.query(Analysis).filter(
            Analysis.message_id == message_id
        ).order_by(Analysis.created_at.desc()).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis found for this message"
            )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving analysis: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis: {str(e)}"
        )

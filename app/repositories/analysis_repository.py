"""
Analysis Repository - Data access layer for Analysis and related entities
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.models import (
    Analysis, 
    ArgumentComponent as ArgumentComponentDB,
    ComponentType,
    ParagraphAnalysisDB,
    LLMCommunication,
    Message,
    Conversation,
    MessageRole
)
from app.schemas.schemas import (
    ArgumentComponent,
    ArgumentSuggestion,
    ParagraphAnalysis
)


class AnalysisRepository:
    """Repository for managing Analysis data access"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(self, user_id: int, title: str) -> Conversation:
        """
        Create a new conversation
        
        Args:
            user_id: ID of the user
            title: Conversation title
            
        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            user_id=user_id,
            title=title
        )
        self.db.add(conversation)
        self.db.flush()
        return conversation
    
    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """
        Get conversation by ID and user
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            
        Returns:
            Conversation or None
        """
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
    
    def create_message(self, conversation_id: int, content: str, role: MessageRole = MessageRole.USER) -> Message:
        """
        Create a new message
        
        Args:
            conversation_id: Conversation ID
            content: Message content
            role: Message role (default USER)
            
        Returns:
            Created Message object
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.db.add(message)
        self.db.flush()
        return message
    
    def create_analysis(
        self,
        message_id: int,
        premises: List[ArgumentComponent],
        conclusions: List[ArgumentComponent],
        suggestions: Optional[List[ArgumentSuggestion]] = None,
        paragraph_analysis: Optional[List[ParagraphAnalysis]] = None
    ) -> Analysis:
        """
        Create a new analysis with components
        
        Args:
            message_id: Message ID
            premises: List of premises
            conclusions: List of conclusions
            suggestions: Optional list of suggestions
            paragraph_analysis: Optional paragraph analysis
            
        Returns:
            Created Analysis object
        """
        # Prepare analysis data
        analysis_data = {
            "premises": [p.dict() for p in premises],
            "conclusions": [c.dict() for c in conclusions],
        }
        
        if suggestions:
            analysis_data["suggestions"] = [s.dict() for s in suggestions]
        
        if paragraph_analysis:
            analysis_data["paragraph_analysis"] = [pa.dict() for pa in paragraph_analysis]
        
        # Create analysis
        analysis = Analysis(
            message_id=message_id,
            spec=json.dumps(analysis_data),
            total_premises=len(premises),
            total_conclusions=len(conclusions),
        )
        self.db.add(analysis)
        self.db.flush()
        
        return analysis
    
    def save_components(self, analysis_id: int, premises: List[ArgumentComponent], conclusions: List[ArgumentComponent]):
        """
        Save argument components to database
        
        Args:
            analysis_id: Analysis ID
            premises: List of premises
            conclusions: List of conclusions
        """
        # Save premises
        for idx, premise in enumerate(premises):
            component = ArgumentComponentDB(
                analysis_id=analysis_id,
                component_type=ComponentType.PREMISE,
                text=premise.text,
                tokens=json.dumps(premise.tokens),
                start_pos=premise.start_pos,
                end_pos=premise.end_pos,
                sequence_order=idx
            )
            self.db.add(component)
        
        # Save conclusions
        for idx, conclusion in enumerate(conclusions):
            component = ArgumentComponentDB(
                analysis_id=analysis_id,
                component_type=ComponentType.CONCLUSION,
                text=conclusion.text,
                tokens=json.dumps(conclusion.tokens),
                start_pos=conclusion.start_pos,
                end_pos=conclusion.end_pos,
                sequence_order=idx
            )
            self.db.add(component)
        
        self.db.flush()
    
    def save_paragraph_analysis(self, analysis_id: int, paragraphs: List[ParagraphAnalysis]):
        """
        Save paragraph analysis to database
        
        Args:
            analysis_id: Analysis ID
            paragraphs: List of paragraph analyses
        """
        for idx, paragraph in enumerate(paragraphs):
            para_db = ParagraphAnalysisDB(
                analysis_id=analysis_id,
                text=paragraph.text,
                strength=paragraph.strength,
                premises_count=paragraph.premises_count,
                conclusions_count=paragraph.conclusions_count,
                word_count=paragraph.word_count,
                density=paragraph.density,
                strength_score=paragraph.strength_score,
                recommendation=paragraph.recommendation,
                sequence_order=idx
            )
            self.db.add(para_db)
        
        self.db.flush()
    
    def save_suggestions(self, analysis_id: int, suggestions: List[ArgumentSuggestion]):
        """
        Save LLM suggestions to database
        
        Args:
            analysis_id: Analysis ID
            suggestions: List of suggestions
        """
        for suggestion in suggestions:
            # Find matching component
            component = self.db.query(ArgumentComponentDB).filter(
                ArgumentComponentDB.analysis_id == analysis_id,
                ArgumentComponentDB.text == suggestion.original_text
            ).first()
            
            llm_comm = LLMCommunication(
                analysis_id=analysis_id,
                component_id=component.id if component else None,
                suggestion_text=suggestion.suggestion,
                explanation=suggestion.explanation,
                original_text=suggestion.original_text,
                applied=False,
                llm_model="gpt-3.5-turbo"
            )
            self.db.add(llm_comm)
        
        self.db.flush()
    
    def create_simple_analysis(self, message_id: int, analysis_text: str) -> Analysis:
        """
        Create a simple text-based analysis (for legacy endpoints)
        
        Args:
            message_id: Message ID
            analysis_text: Analysis text
            
        Returns:
            Created Analysis object
        """
        analysis = Analysis(
            message_id=message_id,
            spec=analysis_text,
        )
        self.db.add(analysis)
        self.db.flush()
        return analysis
    
    def commit(self):
        """Commit transaction"""
        self.db.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self.db.rollback()
    
    def refresh(self, instance):
        """Refresh instance from database"""
        self.db.refresh(instance)

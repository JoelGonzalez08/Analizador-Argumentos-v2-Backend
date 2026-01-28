"""
Arguments router - endpoints for argument analysis (Updated for new schema)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
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
)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
API_KEY = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
openai_client = None
if API_KEY:
    openai_client = OpenAI(api_key=API_KEY)

# Initialize CRF model and Stanza (lazy loading to avoid startup errors if dependencies are missing)
crf_model = None
nlp_stanza = None

def init_crf_model():
    """Initialize CRF model and Stanza NLP pipeline"""
    global crf_model, nlp_stanza
    if crf_model is None:
        try:
            import joblib
            import stanza
            import os
            
            # Determine the correct path for the CRF model
            # Try multiple possible locations
            possible_paths = [
                "crf_model_fold_3_7.pkl",  # If running from backend/
                "backend/crf_model_fold_3_7.pkl",  # If running from project root
                os.path.join(os.path.dirname(__file__), "..", "crf_model_fold_3_7.pkl")  # Relative to this file
            ]
            
            model_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if not model_path:
                raise FileNotFoundError(f"CRF model not found. Tried paths: {possible_paths}")
            
            # Load CRF model
            crf_model = joblib.load(model_path)
            print(f"✓ CRF model loaded successfully from: {model_path}")
            
            # Initialize Stanza
            try:
                nlp_stanza = stanza.Pipeline('es', download_method=None)
            except:
                print("Downloading Stanza Spanish model...")
                stanza.download('es', processors='tokenize,pos,lemma')
                nlp_stanza = stanza.Pipeline('es')
                
        except Exception as e:
            print(f"Warning: Could not initialize CRF model: {e}")
            print("CRF-based analysis will not be available")

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
        # Initialize CRF model if not already done
        init_crf_model()
        
        # If CRF model is available, use it
        if crf_model is not None and nlp_stanza is not None:
            texto = request.text.strip()
            if not texto:
                raise HTTPException(400, "El campo 'text' no puede estar vacío.")

            # Tokenization with Stanza
            doc = nlp_stanza(texto)
            tokens = [(w.text, w.upos, None) for s in doc.sentences for w in s.words]

            # Features + prediction
            import features
            feats = features.sent2features(tokens, ventana=3, incluir_sentimiento=True, lemma=True)
            labels = crf_model.predict_single(feats)
            
            # Extract premises and conclusions
            premises = []
            conclusions = []
            current_premise = []
            current_conclusion = []
            
            for (tok, pos, _), lab in zip(tokens, labels):
                if lab.startswith('B-Premise') or lab.startswith('I-Premise'):
                    current_premise.append(tok)
                elif current_premise:
                    premises.append(' '.join(current_premise))
                    current_premise = []
                
                if lab.startswith('B-Claim') or lab.startswith('I-Claim'):
                    current_conclusion.append(tok)
                elif current_conclusion:
                    conclusions.append(' '.join(current_conclusion))
                    current_conclusion = []
            
            # Add remaining
            if current_premise:
                premises.append(' '.join(current_premise))
            if current_conclusion:
                conclusions.append(' '.join(current_conclusion))
            
            # Format analysis result
            analysis_result = "Análisis del texto:\n\n"
            if premises:
                analysis_result += "Premisas identificadas:\n"
                for i, p in enumerate(premises, 1):
                    analysis_result += f"{i}. {p}\n"
            else:
                analysis_result += "No se identificaron premisas claras.\n"
            
            analysis_result += "\n"
            if conclusions:
                analysis_result += "Conclusiones identificadas:\n"
                for i, c in enumerate(conclusions, 1):
                    analysis_result += f"{i}. {c}\n"
            else:
                analysis_result += "No se identificaron conclusiones claras.\n"
        else:
            # Fallback analysis
            analysis_result = f"Análisis del texto:\n\nPremisas identificadas:\n- [Premisa 1]\n- [Premisa 2]\n\nConclusión:\n- [Conclusión principal]\n\nTexto original: {request.text[:100]}..."
        
        # Create or get conversation
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation for authenticated user
            conversation = Conversation(
                user_id=current_user.id,
                title=f"Análisis: {request.text[:30]}..."
            )
            db.add(conversation)
            db.flush()
        
        # Create message
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.text,
        )
        db.add(message)
        db.flush()
        
        # Create analysis
        analysis = Analysis(
            message_id=message.id,
            spec=analysis_result,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
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
        # Initialize CRF model if not already done
        init_crf_model()
        
        premises = []
        conclusions = []
        
        # If CRF model is available, extract premises and conclusions
        if crf_model is not None and nlp_stanza is not None:
            texto = request.text.strip()
            if texto:
                # Tokenization with Stanza
                doc = nlp_stanza(texto)
                tokens = [(w.text, w.upos, None) for s in doc.sentences for w in s.words]

                # Features + prediction
                import features
                feats = features.sent2features(tokens, ventana=3, incluir_sentimiento=True, lemma=True)
                labels = crf_model.predict_single(feats)
                
                # Extract premises and conclusions
                current_premise = []
                current_conclusion = []
                
                for (tok, pos, _), lab in zip(tokens, labels):
                    if lab.startswith('B-Premise') or lab.startswith('I-Premise'):
                        current_premise.append(tok)
                    elif current_premise:
                        premises.append(' '.join(current_premise))
                        current_premise = []
                    
                    if lab.startswith('B-Claim') or lab.startswith('I-Claim'):
                        current_conclusion.append(tok)
                    elif current_conclusion:
                        conclusions.append(' '.join(current_conclusion))
                        current_conclusion = []
                
                # Add remaining
                if current_premise:
                    premises.append(' '.join(current_premise))
                if current_conclusion:
                    conclusions.append(' '.join(current_conclusion))
        
        # Generate recommendations with OpenAI
        if openai_client and (premises or conclusions):
            prompt = (
                "Eres un asistente experto en argumentación académica.\n\n"
                "A continuación verás una lista de premisas y conclusiones extraídas de un texto.\n"
                "Para cada elemento, genera **exactamente una** sugerencia clara y práctica que ayude a mejorar esa premisa o conclusión.\n"
                "Las sugerencias deben ser específicas y directamente aplicables.\n"
                "Además, haz un solo párrafo por sugerencia (uno para cada premisa y conclusión) sin agregar titulos ni numeraciones y menciones previas a las premisas o conclusiones.\n\n"
            )
            
            if premises:
                prompt += "Premisas:\n" + "\n".join(f"- {p}" for p in premises) + "\n\n"
            
            if conclusions:
                prompt += "Conclusiones:\n" + "\n".join(f"- {c}" for c in conclusions) + "\n\n"
            
            prompt += "Ahora, genera las sugerencias solicitadas."

            try:
                resp = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "developer", "content": "Eres un experto en argumentación académica. Responde de forma clara y concisa."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=400,
                    temperature=0.7,
                )
                recommendations_text = resp.choices[0].message.content.strip()
            except Exception as e:
                traceback.print_exc()
                print("OPENAI ERROR ARGS:", e.args)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Error al invocar a OpenAI: {str(e)}"
                )
        else:
            # Fallback recommendations
            recommendations_text = f"Recomendaciones para mejorar tu argumento:\n\n1. Fortalece las premisas con más evidencia\n2. Clarifica la conexión lógica\n3. Considera contrargumentos\n\nTexto analizado: {request.text[:100]}..."
        
        # Create or get conversation
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = Conversation(
                user_id=current_user.id,
                title=f"Recomendaciones: {request.text[:30]}..."
            )
            db.add(conversation)
            db.flush()
        
        # Create message
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.text,
        )
        db.add(message)
        db.flush()
        
        # Create analysis
        analysis = Analysis(
            message_id=message.id,
            spec=recommendations_text,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
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
    Complete argument analysis: CRF extraction + OpenAI suggestions.
    Returns structured premises, conclusions, and specific suggestions for each.
    """
    try:
        from datetime import datetime
        
        # Initialize CRF model if not already done
        init_crf_model()
        
        texto = request.text.strip()
        if not texto:
            raise HTTPException(400, "El campo 'text' no puede estar vacío.")

        premises = []
        conclusions = []
        
        # Step 1: Extract premises and conclusions with CRF
        if crf_model is not None and nlp_stanza is not None:
            # Tokenization with Stanza
            doc = nlp_stanza(texto)
            tokens = [(w.text, w.upos, None) for s in doc.sentences for w in s.words]

            # Features + prediction
            import features
            feats = features.sent2features(tokens, ventana=3, incluir_sentimiento=True, lemma=True)
            labels = crf_model.predict_single(feats)
            
            # Debug: Print unique labels to see what the model is producing
            unique_labels = set(labels)
            print(f"DEBUG - Unique labels produced by CRF: {unique_labels}")
            print(f"DEBUG - First 10 tokens with labels: {list(zip([t[0] for t in tokens[:10]], labels[:10]))}")
            
            # Extract premises and conclusions with positions
            # Model uses: B-P, I-P (Premise), B-C, I-C (Conclusion), O (Outside)
            current_premise_tokens = []
            current_conclusion_tokens = []
            char_position = 0
            
            for (tok, pos, _), lab in zip(tokens, labels):
                # Find token position in original text
                token_start = texto.find(tok, char_position)
                if token_start == -1:
                    token_start = char_position
                token_end = token_start + len(tok)
                char_position = token_end
                
                # Check for premise labels (B-P or I-P)
                if lab in ['B-P', 'I-P']:
                    current_premise_tokens.append((tok, token_start, token_end))
                else:
                    # End of premise sequence
                    if current_premise_tokens:
                        tokens_list = [t[0] for t in current_premise_tokens]
                        start_pos = current_premise_tokens[0][1]
                        end_pos = current_premise_tokens[-1][2]
                        premises.append(ArgumentComponent(
                            type="premise",
                            text=" ".join(tokens_list),
                            start_pos=start_pos,
                            end_pos=end_pos,
                            tokens=tokens_list
                        ))
                        current_premise_tokens = []
                
                # Check for conclusion labels (B-C or I-C)
                if lab in ['B-C', 'I-C']:
                    current_conclusion_tokens.append((tok, token_start, token_end))
                else:
                    # End of conclusion sequence
                    if current_conclusion_tokens:
                        tokens_list = [t[0] for t in current_conclusion_tokens]
                        start_pos = current_conclusion_tokens[0][1]
                        end_pos = current_conclusion_tokens[-1][2]
                        conclusions.append(ArgumentComponent(
                            type="conclusion",
                            text=" ".join(tokens_list),
                            start_pos=start_pos,
                            end_pos=end_pos,
                            tokens=tokens_list
                        ))
                        current_conclusion_tokens = []
            
            # Add remaining sequences
            if current_premise_tokens:
                tokens_list = [t[0] for t in current_premise_tokens]
                start_pos = current_premise_tokens[0][1]
                end_pos = current_premise_tokens[-1][2]
                premises.append(ArgumentComponent(
                    type="premise",
                    text=" ".join(tokens_list),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    tokens=tokens_list
                ))
            if current_conclusion_tokens:
                tokens_list = [t[0] for t in current_conclusion_tokens]
                start_pos = current_conclusion_tokens[0][1]
                end_pos = current_conclusion_tokens[-1][2]
                conclusions.append(ArgumentComponent(
                    type="conclusion",
                    text=" ".join(tokens_list),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    tokens=tokens_list
                ))
            
            print(f"DEBUG - Extracted {len(premises)} premises and {len(conclusions)} conclusions")
            if premises:
                print(f"DEBUG - First premise: {premises[0].text}")
            if conclusions:
                print(f"DEBUG - First conclusion: {conclusions[0].text}")
        
        # Step 2: Generate specific suggestions for each component with OpenAI
        suggestions = []
        
        if openai_client and (premises or conclusions):
            for premise in premises:
                prompt = (
                    f"Eres un experto en argumentación académica. Analiza esta PREMISA:\n\n"
                    f"\"{premise.text}\"\n\n"
                    f"Proporciona UNA sugerencia específica y práctica para mejorarla. "
                    f"Sé conciso y directo (máximo 2 oraciones)."
                )
                
                try:
                    resp = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Eres un experto en argumentación académica. Responde de forma clara y concisa."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.7,
                    )
                    suggestion_text = resp.choices[0].message.content.strip()
                    
                    suggestions.append(ArgumentSuggestion(
                        component_type="premise",
                        original_text=premise.text,
                        suggestion=f"Fortalece esta premisa",
                        explanation=suggestion_text,
                        applied=False
                    ))
                except Exception as e:
                    print(f"Error generating suggestion for premise: {e}")
            
            for conclusion in conclusions:
                prompt = (
                    f"Eres un experto en argumentación académica. Analiza esta CONCLUSIÓN:\n\n"
                    f"\"{conclusion.text}\"\n\n"
                    f"Proporciona UNA sugerencia específica y práctica para mejorarla. "
                    f"Sé conciso y directo (máximo 2 oraciones)."
                )
                
                try:
                    resp = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Eres un experto en argumentación académica. Responde de forma clara y concisa."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.7,
                    )
                    suggestion_text = resp.choices[0].message.content.strip()
                    
                    suggestions.append(ArgumentSuggestion(
                        component_type="conclusion",
                        original_text=conclusion.text,
                        suggestion=f"Mejora esta conclusión",
                        explanation=suggestion_text,
                        applied=False
                    ))
                except Exception as e:
                    print(f"Error generating suggestion for conclusion: {e}")
        
        # Save to database
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = Conversation(
                user_id=current_user.id,
                title=f"Análisis: {texto[:30]}..."
            )
            db.add(conversation)
            db.flush()
        
        # Create message
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=texto,
        )
        db.add(message)
        db.flush()
        
        # Create analysis
        analysis_data = {
            "premises": [p.dict() for p in premises],
            "conclusions": [c.dict() for c in conclusions],
            "suggestions": [s.dict() for s in suggestions]
        }
        
        analysis = Analysis(
            message_id=message.id,
            spec=json.dumps(analysis_data),  # Mantener JSON completo
            total_premises=len(premises),
            total_conclusions=len(conclusions),
        )
        db.add(analysis)
        db.flush()
        
        # Save individual components
        for idx, premise in enumerate(premises):
            component = ArgumentComponentDB(
                analysis_id=analysis.id,
                component_type=ComponentType.PREMISE,
                text=premise.text,
                tokens=json.dumps(premise.tokens),
                start_pos=premise.start_pos,
                end_pos=premise.end_pos,
                sequence_order=idx
            )
            db.add(component)
        
        for idx, conclusion in enumerate(conclusions):
            component = ArgumentComponentDB(
                analysis_id=analysis.id,
                component_type=ComponentType.CONCLUSION,
                text=conclusion.text,
                tokens=json.dumps(conclusion.tokens),
                start_pos=conclusion.start_pos,
                end_pos=conclusion.end_pos,
                sequence_order=idx
            )
            db.add(component)
        
        db.flush()
        
        # Save suggestions in llm_communications table
        for suggestion in suggestions:
            # Find matching component
            component = db.query(ArgumentComponentDB).filter(
                ArgumentComponentDB.analysis_id == analysis.id,
                ArgumentComponentDB.text == suggestion.original_text
            ).first()
            
            llm_comm = LLMCommunication(
                analysis_id=analysis.id,
                component_id=component.id if component else None,
                suggestion_text=suggestion.suggestion,
                explanation=suggestion.explanation,
                original_text=suggestion.original_text,
                applied=False,
                llm_model="gpt-3.5-turbo"
            )
            db.add(llm_comm)
        
        db.commit()
        db.refresh(analysis)
        
        return CompleteAnalysisResponse(
            premises=premises,
            conclusions=conclusions,
            suggestions=suggestions,
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

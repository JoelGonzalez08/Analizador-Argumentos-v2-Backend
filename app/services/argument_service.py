"""
Argument Analysis Service - Business logic for CRF-based argument extraction
"""
from typing import List, Tuple
from app.schemas.schemas import ArgumentComponent
from app.utils import features


class ArgumentAnalysisService:
    """Service for analyzing argumentative text using CRF model"""
    
    def __init__(self):
        self.crf_model = None
        self.nlp_stanza = None
    
    def initialize_models(self):
        """Initialize CRF model and Stanza NLP pipeline"""
        if self.crf_model is None:
            try:
                import joblib
                import stanza
                import os
                
                # Determine the correct path for the CRF model
                possible_paths = [
                    "crf_model_fold_3_7.pkl",
                    "backend/crf_model_fold_3_7.pkl",
                    os.path.join(os.path.dirname(__file__), "..", "..", "crf_model_fold_3_7.pkl")
                ]
                
                model_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        model_path = path
                        break
                
                if not model_path:
                    raise FileNotFoundError(f"CRF model not found. Tried paths: {possible_paths}")
                
                # Load CRF model
                self.crf_model = joblib.load(model_path)
                print(f"✓ CRF model loaded successfully from: {model_path}")
                
                # Initialize Stanza
                try:
                    self.nlp_stanza = stanza.Pipeline('es', download_method=None)
                except:
                    print("Downloading Stanza Spanish model...")
                    stanza.download('es', processors='tokenize,pos,lemma', gpu=False)
                    self.nlp_stanza = stanza.Pipeline('es')
                    
            except Exception as e:
                print(f"Warning: Could not initialize CRF model: {e}")
                print("CRF-based analysis will not be available")
    
    def extract_components(self, text: str) -> Tuple[List[ArgumentComponent], List[ArgumentComponent]]:
        """
        Extract premises and conclusions from text using CRF model
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (premises, conclusions) as ArgumentComponent lists
        """
        self.initialize_models()
        
        premises = []
        conclusions = []
        
        if self.crf_model is None or self.nlp_stanza is None:
            return premises, conclusions
        
        # Tokenization with Stanza
        doc = self.nlp_stanza(text)
        
        # Extract tokens with their character positions from Stanza
        tokens = []
        token_positions = []
        
        for sentence in doc.sentences:
            # Build mapping from words to character positions using sentence tokens
            word_to_pos = {}
            if hasattr(sentence, 'tokens'):
                for token in sentence.tokens:
                    # Each token has start_char and end_char
                    word_to_pos[token.text] = (token.start_char, token.end_char)
            
            for word in sentence.words:
                tokens.append((word.text, word.upos, None))
                # Try to get position from the mapping
                if word.text in word_to_pos:
                    token_positions.append(word_to_pos[word.text])
                else:
                    # For multi-word tokens or if not found, mark as None
                    token_positions.append((None, None))
        
        # If Stanza didn't provide positions, calculate them manually
        if all(pos == (None, None) for pos in token_positions):
            token_positions = []
            char_position = 0
            for tok, _, _ in tokens:
                token_start = text.find(tok, char_position)
                if token_start == -1:
                    token_start = char_position
                token_end = token_start + len(tok)
                token_positions.append((token_start, token_end))
                char_position = token_end
        else:
            # Fill in None positions with manual calculation
            char_position = 0
            for idx, (tok, _, _) in enumerate(tokens):
                if token_positions[idx] == (None, None):
                    token_start = text.find(tok, char_position)
                    if token_start == -1:
                        token_start = char_position
                    token_end = token_start + len(tok)
                    token_positions[idx] = (token_start, token_end)
                    char_position = token_end
                else:
                    char_position = token_positions[idx][1]
        
        # Features + prediction
        feats = features.sent2features(tokens, ventana=3, incluir_sentimiento=True, lemma=True)
        labels = self.crf_model.predict_single(feats)
        
        # Extract premises and conclusions with positions
        current_premise_tokens = []
        current_conclusion_tokens = []
        
        for idx, ((tok, pos, _), lab) in enumerate(zip(tokens, labels)):
            token_start, token_end = token_positions[idx]
            
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
        
        return premises, conclusions
    
    def extract_simple_components(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Extract simple text lists of premises and conclusions (for legacy endpoints)
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (premises_list, conclusions_list) as string lists
        """
        self.initialize_models()
        
        premises = []
        conclusions = []
        
        if self.crf_model is None or self.nlp_stanza is None:
            return premises, conclusions
        
        # Tokenization with Stanza
        doc = self.nlp_stanza(text)
        tokens = [(w.text, w.upos, None) for s in doc.sentences for w in s.words]
        
        # Features + prediction
        feats = features.sent2features(tokens, ventana=3, incluir_sentimiento=True, lemma=True)
        labels = self.crf_model.predict_single(feats)
        
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
        
        return premises, conclusions


# Singleton instance
argument_service = ArgumentAnalysisService()

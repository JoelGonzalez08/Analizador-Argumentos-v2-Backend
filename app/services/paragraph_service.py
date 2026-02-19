"""
Paragraph Analysis Service - Business logic for paragraph-level analysis
"""
from typing import List, Optional
from app.schemas.schemas import ArgumentComponent, ParagraphAnalysis


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs by double newlines.
    Filters out empty paragraphs and those with less than 10 words.
    
    Args:
        text: Text to split into paragraphs
        
    Returns:
        List of paragraph strings
    """
    paragraphs = text.split('\n\n')
    # Filter out empty or very short paragraphs
    return [p.strip() for p in paragraphs if p.strip() and len(p.strip().split()) >= 10]


def count_words(text: str) -> int:
    """
    Count words in text
    
    Args:
        text: Text to count words in
        
    Returns:
        Number of words
    """
    return len(text.split())


def calculate_paragraph_strength(
    premises_count: int, 
    conclusions_count: int, 
    word_count: int, 
    density: float
) -> tuple[int, str]:
    """
    Calculate strength score and category for a paragraph
    
    Args:
        premises_count: Number of premises in paragraph
        conclusions_count: Number of conclusions in paragraph
        word_count: Total words in paragraph
        density: Argumentative density (components/words)
    
    Returns:
        tuple: (strength_score, strength_category)
    """
    # Base score
    score = (premises_count * 15) + (conclusions_count * 20)
    
    # Bonus for density
    if density > 0.15:
        score += 20
    
    # Bonus for balance (has both premises and conclusions)
    if premises_count > 0 and conclusions_count > 0:
        score += 10
    
    # Penalty for long paragraphs without components
    total_components = premises_count + conclusions_count
    if total_components == 0:
        penalty = (word_count // 50) * 5
        score -= penalty
    
    # Ensure score is within 0-100 range
    score = max(0, min(100, score))
    
    # Categorize strength
    if score >= 70:
        strength = "muy fuerte"
    elif score >= 50:
        strength = "fuerte"
    elif score >= 30:
        strength = "moderada"
    else:
        strength = "débil"
    
    return score, strength


def generate_recommendation(
    premises_count: int, 
    conclusions_count: int, 
    density: float, 
    word_count: int
) -> Optional[str]:
    """
    Generate recommendation based on paragraph characteristics
    
    Args:
        premises_count: Number of premises
        conclusions_count: Number of conclusions
        density: Argumentative density
        word_count: Total words
        
    Returns:
        Recommendation string or None
    """
    if premises_count == 0:
        return "Añade premisas que sustenten tus afirmaciones"
    elif conclusions_count == 0:
        return "Incluye conclusiones que sinteticen las ideas"
    elif density < 0.1:
        return "Considera hacer el párrafo más conciso o añadir más argumentación"
    elif word_count > 150:
        return "Párrafo extenso, considera dividirlo para mayor claridad"
    return None


def analyze_paragraphs(
    text: str, 
    premises: List[ArgumentComponent], 
    conclusions: List[ArgumentComponent]
) -> List[ParagraphAnalysis]:
    """
    Analyze text by paragraphs and classify them based on argumentative components
    
    Args:
        text: Full text to analyze
        premises: List of identified premises with their positions
        conclusions: List of identified conclusions with their positions
    
    Returns:
        List of ParagraphAnalysis objects
    """
    paragraphs = split_into_paragraphs(text)
    paragraph_analyses = []
    
    # Calculate cumulative positions for each paragraph
    paragraph_positions = []
    current_pos = 0
    
    for paragraph_text in paragraphs:
        # Find the position of this paragraph in the original text
        # Search from current position to avoid finding duplicates
        paragraph_start = text.find(paragraph_text, current_pos)
        if paragraph_start == -1:
            # If exact match not found, try without extra spaces
            # This handles cases where formatting might differ
            search_text = ' '.join(paragraph_text.split())
            paragraph_start = text.find(search_text, current_pos)
            if paragraph_start == -1:
                continue
            paragraph_end = paragraph_start + len(search_text)
        else:
            paragraph_end = paragraph_start + len(paragraph_text)
        
        paragraph_positions.append({
            'text': paragraph_text,
            'start': paragraph_start,
            'end': paragraph_end
        })
        current_pos = paragraph_end
    
    for para_info in paragraph_positions:
        paragraph_text = para_info['text']
        paragraph_start = para_info['start']
        paragraph_end = para_info['end']
        
        # Count components in this paragraph
        premises_in_paragraph = 0
        conclusions_in_paragraph = 0
        
        for premise in premises:
            if premise.start_pos is not None and premise.end_pos is not None:
                # Calculate the center point of the component
                component_center = (premise.start_pos + premise.end_pos) / 2
                # Count if the center is within this paragraph
                if paragraph_start <= component_center < paragraph_end:
                    premises_in_paragraph += 1
            else:
                # Fallback: check if premise text is in paragraph
                if premise.text in paragraph_text:
                    premises_in_paragraph += 1
        
        for conclusion in conclusions:
            if conclusion.start_pos is not None and conclusion.end_pos is not None:
                # Calculate the center point of the component
                component_center = (conclusion.start_pos + conclusion.end_pos) / 2
                # Count if the center is within this paragraph
                if paragraph_start <= component_center < paragraph_end:
                    conclusions_in_paragraph += 1
            else:
                # Fallback: check if conclusion text is in paragraph
                if conclusion.text in paragraph_text:
                    conclusions_in_paragraph += 1
        
        # Calculate metrics
        word_count = count_words(paragraph_text)
        total_components = premises_in_paragraph + conclusions_in_paragraph
        density = total_components / word_count if word_count > 0 else 0.0
        
        # Calculate strength
        strength_score, strength = calculate_paragraph_strength(
            premises_in_paragraph, 
            conclusions_in_paragraph, 
            word_count, 
            density
        )
        
        # Generate recommendation
        recommendation = generate_recommendation(
            premises_in_paragraph,
            conclusions_in_paragraph,
            density,
            word_count
        )
        
        # Create paragraph analysis
        paragraph_analysis = ParagraphAnalysis(
            text=paragraph_text,
            strength=strength,
            premises_count=premises_in_paragraph,
            conclusions_count=conclusions_in_paragraph,
            word_count=word_count,
            density=round(density, 3),
            strength_score=strength_score,
            recommendation=recommendation
        )
        
        paragraph_analyses.append(paragraph_analysis)
    
    return paragraph_analyses

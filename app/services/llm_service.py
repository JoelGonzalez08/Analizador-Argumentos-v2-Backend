"""
LLM Service - Business logic for OpenAI interactions
"""
from typing import List, Optional
from openai import OpenAI
from app.schemas.schemas import ArgumentSuggestion, ArgumentComponent


class LLMService:
    """Service for generating suggestions using OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def generate_suggestions_for_components(
        self, 
        premises: List[ArgumentComponent], 
        conclusions: List[ArgumentComponent]
    ) -> List[ArgumentSuggestion]:
        """
        Generate specific suggestions for each premise and conclusion
        
        Args:
            premises: List of identified premises
            conclusions: List of identified conclusions
            
        Returns:
            List of ArgumentSuggestion objects
        """
        if not self.client:
            return []
        
        suggestions = []
        
        # Generate suggestions for premises
        for premise in premises:
            prompt = (
                f"Eres un experto en argumentación académica. Analiza esta PREMISA:\n\n"
                f"\"{premise.text}\"\n\n"
                f"Proporciona UNA sugerencia específica y práctica para mejorarla. "
                f"Sé conciso y directo (máximo 2 oraciones)."
            )
            
            try:
                resp = self.client.chat.completions.create(
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
                    suggestion="Fortalece esta premisa",
                    explanation=suggestion_text,
                    applied=False
                ))
            except Exception as e:
                print(f"Error generating suggestion for premise: {e}")
        
        # Generate suggestions for conclusions
        for conclusion in conclusions:
            prompt = (
                f"Eres un experto en argumentación académica. Analiza esta CONCLUSIÓN:\n\n"
                f"\"{conclusion.text}\"\n\n"
                f"Proporciona UNA sugerencia específica y práctica para mejorarla. "
                f"Sé conciso y directo (máximo 2 oraciones)."
            )
            
            try:
                resp = self.client.chat.completions.create(
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
                    suggestion="Mejora esta conclusión",
                    explanation=suggestion_text,
                    applied=False
                ))
            except Exception as e:
                print(f"Error generating suggestion for conclusion: {e}")
        
        return suggestions
    
    def generate_general_recommendations(
        self, 
        premises: List[str], 
        conclusions: List[str]
    ) -> str:
        """
        Generate general recommendations for improving the argument
        
        Args:
            premises: List of premise texts
            conclusions: List of conclusion texts
            
        Returns:
            Recommendations as text
        """
        if not self.client or (not premises and not conclusions):
            return self._fallback_recommendations()
        
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
            resp = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "developer", "content": "Eres un experto en argumentación académica. Responde de forma clara y concisa."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return self._fallback_recommendations()
    
    def _fallback_recommendations(self) -> str:
        """Fallback recommendations when OpenAI is not available"""
        return (
            "Recomendaciones para mejorar tu argumento:\n\n"
            "1. Fortalece las premisas con más evidencia\n"
            "2. Clarifica la conexión lógica\n"
            "3. Considera contrargumentos"
        )

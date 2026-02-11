"""
AI-Powered Impact Analysis Generator
Generates custom impact explanations for each news article using AI
"""

import os
import json
from typing import Dict, List
import anthropic

# You can also use OpenAI instead - uncomment below
# import openai

class ImpactGenerator:
    """Generate AI-powered impact analysis for news articles"""
    
    def __init__(self):
        """Initialize the AI client"""
        # Using Anthropic Claude API
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Uncomment for OpenAI
        # self.openai_key = os.getenv("OPENAI_API_KEY")
        # openai.api_key = self.openai_key
        
        if self.anthropic_key:
            self.client = anthropic.Anthropic(api_key=self.anthropic_key)
            self.use_ai = True
            print("✅ AI Impact Generator enabled (Anthropic)")
        else:
            self.use_ai = False
            print("⚠️ ANTHROPIC_API_KEY not found - using default impacts")
    
    def generate_fake_news_impact(self, headline: str, description: str = "") -> List[Dict]:
        """Generate specific harmful impacts for fake news"""
        
        if not self.use_ai:
            return self._get_default_fake_impacts()
        
        try:
            prompt = f"""Given this FAKE news article, generate 4 specific harmful impacts on society.

News Headline: {headline}
Description: {description}

For each impact, provide:
1. A short title (3-5 words)
2. A specific description (1 sentence) explaining how THIS PARTICULAR fake news harms people

Format as JSON array:
[
  {{"icon": "🧠", "title": "Short Title", "description": "Specific harmful effect"}},
  {{"icon": "😰", "title": "Short Title", "description": "Specific harmful effect"}},
  {{"icon": "🤝", "title": "Short Title", "description": "Specific harmful effect"}},
  {{"icon": "💔", "title": "Short Title", "description": "Specific harmful effect"}}
]

Use these icons: 🧠 (manipulation), 😰 (fear/panic), 🤝 (social division), 💔 (reputation damage), ⚖️ (democracy), ⚕️ (health risks)"""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text
            
            # Parse JSON
            impacts = json.loads(response_text)
            return impacts
            
        except Exception as e:
            print(f"AI impact generation error: {e}")
            return self._get_default_fake_impacts()
    
    def generate_real_news_impact(self, headline: str, description: str = "") -> List[Dict]:
        """Generate specific positive impacts for real news"""
        
        if not self.use_ai:
            return self._get_default_real_impacts()
        
        try:
            prompt = f"""Given this REAL/VERIFIED news article, generate 4 specific positive impacts on society.

News Headline: {headline}
Description: {description}

For each impact, provide:
1. A short title (3-5 words)
2. A specific description (1 sentence) explaining how THIS PARTICULAR real news benefits people

Format as JSON array:
[
  {{"icon": "📚", "title": "Short Title", "description": "Specific positive benefit"}},
  {{"icon": "🏛️", "title": "Short Title", "description": "Specific positive benefit"}},
  {{"icon": "🤝", "title": "Short Title", "description": "Specific positive benefit"}},
  {{"icon": "💡", "title": "Short Title", "description": "Specific positive benefit"}}
]

Use these icons: 📚 (education), 🏛️ (democracy), 🤝 (unity), 💡 (awareness), 🌍 (global), 🛡️ (safety)"""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text
            
            # Parse JSON
            impacts = json.loads(response_text)
            return impacts
            
        except Exception as e:
            print(f"AI impact generation error: {e}")
            return self._get_default_real_impacts()
    
    def _get_default_fake_impacts(self) -> List[Dict]:
        """Fallback default impacts for fake news"""
        return [
            {
                "icon": "🧠",
                "title": "Manipulates Opinion",
                "description": "This misinformation deliberately misleads people and creates false beliefs."
            },
            {
                "icon": "😰",
                "title": "Spreads Panic",
                "description": "False claims can cause unnecessary fear and anxiety in communities."
            },
            {
                "icon": "🤝",
                "title": "Divides Society",
                "description": "Creates polarization and damages trust between different groups."
            },
            {
                "icon": "💔",
                "title": "Harms Reputations",
                "description": "Can unfairly damage the reputation of individuals or organizations."
            }
        ]
    
    def _get_default_real_impacts(self) -> List[Dict]:
        """Fallback default impacts for real news"""
        return [
            {
                "icon": "📚",
                "title": "Educates Citizens",
                "description": "Accurate information helps people understand important issues."
            },
            {
                "icon": "🏛️",
                "title": "Strengthens Democracy",
                "description": "Truthful journalism enables informed democratic participation."
            },
            {
                "icon": "🤝",
                "title": "Builds Trust",
                "description": "Reliable reporting fosters social cohesion and understanding."
            },
            {
                "icon": "💡",
                "title": "Enables Decisions",
                "description": "Access to facts helps people make better life choices."
            }
        ]


# Alternative: OpenAI Implementation
class ImpactGeneratorOpenAI:
    """Generate AI-powered impact analysis using OpenAI"""
    
    def __init__(self):
        import openai
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
            self.use_ai = True
            print("✅ AI Impact Generator enabled (OpenAI)")
        else:
            self.use_ai = False
            print("⚠️ OPENAI_API_KEY not found")
    
    def generate_fake_news_impact(self, headline: str, description: str = "") -> List[Dict]:
        """Generate impacts using OpenAI"""
        if not self.use_ai:
            return ImpactGenerator()._get_default_fake_impacts()
        
        try:
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing the societal impact of fake news."},
                    {"role": "user", "content": f"Generate 4 specific harmful impacts of this fake news: {headline}. {description}. Return as JSON array with icon, title, description fields."}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            impacts = json.loads(response.choices[0].message.content)
            return impacts
        except Exception as e:
            print(f"OpenAI error: {e}")
            return ImpactGenerator()._get_default_fake_impacts()
    
    def generate_real_news_impact(self, headline: str, description: str = "") -> List[Dict]:
        """Generate impacts using OpenAI"""
        if not self.use_ai:
            return ImpactGenerator()._get_default_real_impacts()
        
        try:
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing the societal benefits of real news."},
                    {"role": "user", "content": f"Generate 4 specific positive impacts of this real news: {headline}. {description}. Return as JSON array with icon, title, description fields."}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            impacts = json.loads(response.choices[0].message.content)
            return impacts
        except Exception as e:
            print(f"OpenAI error: {e}")
            return ImpactGenerator()._get_default_real_impacts()
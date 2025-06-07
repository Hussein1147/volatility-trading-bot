"""
AI Provider abstraction for Claude and Gemini
"""

import os
import json
import re
import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def analyze_trade(self, prompt: str) -> Optional[Dict]:
        """Analyze a trade opportunity and return recommendations"""
        pass

class ClaudeProvider(AIProvider):
    """Claude AI provider using Anthropic API"""
    
    def __init__(self):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
    async def analyze_trade(self, prompt: str) -> Optional[Dict]:
        """Get Claude's analysis for the trade"""
        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Claude Sonnet 4
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            return self._extract_json(content)
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None
            
    def _extract_json(self, content: str) -> Optional[Dict]:
        """Extract JSON from Claude's response"""
        try:
            # Try to find JSON between ```json markers
            json_match = re.search(r'```json\s*\n?(.*?)\n?```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # Extract between first { and last }
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = content[start:end+1]
                else:
                    return None
                    
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None

class GeminiProvider(AIProvider):
    """Gemini AI provider using Google's API"""
    
    def __init__(self):
        import google.generativeai as genai
        
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("No Google/Gemini API key found in environment")
            
        genai.configure(api_key=api_key)
        
        # Try different models in order of preference
        model_preference = [
            'gemini-2.5-pro-preview-06-05',  # Latest 2.5 Pro (paid only)
            'gemini-2.0-flash',               # Latest 2.0 Flash (free tier)
            'gemini-1.5-flash-latest',        # Fallback to 1.5 Flash
        ]
        
        self.model = None
        for model_name in model_preference:
            try:
                self.model = genai.GenerativeModel(model_name)
                # Test the model with a simple prompt
                response = self.model.generate_content("Say 'test'")
                logger.info(f"Using Gemini model: {model_name}")
                break
            except Exception as e:
                logger.debug(f"Model {model_name} not available: {str(e)[:50]}...")
                continue
                
        if not self.model:
            raise ValueError("No available Gemini model found")
        
    async def analyze_trade(self, prompt: str) -> Optional[Dict]:
        """Get Gemini's analysis for the trade"""
        try:
            # Add JSON instruction to prompt
            enhanced_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON without any markdown formatting or extra text."
            
            response = await self.model.generate_content_async(enhanced_prompt)
            content = response.text
            
            # Gemini tends to be cleaner with JSON responses
            return self._extract_json(content)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
            
    def _extract_json(self, content: str) -> Optional[Dict]:
        """Extract JSON from Gemini's response"""
        try:
            # Gemini usually returns clean JSON, but let's be safe
            content = content.strip()
            
            # Remove markdown if present
            if content.startswith('```json'):
                content = re.sub(r'```json\s*\n?', '', content)
                content = re.sub(r'\n?```', '', content)
            elif content.startswith('```'):
                content = re.sub(r'```\s*\n?', '', content)
                content = re.sub(r'\n?```', '', content)
                
            return json.loads(content.strip())
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            # Try extracting between braces as fallback
            try:
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                    return json.loads(json_str)
            except:
                pass
            return None

def create_ai_provider(provider_name: str = None) -> AIProvider:
    """
    Factory function to create AI provider
    
    Args:
        provider_name: 'claude' or 'gemini'. If None, try Claude first, then Gemini
        
    Returns:
        AIProvider instance
    """
    if provider_name is None:
        # Default to Claude Sonnet 4, fall back to Gemini if not available
        if os.getenv('ANTHROPIC_API_KEY'):
            try:
                # Test if Claude Sonnet 4 is available
                claude_provider = ClaudeProvider()
                logger.info("Using Claude Sonnet 4 AI provider (preferred)")
                return claude_provider
            except Exception as e:
                logger.warning(f"Claude not available: {e}")
                # Fall back to Gemini
                if os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'):
                    logger.info("Falling back to Gemini AI provider")
                    return GeminiProvider()
        elif os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'):
            logger.info("Using Gemini AI provider (Claude API key not found)")
            return GeminiProvider()
        else:
            raise ValueError("No AI provider API keys found in environment")
    
    if provider_name.lower() == 'gemini':
        return GeminiProvider()
    elif provider_name.lower() == 'claude':
        return ClaudeProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}")
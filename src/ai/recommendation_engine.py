"""AI-powered recommendation engine"""

import logging
from typing import Dict, Any
from anthropic import AsyncAnthropic

try:
    from ..config import settings
except ImportError:
    from src.config import settings

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generates AI-powered build recommendations"""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        if settings.ANTHROPIC_API_KEY:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            self.client = None

    async def generate_recommendations(
        self,
        character_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> str:
        """Generate AI recommendations based on character analysis"""
        if not self.client:
            return "AI recommendations not available (API key not set)"

        try:
            prompt = f"""Analyze this Path of Exile 2 character and provide specific recommendations:

Character: {character_data.get('name', 'Unknown')}
Class: {character_data.get('class', 'Unknown')}
Level: {character_data.get('level', '?')}

Build Analysis:
- Overall Score: {analysis.get('overall_score', 0):.2f}/1.00
- Tier: {analysis['tier']}
- Strengths: {', '.join(analysis.get('strengths', ['None']))}
- Weaknesses: {', '.join(analysis.get('weaknesses', ['None']))}

Provide 3-5 specific, actionable recommendations to improve this build."""

            response = await self.client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"AI recommendations failed: {e}")
            return f"Could not generate AI recommendations: {str(e)}"

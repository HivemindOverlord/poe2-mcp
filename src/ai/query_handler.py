"""
Natural language query handler
Uses Claude AI to answer build-related questions
"""

import logging
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic

try:
    from ..config import settings
except ImportError:
    from src.config import settings

logger = logging.getLogger(__name__)


class QueryHandler:
    """Handles natural language queries about builds"""

    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("Anthropic API key not set. AI features will be limited.")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def handle_query(
        self,
        query: str,
        character_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Handle a natural language query

        Args:
            query: User's question
            character_context: Optional character data for context

        Returns:
            AI-generated response
        """
        if not self.client:
            return "AI features are not enabled. Please set ANTHROPIC_API_KEY in your .env file."

        try:
            # Build context
            system_prompt = """You are an expert Path of Exile 2 build advisor.
Help players optimize their builds by providing actionable, specific advice.
Focus on practical recommendations that can be implemented immediately."""

            user_message = query

            if character_context:
                user_message += f"\n\nCharacter Context:\n{character_context}"

            # Call Claude
            response = await self.client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=settings.AI_MAX_TOKENS,
                temperature=settings.AI_TEMPERATURE,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"AI query failed: {e}")
            return f"I encountered an error processing your query: {str(e)}"

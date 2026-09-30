import json
from typing import Any

import httpx

from app.core.config import Settings
from app.models.intent import IntentResult


class GroqClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_intent(self, message: str) -> IntentResult:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")

        system_prompt = """
You are an intent extraction engine for a restaurant ordering chatbot.

Return ONLY a valid JSON object.
Do not return markdown, code fences, explanations, or extra text.

JSON format:
{
  "intent": "ADD",
  "items": [
    {
      "name": "chicken biryani",
      "quantity": 5
    }
  ]
}

Allowed intents:
GREETING, THANKS, HELP, ADD, REMOVE, UPDATE, LIST, MENU,
CLEAR_CART, CHECKOUT, CANCEL_ORDER, ORDER_STATUS, UNKNOWN.

Rules:
- Extract the user's requested item names exactly as spoken.
- Trim item name by (s) or s if contains (s) at ending or plural names which ends with s
- Quantity defaults to 1 when not specified.
- For GREETING, THANKS, HELP, LIST, MENU, CLEAR_CART, CHECKOUT,
  CANCEL_ORDER, ORDER_STATUS, and UNKNOWN, items should be [].
- For ADD, REMOVE, and UPDATE, include requested items.
- Never invent menu IDs, prices, stock, or availability.
- Return JSON only.
"""

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "model": self.settings.groq_model,
            "temperature": 1,
            "max_completion_tokens": 2048,
            "top_p": 1,
            "stream": False,
            "reasoning_effort": "medium",
            "stop": None
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.settings.groq_api_key}"
            ),
        }

        url = (
            f"{self.settings.groq_base_url.rstrip('/')}"
            "/chat/completions"
        )

        async with httpx.AsyncClient(
            timeout=self.settings.groq_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            data: dict[str, Any] = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected Groq response: {data}"
            ) from exc

        if not content:
            raise RuntimeError("Groq returned an empty response")

        try:
            parsed = (
                json.loads(content)
                if isinstance(content, str)
                else content
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Groq returned invalid JSON: {content}"
            ) from exc

        return IntentResult.model_validate(parsed)
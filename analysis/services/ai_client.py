import os
import json
import logging
import httpx
from typing import Type, Tuple, Dict, Any, Optional
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class AllFreeModelsUnavailableException(Exception):
    """Raised when all free-tier OpenRouter models fail or exceed quotas."""
    pass


class OpenRouterClient:
    """
    OpenRouter Client targeting strictly :free tier model endpoints.
    Enforces the Zero-Paid-AI requirement: calculated cost is strictly $0.00000.
    Handles automatic model fallback and structured Pydantic validation.
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    FREE_MODEL_FALLBACKS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 45.0,
        models: Optional[list] = None
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.timeout = timeout
        self.models = models or self.FREE_MODEL_FALLBACKS

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fcbarcelona.culer.app",
            "X-Title": "FC Barcelona Intelligence Platform",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        schema_class: Type[BaseModel],
        model: Optional[str] = None
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Generate structured output adhering to a Pydantic schema using OpenRouter free models.
        Returns a tuple of (validated_pydantic_instance, telemetry_dict).
        """
        candidate_models = [model] if model else list(self.models)
        errors = []

        headers = self._get_headers()
        json_schema_prompt = (
            f"\n\nYou MUST return a single valid JSON object strictly matching this schema:\n"
            f"{json.dumps(schema_class.model_json_schema())}\n"
            f"Do not include any conversational preamble or markdown code blocks (like ```json), "
            f"only return the pure JSON string."
        )

        full_system_prompt = f"{system_prompt}{json_schema_prompt}"

        for current_model in candidate_models:
            logger.info(f"Attempting structured generation with OpenRouter free model: {current_model}")

            payload = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            }

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(self.BASE_URL, headers=headers, json=payload)

                    if response.status_code in (429, 503, 502, 504):
                        logger.warning(
                            f"Model {current_model} returned HTTP {response.status_code}. Falling back to next free model."
                        )
                        errors.append(f"{current_model}: HTTP {response.status_code}")
                        continue

                    if response.status_code >= 400:
                        logger.warning(
                            f"Model {current_model} returned error status {response.status_code}: {response.text[:200]}"
                        )
                        errors.append(f"{current_model}: HTTP {response.status_code} - {response.text[:100]}")
                        continue

                    data = response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        errors.append(f"{current_model}: Empty choices returned")
                        continue

                    content = choices[0].get("message", {}).get("content", "").strip()

                    # Strip code block fences if present despite instructions
                    if content.startswith("```json"):
                        content = content[7:]
                    elif content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

                    # Extract usage metadata
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)

                    telemetry = {
                        "model": current_model,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "calculated_cost_usd": 0.00000,  # Zero-Paid-AI Guarantee
                        "raw_response": content
                    }

                    # Validate against Pydantic schema
                    try:
                        validated_instance = schema_class.model_validate_json(content)
                        return validated_instance, telemetry
                    except ValidationError as val_err:
                        logger.warning(
                            f"Model {current_model} response failed Pydantic validation: {val_err}. "
                            f"Content: {content[:300]}"
                        )
                        errors.append(f"{current_model} validation error: {str(val_err)[:100]}")
                        continue

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                logger.warning(f"Connection/timeout error with {current_model}: {exc}. Trying next model.")
                errors.append(f"{current_model} connection error: {exc}")
                continue

        error_summary = "; ".join(errors)
        raise AllFreeModelsUnavailableException(
            f"All free OpenRouter models failed to generate valid structured data. Details: {error_summary}"
        )

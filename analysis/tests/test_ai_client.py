import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from pydantic import BaseModel
from analysis.services.ai_client import OpenRouterClient, AllFreeModelsUnavailableException


class DummySchema(BaseModel):
    title: str
    score: int


class OpenRouterClientTestCase(TestCase):
    def setUp(self):
        self.client = OpenRouterClient(
            api_key="test-key",
            models=["model-1:free", "model-2:free"]
        )

    @patch("httpx.Client.post")
    def test_successful_structured_generation(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"title": "El Clasico Review", "score": 10})
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 45
            }
        }
        mock_post.return_value = mock_response

        instance, telemetry = self.client.generate_structured(
            prompt="Analyze the match",
            system_prompt="You are an expert",
            schema_class=DummySchema
        )

        self.assertIsInstance(instance, DummySchema)
        self.assertEqual(instance.title, "El Clasico Review")
        self.assertEqual(instance.score, 10)
        self.assertEqual(telemetry["prompt_tokens"], 120)
        self.assertEqual(telemetry["completion_tokens"], 45)
        self.assertEqual(telemetry["calculated_cost_usd"], 0.0)

    @patch("httpx.Client.post")
    def test_fallback_on_http_429(self, mock_post):
        """
        Verify that when Model 1 returns HTTP 429 (rate limit),
        the client automatically falls back to Model 2.
        """
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.text = "Rate limit exceeded"

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"title": "Fallback Model Review", "score": 9})
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 80,
                "completion_tokens": 30
            }
        }

        # First call returns 429, second call returns 200
        mock_post.side_effect = [response_429, response_200]

        instance, telemetry = self.client.generate_structured(
            prompt="Analyze the match",
            system_prompt="You are an expert",
            schema_class=DummySchema
        )

        self.assertEqual(instance.title, "Fallback Model Review")
        self.assertEqual(telemetry["model"], "model-2:free")
        self.assertEqual(mock_post.call_count, 2)

    @patch("httpx.Client.post")
    def test_all_models_fail_raises_exception(self, mock_post):
        """Verify AllFreeModelsUnavailableException is raised when all models fail."""
        response_503 = MagicMock()
        response_503.status_code = 503
        mock_post.return_value = response_503

        with self.assertRaises(AllFreeModelsUnavailableException):
            self.client.generate_structured(
                prompt="Analyze the match",
                system_prompt="You are an expert",
                schema_class=DummySchema
            )


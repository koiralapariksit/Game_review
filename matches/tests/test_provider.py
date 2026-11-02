from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
import httpx

from matches.models import ProviderSyncLog
from matches.services.providers.base import RateLimitExceededException, ProviderAPIException
from matches.services.providers.football_data import FootballDataOrgProvider


class FootballDataOrgProviderTests(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        ProviderSyncLog.objects.all().delete()
        self.provider = FootballDataOrgProvider(
            api_key="test_api_key_12345",
            team_id=81,
            raise_on_limit=True,
            cache_key="test_football_data_limit"
        )

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @patch.object(httpx.Client, 'get')
    def test_fetch_team_fixtures_success_and_sync_log(self, mock_get):
        """
        Verify that FootballDataOrgProvider parses a mocked teams/81/matches response
        and correctly creates a ProviderSyncLog telemetry entry.
        """
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 2,
            "filters": {"season": "2026"},
            "matches": [
                {
                    "id": 5001,
                    "utcDate": "2026-08-23T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 81, "name": "FC Barcelona", "shortName": "Barca"},
                    "awayTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
                    "score": {"fullTime": {"home": 3, "away": 1}}
                },
                {
                    "id": 5002,
                    "utcDate": "2026-08-30T19:00:00Z",
                    "status": "SCHEDULED",
                    "homeTeam": {"id": 81, "name": "FC Barcelona", "shortName": "Barca"},
                    "awayTeam": {"id": 90, "name": "Real Betis", "shortName": "Betis"},
                    "score": {"fullTime": {"home": None, "away": None}}
                }
            ]
        }
        mock_get.return_value = mock_response

        matches = self.provider.fetch_team_fixtures(season=2026)

        # Assert returned parsed data
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["id"], 5001)
        self.assertEqual(matches[0]["homeTeam"]["name"], "FC Barcelona")
        self.assertEqual(matches[1]["id"], 5002)

        # Assert correct request parameters passed to httpx
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertIn("https://api.football-data.org/v4/teams/81/matches", args[0])
        self.assertEqual(kwargs.get("params"), {"season": 2026})
        self.assertEqual(kwargs.get("headers", {}).get("X-Auth-Token"), "test_api_key_12345")

        # Assert ProviderSyncLog entry was created
        log = ProviderSyncLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.provider_name, "football-data.org")
        self.assertEqual(log.endpoint, "/teams/81/matches")
        self.assertEqual(log.status_code, 200)
        self.assertTrue(log.success)
        self.assertEqual(log.records_processed, 2)
        self.assertEqual(log.error_message, "")
        self.assertIsNotNone(log.response_time_ms)

    @patch.object(httpx.Client, 'get')
    def test_rate_limiter_blocks_11th_request(self, mock_get):
        """
        Verify that cache-backed rate limiting strictly enforces the 10 requests/minute
        quota by blocking the 11th request with a RateLimitExceededException.
        """
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}
        mock_get.return_value = mock_response

        # Execute 10 allowed requests
        for i in range(10):
            result = self.provider.fetch_team_fixtures()
            self.assertEqual(result, [])

        self.assertEqual(mock_get.call_count, 10)
        self.assertEqual(ProviderSyncLog.objects.count(), 10)

        # 11th request must be blocked by rate limiter
        with self.assertRaises(RateLimitExceededException) as ctx:
            self.provider.fetch_team_fixtures()

        self.assertIn("rate limit exceeded", str(ctx.exception).lower())
        # The mock HTTP client should NOT have been called an 11th time
        self.assertEqual(mock_get.call_count, 10)

    @patch.object(httpx.Client, 'get')
    def test_fetch_squad_and_telemetry(self, mock_get):
        """
        Verify fetch_squad properly parses squad list and logs telemetry.
        """
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 81,
            "name": "FC Barcelona",
            "squad": [
                {"id": 10, "name": "Lamine Yamal", "position": "Offence", "nationality": "Spain"},
                {"id": 8, "name": "Pedri", "position": "Midfield", "nationality": "Spain"},
                {"id": 6, "name": "Gavi", "position": "Midfield", "nationality": "Spain"}
            ]
        }
        mock_get.return_value = mock_response

        squad = self.provider.fetch_squad()
        self.assertEqual(len(squad), 3)
        self.assertEqual(squad[0]["name"], "Lamine Yamal")

        log = ProviderSyncLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.endpoint, "/teams/81")
        self.assertEqual(log.records_processed, 3)
        self.assertTrue(log.success)

    @patch.object(httpx.Client, 'get')
    def test_fetch_match_details_and_telemetry(self, mock_get):
        """
        Verify fetch_match_details fetches and logs single match payload.
        """
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 9999,
            "homeTeam": {"id": 81, "name": "FC Barcelona"},
            "awayTeam": {"id": 86, "name": "Real Madrid"},
            "score": {"fullTime": {"home": 2, "away": 0}}
        }
        mock_get.return_value = mock_response

        details = self.provider.fetch_match_details("9999")
        self.assertEqual(details["id"], 9999)

        log = ProviderSyncLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.endpoint, "/matches/9999")
        self.assertEqual(log.records_processed, 1)
        self.assertTrue(log.success)

    @patch.object(httpx.Client, 'get')
    def test_http_error_logs_failure_and_raises(self, mock_get):
        """
        Verify provider logs failed HTTP status code and raises ProviderAPIException.
        """
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = '{"message": "API rate limit reached on remote server"}'
        mock_get.return_value = mock_response

        with self.assertRaises(ProviderAPIException) as ctx:
            self.provider.fetch_team_fixtures()

        self.assertEqual(ctx.exception.status_code, 429)

        log = ProviderSyncLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status_code, 429)
        self.assertFalse(log.success)
        self.assertEqual(log.records_processed, 0)
        self.assertIn("429", log.error_message)


import os
import time
from datetime import datetime, timezone as dt_timezone
import httpx
from typing import Optional, List, Dict, Any
from django.core.cache import cache
from matches.models import ProviderSyncLog
from .base import FootballDataProvider, RateLimitExceededException, ProviderAPIException


class APIFootballFallbackProvider(FootballDataProvider):
    """
    Fallback client for API-Football (v3.football.api-sports.io).
    Free tier limit: 100 requests per day.
    Enforces a strict daily quota counter in cache: maximum 95 requests/day.
    FC Barcelona team ID in API-Football is 529.
    """

    BASE_URL = "https://v3.football.api-sports.io"
    PROVIDER_NAME = "api-football"
    BARCELONA_TEAM_ID = 529
    DAILY_LIMIT_MAX_REQUESTS = 95
    CACHE_KEY_PREFIX = "api_football_daily_reqs"

    def __init__(
        self,
        api_key: Optional[str] = None,
        team_id: int = BARCELONA_TEAM_ID,
        timeout: float = 15.0,
        raise_on_limit: bool = True,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("API_FOOTBALL_KEY", "").strip()
        self.team_id = team_id
        self.timeout = timeout
        self.raise_on_limit = raise_on_limit

    def _get_daily_cache_key(self) -> str:
        today_str = datetime.now(dt_timezone.utc).strftime("%Y%m%d")
        return f"{self.CACHE_KEY_PREFIX}_{today_str}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "CulerApp/1.0"
        }
        if self.api_key:
            headers["x-apisports-key"] = self.api_key
        return headers

    def _check_rate_limit(self) -> None:
        """
        Check daily request quota using Django cache.
        Enforces maximum 95 requests per day to stay safely under the 100/day free limit.
        """
        cache_key = self._get_daily_cache_key()
        count = cache.get(cache_key, 0)
        if count >= self.DAILY_LIMIT_MAX_REQUESTS:
            msg = (
                f"API-Football daily quota reached: {count}/{self.DAILY_LIMIT_MAX_REQUESTS} "
                f"requests used today. Refusing request to protect free tier limit."
            )
            if self.raise_on_limit:
                raise RateLimitExceededException(msg)
            else:
                raise RateLimitExceededException(msg)

    def _increment_quota(self) -> None:
        cache_key = self._get_daily_cache_key()
        # 86400s (24h) TTL plus buffer
        try:
            cache.add(cache_key, 0, timeout=86400 * 2)
            cache.incr(cache_key)
        except Exception:
            curr = cache.get(cache_key, 0)
            cache.set(cache_key, curr + 1, timeout=86400 * 2)

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute request with rate limit checks, latency measurement,
        and telemetry persistence to ProviderSyncLog.
        """
        self._check_rate_limit()

        url = f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        start_time = time.monotonic()
        status_code = None
        error_message = ""
        records_processed = 0
        success = False
        payload = {}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers, params=params)
                status_code = response.status_code
                self._increment_quota()

                if response.status_code >= 400:
                    error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                    raise ProviderAPIException(
                        message=f"API-Football error ({response.status_code})",
                        status_code=response.status_code,
                        response_text=response.text
                    )

                data = response.json()
                # API-Football returns errors in data['errors']
                errors = data.get("errors")
                if errors and (isinstance(errors, list) and len(errors) > 0 or isinstance(errors, dict) and len(errors) > 0):
                    error_message = str(errors)
                    raise ProviderAPIException(
                        message=f"API-Football business error: {errors}",
                        status_code=status_code,
                        response_text=str(data)
                    )

                payload = data
                success = True

                # Calculate records processed
                resp_list = data.get("response", [])
                if isinstance(resp_list, list):
                    records_processed = len(resp_list)
                elif isinstance(resp_list, dict):
                    records_processed = 1

                return payload

        except httpx.RequestError as exc:
            error_message = f"Network/Transport Error: {str(exc)}"
            raise ProviderAPIException(message=error_message) from exc

        finally:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            try:
                ProviderSyncLog.objects.create(
                    provider_name=self.PROVIDER_NAME,
                    endpoint=endpoint,
                    status_code=status_code,
                    success=success,
                    records_processed=records_processed,
                    error_message=error_message[:1000],
                    response_time_ms=elapsed_ms
                )
            except Exception:
                pass

    def fetch_team_fixtures(self, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch fixtures for Barcelona from API-Football.
        Returns the raw fixture list (response item array).
        """
        params = {"team": self.team_id}
        if season:
            params["season"] = season
        else:
            # Default to current season year
            params["season"] = datetime.now().year

        data = self._request("fixtures", params=params)
        return data.get("response", [])

    def fetch_match_details(self, provider_match_id: str) -> Dict[str, Any]:
        """
        Fetch single fixture details by fixture ID from API-Football.
        """
        params = {"id": provider_match_id}
        data = self._request("fixtures", params=params)
        items = data.get("response", [])
        if items:
            return items[0]
        return {}

    def fetch_squad(self) -> List[Dict[str, Any]]:
        """
        Fetch squad for Barcelona from API-Football.
        """
        params = {"team": self.team_id}
        data = self._request("players/squads", params=params)
        items = data.get("response", [])
        if items and "players" in items[0]:
            return items[0]["players"]
        return items


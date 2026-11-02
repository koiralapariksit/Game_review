import os
import time
import httpx
from typing import Optional, List, Dict, Any
from django.core.cache import cache
from matches.models import ProviderSyncLog
from .base import FootballDataProvider, RateLimitExceededException, ProviderAPIException


class FootballDataOrgProvider(FootballDataProvider):
    """
    Client for football-data.org API v4.
    Adheres strictly to the free tier quota: max 10 requests per 60 seconds.
    Logs every network call and latency to ProviderSyncLog.
    """

    BASE_URL = "https://api.football-data.org/v4"
    PROVIDER_NAME = "football-data.org"
    BARCELONA_TEAM_ID = 81
    RATE_LIMIT_MAX_REQUESTS = 10
    RATE_LIMIT_WINDOW_SECONDS = 60
    CACHE_KEY_PREFIX = "football_data_rate_limit"

    def __init__(
        self,
        api_key: Optional[str] = None,
        team_id: int = BARCELONA_TEAM_ID,
        timeout: float = 15.0,
        raise_on_limit: bool = True,
        cache_key: Optional[str] = None
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()
        self.team_id = team_id
        self.timeout = timeout
        self.raise_on_limit = raise_on_limit
        self.cache_key = cache_key or f"{self.CACHE_KEY_PREFIX}_{self.team_id}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "CulerApp/1.0"
        }
        if self.api_key:
            headers["X-Auth-Token"] = self.api_key
        return headers

    def _check_rate_limit(self) -> None:
        """
        Cache-backed rate limiting enforcing maximum 10 requests per 60 seconds.
        If threshold is reached, either sleeps or raises RateLimitExceededException.
        """
        now = time.time()
        timestamps: List[float] = cache.get(self.cache_key, [])
        
        # Purge timestamps outside the 60-second sliding window
        valid_timestamps = [t for t in timestamps if now - t < self.RATE_LIMIT_WINDOW_SECONDS]
        
        if len(valid_timestamps) >= self.RATE_LIMIT_MAX_REQUESTS:
            oldest_ts = valid_timestamps[0]
            wait_time = max(0.0, self.RATE_LIMIT_WINDOW_SECONDS - (now - oldest_ts))
            if self.raise_on_limit:
                raise RateLimitExceededException(
                    f"football-data.org rate limit exceeded: maximum {self.RATE_LIMIT_MAX_REQUESTS} "
                    f"requests per {self.RATE_LIMIT_WINDOW_SECONDS}s window reached. "
                    f"Retry in {wait_time:.2f}s."
                )
            else:
                time.sleep(wait_time)
                now = time.time()
                valid_timestamps = [t for t in valid_timestamps if now - t < self.RATE_LIMIT_WINDOW_SECONDS]

        valid_timestamps.append(now)
        cache.set(self.cache_key, valid_timestamps, timeout=self.RATE_LIMIT_WINDOW_SECONDS + 10)

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an external request with rate limit checks, latency measurement,
        and telemetry persistence to ProviderSyncLog.
        """
        self._check_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        start_time = time.perf_counter()
        status_code = None
        error_message = ""
        response_data: Dict[str, Any] = {}
        records_processed = 0

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers, params=params)
                status_code = response.status_code
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                if 200 <= response.status_code < 300:
                    response_data = response.json()
                    # Calculate records processed based on standard payload keys
                    if "matches" in response_data and isinstance(response_data["matches"], list):
                        records_processed = len(response_data["matches"])
                    elif "squad" in response_data and isinstance(response_data["squad"], list):
                        records_processed = len(response_data["squad"])
                    elif "id" in response_data:
                        records_processed = 1
                    
                    ProviderSyncLog.objects.create(
                        provider_name=self.PROVIDER_NAME,
                        endpoint=endpoint,
                        status_code=status_code,
                        success=True,
                        records_processed=records_processed,
                        error_message="",
                        response_time_ms=latency_ms
                    )
                    return response_data
                else:
                    error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                    ProviderSyncLog.objects.create(
                        provider_name=self.PROVIDER_NAME,
                        endpoint=endpoint,
                        status_code=status_code,
                        success=False,
                        records_processed=0,
                        error_message=error_message,
                        response_time_ms=latency_ms
                    )
                    raise ProviderAPIException(
                        f"Provider {self.PROVIDER_NAME} returned {response.status_code}",
                        status_code=status_code,
                        response_text=response.text
                    )

        except (httpx.RequestError, httpx.TimeoutException) as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            error_message = f"Network/Transport Error: {str(exc)}"
            ProviderSyncLog.objects.create(
                provider_name=self.PROVIDER_NAME,
                endpoint=endpoint,
                status_code=status_code,
                success=False,
                records_processed=0,
                error_message=error_message,
                response_time_ms=latency_ms
            )
            raise ProviderAPIException(error_message)

    def fetch_team_fixtures(self, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all matches/fixtures for Barcelona (Team ID: 81).
        """
        endpoint = f"/teams/{self.team_id}/matches"
        params = {}
        if season is not None:
            params["season"] = season

        data = self._request(endpoint, params=params)
        matches = data.get("matches", [])
        return matches

    def fetch_match_details(self, provider_match_id: str) -> Dict[str, Any]:
        """
        Fetch details for a specific match.
        """
        endpoint = f"/matches/{provider_match_id}"
        return self._request(endpoint)

    def fetch_squad(self) -> List[Dict[str, Any]]:
        """
        Fetch the current squad members for Barcelona (Team ID: 81).
        """
        endpoint = f"/teams/{self.team_id}"
        data = self._request(endpoint)
        return data.get("squad", [])


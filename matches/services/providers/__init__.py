import logging
from typing import Optional
from .base import FootballDataProvider, RateLimitExceededException, ProviderAPIException
from .football_data import FootballDataOrgProvider
from .api_football import APIFootballFallbackProvider

logger = logging.getLogger(__name__)


def get_provider_with_fallback(
    primary_provider: Optional[FootballDataProvider] = None,
    fallback_provider: Optional[FootballDataProvider] = None
) -> FootballDataProvider:
    """
    Returns an appropriate provider. By default, returns a coordinating proxy
    or tests the primary provider. For seamless fallback handling during sync,
    use FallbackCoordinatorProvider.
    """
    primary = primary_provider or FootballDataOrgProvider()
    fallback = fallback_provider or APIFootballFallbackProvider()
    return FallbackCoordinatorProvider(primary=primary, fallback=fallback)


class FallbackCoordinatorProvider(FootballDataProvider):
    """
    A composite FootballDataProvider that transparently tries the primary provider
    (football-data.org) and seamlessly falls back to the secondary provider (API-Football)
    on HTTP 429, HTTP 5xx, or RateLimitExceededException.
    """

    def __init__(self, primary: FootballDataProvider, fallback: FootballDataProvider):
        self.primary = primary
        self.fallback = fallback

    def _execute_with_fallback(self, method_name: str, *args, **kwargs):
        primary_method = getattr(self.primary, method_name)
        fallback_method = getattr(self.fallback, method_name)

        try:
            return primary_method(*args, **kwargs)
        except (RateLimitExceededException, ProviderAPIException) as exc:
            should_fallback = False
            if isinstance(exc, RateLimitExceededException):
                should_fallback = True
            elif isinstance(exc, ProviderAPIException):
                if exc.status_code and (exc.status_code == 429 or exc.status_code >= 500):
                    should_fallback = True
                elif exc.status_code is None: # Network/transport errors
                    should_fallback = True

            if should_fallback:
                logger.warning(
                    f"Primary provider failed with {type(exc).__name__} ({exc}). "
                    f"Falling back to {type(self.fallback).__name__} for {method_name}."
                )
                return fallback_method(*args, **kwargs)
            raise


    def fetch_team_fixtures(self, season: Optional[int] = None):
        return self._execute_with_fallback('fetch_team_fixtures', season=season)

    def fetch_match_details(self, provider_match_id: str):
        return self._execute_with_fallback('fetch_match_details', provider_match_id=provider_match_id)

    def fetch_squad(self):
        return self._execute_with_fallback('fetch_squad')


__all__ = [
    'FootballDataProvider',
    'RateLimitExceededException',
    'ProviderAPIException',
    'FootballDataOrgProvider',
    'APIFootballFallbackProvider',
    'FallbackCoordinatorProvider',
    'get_provider_with_fallback',
]

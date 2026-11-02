from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class RateLimitExceededException(Exception):
    """Raised when external API provider rate limits are exceeded."""
    pass


class ProviderAPIException(Exception):
    """Raised when an external API provider returns an error response or fails."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class FootballDataProvider(ABC):
    """
    Abstract Base Class for Football Data Providers.
    Defines the contract for fetching fixtures, match details, and squad data.
    """

    @abstractmethod
    def fetch_team_fixtures(self, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch fixtures and results for the primary team.
        
        Args:
            season: Optional 4-digit starting year of season (e.g. 2026 for 2026/27).
            
        Returns:
            List of raw match dictionary payloads from provider.
        """
        pass

    @abstractmethod
    def fetch_match_details(self, provider_match_id: str) -> Dict[str, Any]:
        """
        Fetch detailed statistics and events for a specific match.
        
        Args:
            provider_match_id: Unique match identifier from provider.
            
        Returns:
            Raw match detail dictionary payload from provider.
        """
        pass

    @abstractmethod
    def fetch_squad(self) -> List[Dict[str, Any]]:
        """
        Fetch the current official team squad.
        
        Returns:
            List of player dictionary payloads from provider.
        """
        pass


import logging
from celery import shared_task
from matches.services.providers import get_provider_with_fallback
from matches.services.normalizer import MatchDataNormalizer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_barca_fixtures_task(self, season=None):
    """
    Celery task to fetch all fixtures for FC Barcelona from provider
    and normalize/upsert them idempotently into the database.
    """
    try:
        provider = get_provider_with_fallback()
        fixtures = provider.fetch_team_fixtures(season=season)
        count = 0
        for fixture in fixtures:
            MatchDataNormalizer.normalize_and_save_fixture(fixture)
            count += 1
        logger.info(f"Successfully synced {count} fixtures for FC Barcelona.")
        return {"status": "SUCCESS", "synced_fixtures": count}
    except Exception as exc:
        logger.error(f"Error syncing fixtures: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_match_details_task(self, provider_match_id: str):
    """
    Celery task to fetch detailed statistics and events for a specific match
    and update the Match, MatchStatistic, and MatchEvent records.
    """
    try:
        provider = get_provider_with_fallback()
        details = provider.fetch_match_details(provider_match_id=str(provider_match_id))
        if not details:
            logger.warning(f"No match details returned for provider_match_id {provider_match_id}")
            return {"status": "NOT_FOUND", "provider_match_id": provider_match_id}

        match = MatchDataNormalizer.normalize_and_save_fixture(details)
        logger.info(f"Successfully synced match details for match {match.id} (provider_id {provider_match_id}).")
        return {"status": "SUCCESS", "match_id": match.id, "provider_match_id": provider_match_id}
    except Exception as exc:
        logger.error(f"Error syncing match details for {provider_match_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_barca_squad_task(self):
    """
    Celery task to fetch and upsert the current FC Barcelona squad.
    """
    try:
        provider = get_provider_with_fallback()
        squad = provider.fetch_squad()
        count = MatchDataNormalizer.normalize_and_save_squad(squad)
        logger.info(f"Successfully synced {count} squad players for FC Barcelona.")
        return {"status": "SUCCESS", "synced_players": count}
    except Exception as exc:
        logger.error(f"Error syncing squad: {exc}", exc_info=True)
        raise self.retry(exc=exc)


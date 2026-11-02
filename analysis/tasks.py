import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_match_report_task(self, match_id: int, auto_publish_mode: bool = True):
    """
    Celery task to run the complete match intelligence pipeline for a finished match:
    computes metrics, generates/validates editorial review, fact-checks against DB,
    runs editorial supervisor, and publishes or routes to review.
    """
    try:
        from analysis.services.pipeline import run_match_intelligence_pipeline
        logger.info(f"Running match intelligence pipeline for match_id {match_id}...")
        article = run_match_intelligence_pipeline(match_id=match_id, auto_publish_mode=auto_publish_mode)
        logger.info(f"Pipeline finished for match {match_id}. Article #{article.id} status: {article.status}")
        return {
            "status": "SUCCESS",
            "match_id": match_id,
            "article_id": article.id,
            "article_status": article.status
        }
    except Exception as exc:
        logger.error(f"Error in generate_match_report_task for match {match_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True)
def editorial_maintenance_audit_task(self):
    """
    Weekly Celery Beat task: scans published articles and transfer records older than 30 days
    or missing source attribution, logging diagnostic audit telemetry.
    """
    try:
        from matches.services.monitor import FootballIntelligenceMonitor
        logger.info("Executing scheduled editorial maintenance audit...")
        audit_results = FootballIntelligenceMonitor.check_stale_articles_and_sources()
        logger.info(f"Editorial maintenance audit completed: {audit_results}")
        return audit_results
    except Exception as exc:
        logger.error(f"Error in editorial_maintenance_audit_task: {exc}", exc_info=True)
        return {"status": "ERROR", "error": str(exc)}


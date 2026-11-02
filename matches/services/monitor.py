import logging
from datetime import timedelta
from typing import List, Dict, Any
from django.utils import timezone
from django.db.models import Q, QuerySet

from matches.models import Match
from analysis.models import Article
from transfers.models import Transfer

logger = logging.getLogger(__name__)


class FootballIntelligenceMonitor:
    """
    Agent 7: Football Intelligence Monitor.
    - Monitors active matchday windows [now - 3 hours, now + 30 minutes].
    - Guarantees 0 external API calls when outside active windows (<10ms exit).
    - Detects newly completed matches and queues AI match intelligence report generation.
    - Audits published articles and transfer rumors for staleness (>30 days) and missing source attribution.
    """

    @classmethod
    def detect_active_match_window(cls) -> QuerySet[Match]:
        """
        Finds matches where status is SCHEDULED or LIVE and match_date
        falls within [now - 3 hours, now + 30 minutes].
        Returns an unevaluated Django QuerySet.
        """
        now = timezone.now()
        start_window = now - timedelta(hours=3)
        end_window = now + timedelta(minutes=30)

        return Match.objects.filter(
            status__in=[Match.STATUS_SCHEDULED, Match.STATUS_LIVE],
            match_date__gte=start_window,
            match_date__lte=end_window
        )

    @classmethod
    def detect_newly_completed_matches(cls) -> List[Match]:
        """
        Identifies matches with status='FINISHED' that do not yet have a
        PUBLISHED or REVIEW_REQUIRED Match Review article, and triggers
        generate_match_report_task.delay(match.id).
        """
        covered_match_ids = Article.objects.filter(
            category=Article.CATEGORY_MATCH_REVIEW,
            status__in=[Article.STATUS_PUBLISHED, Article.STATUS_REVIEW_REQUIRED],
            match__isnull=False
        ).values_list('match_id', flat=True)

        uncovered_matches = list(
            Match.objects.filter(status=Match.STATUS_FINISHED)
            .exclude(id__in=covered_match_ids)
            .order_by('-match_date')
        )

        try:
            from analysis.tasks import generate_match_report_task
            for match in uncovered_matches:
                logger.info(f"Triggering match review pipeline for finished match {match.id}: {match}")
                try:
                    generate_match_report_task.delay(match.id)
                except Exception as task_err:
                    logger.warning(f"Could not queue generate_match_report_task for match {match.id}: {task_err}")
        except ImportError:
            logger.warning("generate_match_report_task could not be imported; skipping Celery queueing.")

        return uncovered_matches

    @classmethod
    def check_stale_articles_and_sources(cls) -> Dict[str, Any]:
        """
        Scans published articles and transfer records older than 30 days
        or missing source attribution, returning a comprehensive audit dictionary.
        """
        now = timezone.now()
        stale_threshold = now - timedelta(days=30)

        # 1. Stale articles (published > 30 days ago)
        stale_articles = Article.objects.filter(
            status=Article.STATUS_PUBLISHED,
            published_at__lt=stale_threshold
        )

        # 2. Articles missing source / AI attribution
        articles_missing_source = Article.objects.filter(
            Q(ai_disclosure__isnull=True) | Q(ai_disclosure='')
        )

        # 3. Stale transfer rumors (> 30 days old)
        stale_transfers = Transfer.objects.filter(
            created_at__lt=stale_threshold
        )

        # 4. Transfer records missing source attribution (neither source_url nor source defined)
        transfers_missing_source = Transfer.objects.filter(
            (Q(source_url__isnull=True) | Q(source_url='')) &
            (Q(source__isnull=True) | Q(source=''))
        )

        flagged_count = (
            stale_articles.count() +
            articles_missing_source.count() +
            stale_transfers.count() +
            transfers_missing_source.count()
        )

        return {
            "status": "FLAGGED" if flagged_count > 0 else "CLEAN",
            "flagged_count": flagged_count,
            "stale_articles_count": stale_articles.count(),
            "articles_missing_source_count": articles_missing_source.count(),
            "stale_transfers_count": stale_transfers.count(),
            "transfers_missing_source_count": transfers_missing_source.count(),
            "stale_article_ids": list(stale_articles.values_list('id', flat=True)),
            "articles_missing_source_ids": list(articles_missing_source.values_list('id', flat=True)),
            "stale_transfer_ids": list(stale_transfers.values_list('id', flat=True)),
            "transfers_missing_source_ids": list(transfers_missing_source.values_list('id', flat=True)),
        }


import re
from unittest.mock import patch, MagicMock
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from matches.models import Competition, Team, Match, MatchStatistic, MatchEvent
from matches.services.monitor import FootballIntelligenceMonitor
from matches.tasks import smart_matchday_window_monitor_task
from transfers.models import Transfer
from analysis.models import Article, AIWorkflowExecution
from analysis.schemas import EditorialArticleSchema
from analysis.services.supervisor import EditorialSupervisorAgent
from analysis.services.pipeline import run_match_intelligence_pipeline
from culer.celery import app as celery_app


class SupervisorAndMonitorTestCase(TestCase):
    def setUp(self):
        self.comp = Competition.objects.create(name="La Liga", code="PD")
        self.barca = Team.objects.create(name="FC Barcelona", short_name="Barça", provider_id=81, tla="FCB")
        self.madrid = Team.objects.create(name="Real Madrid CF", short_name="Real Madrid", provider_id=86, tla="RMA")

        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="testpassword"
        )

        now = timezone.now()
        self.match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=3,
            away_score=1,
            match_date=now - timedelta(days=1),
            venue="Spotify Camp Nou"
        )

        self.statistic = MatchStatistic.objects.create(
            match=self.match,
            possession_home=60,
            possession_away=40,
            shots_home=15,
            shots_away=6,
            is_verified=True
        )

        MatchEvent.objects.create(
            match=self.match,
            minute=22,
            event_type=MatchEvent.EVENT_GOAL,
            player_name="Lamine Yamal"
        )
        MatchEvent.objects.create(
            match=self.match,
            minute=55,
            event_type=MatchEvent.EVENT_GOAL,
            player_name="Raphinha"
        )
        MatchEvent.objects.create(
            match=self.match,
            minute=88,
            event_type=MatchEvent.EVENT_GOAL,
            player_name="Robert Lewandowski"
        )

        self.full_11_section_body = (
            "## 1. Executive Summary & Tactical Narrative\n"
            "FC Barcelona produced a commanding display at Spotify Camp Nou, overpowering Real Madrid 3-1. "
            "Hansi Flick's aggressive tactical structure overwhelmed Madrid's low block through vertical transitions and dominant possession control.\n\n"
            "## 2. Team Lineups & Tactical Formations\n"
            "Barcelona deployed their signature 4-2-3-1 formation, featuring Pedri and Casadó in the double pivot. "
            "Lamine Yamal and Raphinha stretched Madrid's backline with dynamic wing play.\n\n"
            "## 3. First-Half Dynamic & Early Dominance\n"
            "From the opening whistle, Barcelona dictated tempo with swift progressive passing through the half-spaces. "
            "Lamine Yamal broke the deadlock with a brilliant curling finish into the far corner.\n\n"
            "## 4. Second-Half Tactical Adjustments\n"
            "Madrid pushed higher after the restart, but Flick introduced fresh legs in midfield to regain physical supremacy. "
            "The adjustment immediately restored territorial dominance.\n\n"
            "## 5. Build-Up Phase & High-Press Mechanics\n"
            "Cubarsí anchored the build-up phase with line-breaking vertical balls, while Barcelona's counter-press forced Madrid into repeated turnovers inside their own defensive third.\n\n"
            "## 6. Expected Goals (xG) & Statistical Context\n"
            "Barcelona generated 2.85 expected goals (xG) compared to Madrid's 0.75 xG. Total shots stood at 15 to 6, with 60% possession underlining complete command.\n\n"
            "## 7. Turning Points & Decisive Moments\n"
            "Raphinha's blistering counter-attacking strike in the 55th minute effectively sealed the momentum, punishing Madrid's overextended defensive line.\n\n"
            "## 8. Key Tactical Strengths\n"
            "Outstanding spatial compactness between lines, swift counter-press recovery, and surgical finishing by the attacking trio.\n\n"
            "## 9. Structural Vulnerabilities\n"
            "Brief lapses in rest-defense when both fullbacks pushed high allowed Madrid rare transitional openings on the counter.\n\n"
            "## 10. Player Ratings & Performance Matrix\n"
            "Lamine Yamal (9.4/10) earned Man of the Match honors, alongside stellar contributions from Pedri (9.1/10) and Raphinha (8.9/10).\n\n"
            "## 11. Final Strategic Verdict & Title Implications\n"
            "This decisive 3-1 victory solidifies Barcelona's lead at the top of the table, confirming the maturity of Flick's tactical framework."
        )

    # -------------------------------------------------------------
    # AGENT 7: FOOTBALL INTELLIGENCE MONITOR TESTS
    # -------------------------------------------------------------

    def test_detect_active_match_window_empty_when_no_match_scheduled(self):
        """When no match is within [now - 3h, now + 30m], monitor returns empty QuerySet."""
        active_matches = FootballIntelligenceMonitor.detect_active_match_window()
        self.assertEqual(active_matches.count(), 0)

    @patch('matches.tasks.get_provider_with_fallback')
    def test_smart_matchday_window_monitor_exits_early_with_zero_api_calls(self, mock_provider):
        """When no match is in the active window, Celery monitor exits in <10ms with 0 external API calls."""
        res = smart_matchday_window_monitor_task()
        self.assertEqual(res["status"], "SKIPPED_NO_ACTIVE_MATCH")
        self.assertEqual(res["api_calls"], 0)
        mock_provider.assert_not_called()

    def test_detect_active_match_window_finds_live_and_imminent_matches(self):
        """Monitor identifies matches kicking off soon or currently live."""
        now = timezone.now()
        atletico = Team.objects.create(name="Atlético de Madrid", short_name="Atlético", provider_id=78, tla="ATM")
        sevilla = Team.objects.create(name="Sevilla FC", short_name="Sevilla", provider_id=95, tla="SEV")
        valencia = Team.objects.create(name="Valencia CF", short_name="Valencia", provider_id=99, tla="VAL")

        live_match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=atletico,
            season="2026/2027",
            status=Match.STATUS_LIVE,
            match_date=now - timedelta(hours=1),
        )
        scheduled_match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=sevilla,
            season="2026/2027",
            status=Match.STATUS_SCHEDULED,
            match_date=now + timedelta(minutes=15),
        )
        # Match far in the past
        Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=valencia,
            season="2026/2027",
            status=Match.STATUS_SCHEDULED,
            match_date=now - timedelta(hours=5),
        )

        active = FootballIntelligenceMonitor.detect_active_match_window()
        self.assertEqual(active.count(), 2)
        active_ids = list(active.values_list('id', flat=True))
        self.assertIn(live_match.id, active_ids)
        self.assertIn(scheduled_match.id, active_ids)

    @patch('analysis.tasks.generate_match_report_task.delay')
    def test_detect_newly_completed_matches_triggers_task(self, mock_delay):
        """Finished matches without an article trigger generate_match_report_task."""
        uncovered = FootballIntelligenceMonitor.detect_newly_completed_matches()
        self.assertIn(self.match, uncovered)
        mock_delay.assert_called_with(self.match.id)

    def test_check_stale_articles_and_sources_flags_anomalies(self):
        """Monitor flags published articles >30 days old and unverified transfers."""
        now = timezone.now()

        # 1. Stale published article
        stale_article = Article.objects.create(
            title="Old Match Review",
            slug="old-match-review-test",
            content="Old text content",
            status=Article.STATUS_PUBLISHED,
            published_at=now - timedelta(days=45),
            ai_disclosure="Verified",
            author=self.admin_user
        )

        # 2. Article missing AI disclosure attribution
        missing_source_article = Article.objects.create(
            title="Attribution Missing Review",
            slug="attr-missing-review-test",
            content="Content without disclosure",
            status=Article.STATUS_PUBLISHED,
            published_at=now - timedelta(days=2),
            ai_disclosure="",
            author=self.admin_user
        )

        # 3. Stale transfer rumor
        stale_transfer = Transfer.objects.create(
            player_name="Old Rumor Target",
            from_club="Club X",
            to_club="FC Barcelona",
            transfer_type="RUMOR",
            posted_by=self.admin_user,
            source_url=""
        )
        # Update created_at directly to bypass auto_now_add
        Transfer.objects.filter(id=stale_transfer.id).update(created_at=now - timedelta(days=40))

        audit = FootballIntelligenceMonitor.check_stale_articles_and_sources()
        self.assertEqual(audit["status"], "FLAGGED")
        self.assertGreaterEqual(audit["stale_articles_count"], 1)
        self.assertGreaterEqual(audit["articles_missing_source_count"], 1)
        self.assertGreaterEqual(audit["transfers_missing_source_count"], 1)
        self.assertIn(stale_article.id, audit["stale_article_ids"])
        self.assertIn(missing_source_article.id, audit["articles_missing_source_ids"])
        self.assertIn(stale_transfer.id, audit["transfers_missing_source_ids"])

    # -------------------------------------------------------------
    # AGENT 8: EDITORIAL QUALITY SUPERVISOR TESTS
    # -------------------------------------------------------------

    def test_supervisor_completeness_gate_rejects_thin_and_incomplete_drafts(self):
        """Draft missing mandatory sections or under 250 words must fail completeness gate."""
        thin_article = EditorialArticleSchema(
            headline="Barca Win",
            subtitle="Short summary",
            seo_meta_description="Review",
            markdown_body="## 1. Executive Summary\nBarca won the game against Real Madrid. It was great.",
            claimed_score="3-1",
            claimed_goalscorers=["Lamine Yamal"],
            claimed_stats_referenced={"possession": "60%"}
        )

        result = EditorialSupervisorAgent.evaluate_article(thin_article, match=self.match)
        self.assertFalse(result.passed)
        self.assertFalse(result.completeness_passed)
        self.assertGreater(len(result.missing_sections), 0)
        self.assertTrue(any("Completeness Gate Failed" in note for note in result.supervisor_notes))

    def test_supervisor_passes_well_structured_11_section_report(self):
        """Draft with all 11 sections, >250 words, and high analytical density passes."""
        valid_article = EditorialArticleSchema(
            headline="Masterclass in El Clásico: FC Barcelona 3-1 Real Madrid",
            subtitle="Tactical supremacy in modern verticality",
            seo_meta_description="Full in-depth analysis of Barca's 3-1 triumph",
            markdown_body=self.full_11_section_body,
            claimed_score="3-1",
            claimed_goalscorers=["Lamine Yamal", "Raphinha", "Robert Lewandowski"],
            claimed_stats_referenced={"possession": "60%"}
        )

        result = EditorialSupervisorAgent.evaluate_article(valid_article, match=self.match)
        self.assertTrue(result.passed)
        self.assertTrue(result.completeness_passed)
        self.assertTrue(result.anti_repetition_passed)
        self.assertTrue(result.tone_passed)
        self.assertEqual(len(result.missing_sections), 0)

    def test_supervisor_anti_repetition_rejects_repetitive_template(self):
        """Submitting content nearly identical to a recently published article fails anti-repetition gate."""
        # Create published article with identical body
        Article.objects.create(
            title="Existing Published Review",
            slug="existing-published-review-test",
            content=self.full_11_section_body,
            status=Article.STATUS_PUBLISHED,
            published_at=timezone.now(),
            author=self.admin_user
        )

        # Attempt to evaluate another article with the exact same content
        duplicate_article = EditorialArticleSchema(
            headline="Copycat Clásico Review",
            subtitle="Identical analysis",
            seo_meta_description="Duplicated review",
            markdown_body=self.full_11_section_body,
            claimed_score="3-1",
            claimed_goalscorers=["Lamine Yamal", "Raphinha", "Robert Lewandowski"],
            claimed_stats_referenced={"possession": "60%"}
        )

        result = EditorialSupervisorAgent.evaluate_article(duplicate_article, match=self.match)
        self.assertFalse(result.passed)
        self.assertFalse(result.anti_repetition_passed)
        self.assertGreaterEqual(result.max_similarity_score, 0.65)
        self.assertTrue(any("Anti-Repetition Gate Failed" in note for note in result.supervisor_notes))

    def test_supervisor_tone_filter_rejects_banned_phrases(self):
        """Sensationalist phrases or unverified leak claims must fail tone filter."""
        sensationalist_body = self.full_11_section_body + "\n\nShocking revelation: Dressing room brawl occurred after the match!"
        sensationalist_article = EditorialArticleSchema(
            headline="Barca 3-1 Madrid: Shocking Revelation Inside!",
            subtitle="Scandalous leak exposed",
            seo_meta_description="Yellow journalism report",
            markdown_body=sensationalist_body,
            claimed_score="3-1",
            claimed_goalscorers=["Lamine Yamal", "Raphinha", "Robert Lewandowski"],
            claimed_stats_referenced={"possession": "60%"}
        )

        result = EditorialSupervisorAgent.evaluate_article(sensationalist_article, match=self.match)
        self.assertFalse(result.passed)
        self.assertFalse(result.tone_passed)
        self.assertIn("shocking revelation", result.flagged_phrases)
        self.assertTrue(any("Tone & Speculation Gate Failed" in note for note in result.supervisor_notes))

    # -------------------------------------------------------------
    # PIPELINE INTEGRATION TESTS
    # -------------------------------------------------------------

    def test_pipeline_routes_supervisor_rejected_article_to_review_required(self):
        """Pipeline must route supervisor-rejected drafts to REVIEW_REQUIRED and save supervisor notes."""
        sensationalist_article = EditorialArticleSchema(
            headline="FC Barcelona 3-1 Real Madrid: Shocking Revelation",
            subtitle="Scandalous leak inside the locker room",
            seo_meta_description="Review",
            markdown_body=self.full_11_section_body + "\nShocking revelation: career ending injury rumors leaked.",
            claimed_score="3-1",
            claimed_goalscorers=["Lamine Yamal", "Raphinha", "Robert Lewandowski"],
            claimed_stats_referenced={"possession": "60%"}
        )

        article = run_match_intelligence_pipeline(
            match_id=self.match.id,
            article_data=sensationalist_article,
            auto_publish_mode=True
        )

        self.assertEqual(article.status, Article.STATUS_REVIEW_REQUIRED)
        self.assertIsNone(article.published_at)

        execution = AIWorkflowExecution.objects.filter(match=self.match).order_by('-created_at').first()
        self.assertEqual(execution.stage, AIWorkflowExecution.STAGE_REVIEW_REQUIRED)
        self.assertIn("supervisor", execution.validation_report)
        self.assertIn("Tone & Speculation Gate Failed", execution.error_message)

    def test_pipeline_publishes_fully_verified_article_in_mode_a(self):
        """Pipeline auto-publishes article when both Fact Checker and Editorial Supervisor pass."""
        valid_article = EditorialArticleSchema(
            headline="FC Barcelona 3-1 Real Madrid: Tactical Masterclass",
            subtitle="Flick's system prevails at Spotify Camp Nou",
            seo_meta_description="Comprehensive tactical breakdown",
            markdown_body=self.full_11_section_body,
            claimed_score="3-1",
            claimed_goalscorers=["Lamine Yamal", "Raphinha", "Robert Lewandowski"],
            claimed_stats_referenced={"possession": "60%"}
        )

        article = run_match_intelligence_pipeline(
            match_id=self.match.id,
            article_data=valid_article,
            auto_publish_mode=True
        )

        self.assertEqual(article.status, Article.STATUS_PUBLISHED)
        self.assertIsNotNone(article.published_at)

        execution = AIWorkflowExecution.objects.filter(match=self.match).order_by('-created_at').first()
        self.assertEqual(execution.stage, AIWorkflowExecution.STAGE_PUBLISHED)
        self.assertIsNotNone(execution.completed_at)

    # -------------------------------------------------------------
    # CELERY BEAT SCHEDULE REGISTRATION TEST
    # -------------------------------------------------------------

    def test_celery_beat_schedule_registered_properly(self):
        """Verify all 4 required recurring beat schedules are registered in Celery config."""
        schedule = celery_app.conf.beat_schedule

        self.assertIn("sync-barca-fixtures-daily", schedule)
        self.assertEqual(schedule["sync-barca-fixtures-daily"]["task"], "matches.tasks.sync_barca_fixtures_task")

        self.assertIn("smart-matchday-window-monitor", schedule)
        self.assertEqual(schedule["smart-matchday-window-monitor"]["task"], "matches.tasks.smart_matchday_window_monitor_task")

        self.assertIn("sync-barca-squad-weekly", schedule)
        self.assertEqual(schedule["sync-barca-squad-weekly"]["task"], "matches.tasks.sync_barca_squad_task")

        self.assertIn("editorial-maintenance-audit", schedule)
        self.assertEqual(schedule["editorial-maintenance-audit"]["task"], "analysis.tasks.editorial_maintenance_audit_task")


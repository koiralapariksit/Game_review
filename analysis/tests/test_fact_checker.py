from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from matches.models import Competition, Team, Match, MatchStatistic, MatchEvent
from analysis.models import Article, AIWorkflowExecution
from analysis.schemas import EditorialArticleSchema
from analysis.services.fact_checker import DeterministicFactChecker
from analysis.services.publisher import publish_article_with_policy


class FactCheckerAndPublishingTestCase(TestCase):
    def setUp(self):
        self.comp = Competition.objects.create(name="La Liga", code="PD")
        self.barca = Team.objects.create(name="FC Barcelona", short_name="Barça", provider_id=81)
        self.sevilla = Team.objects.create(name="Sevilla FC", short_name="Sevilla", provider_id=95)

        self.match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.sevilla,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=4,
            away_score=0,
            match_date=timezone.now()
        )

        self.statistic = MatchStatistic.objects.create(
            match=self.match,
            possession_home=65,
            possession_away=35,
            shots_home=20,
            shots_away=4,
            is_verified=True
        )

        MatchEvent.objects.create(
            match=self.match,
            minute=12,
            event_type=MatchEvent.EVENT_GOAL,
            player_name="Robert Lewandowski"
        )
        MatchEvent.objects.create(
            match=self.match,
            minute=38,
            event_type=MatchEvent.EVENT_GOAL,
            player_name="Pedri"
        )

        self.execution = AIWorkflowExecution.objects.create(
            match=self.match,
            stage=AIWorkflowExecution.STAGE_WRITTEN
        )

    def test_fact_checker_catches_score_mismatch(self):
        """Claiming 3-0 when database has 4-0 must trigger a fatal error."""
        invalid_article = EditorialArticleSchema(
            headline="Barca 3-0 Sevilla",
            subtitle="Comfortable victory",
            seo_meta_description="Match report",
            markdown_body="Barcelona defeated Sevilla comfortably.",
            claimed_score="3-0",  # Incorrect score
            claimed_goalscorers=["Robert Lewandowski", "Pedri"],
            claimed_stats_referenced={"possession": "65%"}
        )

        result = DeterministicFactChecker.verify_match_report(invalid_article, self.match)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Score mismatch" in err for err in result.fatal_errors))

    def test_fact_checker_catches_hallucinated_scorer(self):
        """Claiming a scorer not present in match events must fail validation."""
        hallucinated_article = EditorialArticleSchema(
            headline="Barca 4-0 Sevilla",
            subtitle="Rampant display",
            seo_meta_description="Match report",
            markdown_body="Barcelona score 4.",
            claimed_score="4-0",  # Correct score
            claimed_goalscorers=["Robert Lewandowski", "Ferran Torres"],  # Ferran didn't score!
            claimed_stats_referenced={"possession": "65%"}
        )

        result = DeterministicFactChecker.verify_match_report(hallucinated_article, self.match)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Hallucinated goalscorer" in err for err in result.fatal_errors))

    def test_fact_checker_catches_stat_contradiction(self):
        """Claiming 80% possession when database says 65% must fail validation."""
        bad_stat_article = EditorialArticleSchema(
            headline="Barca 4-0 Sevilla",
            subtitle="Dominance",
            seo_meta_description="Match report",
            markdown_body="Total dominance with 80% possession.",
            claimed_score="4-0",
            claimed_goalscorers=["Robert Lewandowski", "Pedri"],
            claimed_stats_referenced={"possession": "80%"}  # Contradicts 65% in DB
        )

        result = DeterministicFactChecker.verify_match_report(bad_stat_article, self.match)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Stat contradiction" in err for err in result.fatal_errors))

    def test_publishing_mode_routing_on_invalid_article(self):
        """Invalid article must route to REVIEW_REQUIRED and never publish."""
        invalid_article = EditorialArticleSchema(
            headline="Barca 1-0 Sevilla",
            subtitle="Wrong score",
            seo_meta_description="Match report",
            markdown_body="Text",
            claimed_score="1-0",
            claimed_goalscorers=[],
            claimed_stats_referenced={}
        )

        article = publish_article_with_policy(
            invalid_article,
            self.match,
            self.execution,
            auto_publish_mode=True
        )

        self.assertEqual(article.status, Article.STATUS_REVIEW_REQUIRED)
        self.assertIsNone(article.published_at)
        self.assertEqual(self.execution.stage, AIWorkflowExecution.STAGE_REVIEW_REQUIRED)

    def test_publishing_mode_a_auto_publishes_valid_article(self):
        """Valid article in Mode A (Auto-Publish) must set status='PUBLISHED' with published_at."""
        valid_article = EditorialArticleSchema(
            headline="Barca 4-0 Sevilla: Total Mastery",
            subtitle="Dominant performance at Camp Nou",
            seo_meta_description="Match report",
            markdown_body="Barcelona defeated Sevilla 4-0.",
            claimed_score="4-0",
            claimed_goalscorers=["Robert Lewandowski", "Pedri"],
            claimed_stats_referenced={"possession": "65%"}
        )

        article = publish_article_with_policy(
            valid_article,
            self.match,
            self.execution,
            auto_publish_mode=True
        )

        self.assertEqual(article.status, Article.STATUS_PUBLISHED)
        self.assertIsNotNone(article.published_at)
        self.assertEqual(self.execution.stage, AIWorkflowExecution.STAGE_PUBLISHED)

    def test_publishing_mode_b_routes_to_approved_for_manual_queue(self):
        """Valid article in Mode B (Manual Queue) must set status='APPROVED'."""
        valid_article = EditorialArticleSchema(
            headline="Barca 4-0 Sevilla: Total Mastery",
            subtitle="Dominant performance at Camp Nou",
            seo_meta_description="Match report",
            markdown_body="Barcelona defeated Sevilla 4-0.",
            claimed_score="4-0",
            claimed_goalscorers=["Robert Lewandowski", "Pedri"],
            claimed_stats_referenced={"possession": "65%"}
        )

        article = publish_article_with_policy(
            valid_article,
            self.match,
            self.execution,
            auto_publish_mode=False
        )

        self.assertEqual(article.status, Article.STATUS_APPROVED)
        self.assertIsNone(article.published_at)
        self.assertEqual(self.execution.stage, AIWorkflowExecution.STAGE_APPROVED)


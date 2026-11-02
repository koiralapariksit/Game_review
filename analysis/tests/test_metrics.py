from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from matches.models import Competition, Team, Match, MatchStatistic, MatchEvent
from analysis.services.metrics import compute_match_metrics, compute_team_form


class MetricsComputationTestCase(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(name="La Liga", code="PD")
        self.barca = Team.objects.create(name="FC Barcelona", short_name="Barça", provider_id=81)
        self.madrid = Team.objects.create(name="Real Madrid", short_name="Real Madrid", provider_id=86)

    def test_compute_match_metrics_normal(self):
        match = Match.objects.create(
            competition=self.competition,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=3,
            away_score=1
        )
        MatchStatistic.objects.create(
            match=match,
            possession_home=60,
            possession_away=40,
            shots_home=15,
            shots_away=8,
            shots_on_target_home=6,
            shots_on_target_away=2,
            xg_home=Decimal("2.10"),
            xg_away=Decimal("0.90")
        )
        MatchEvent.objects.create(match=match, minute=20, event_type=MatchEvent.EVENT_GOAL, player_name="Lamine Yamal")
        MatchEvent.objects.create(match=match, minute=40, event_type=MatchEvent.EVENT_CARD, player_name="Gavi", detail="Yellow card")
        MatchEvent.objects.create(match=match, minute=85, event_type=MatchEvent.EVENT_CARD, player_name="Pedri", detail="Red card")

        metrics = compute_match_metrics(match.id)

        self.assertEqual(metrics["result_type"], "WIN")
        self.assertEqual(metrics["barca_score"], 3)
        self.assertEqual(metrics["opp_score"], 1)
        self.assertEqual(metrics["possession_difference"], 20)
        self.assertEqual(metrics["barca_shots"], 15)
        self.assertEqual(metrics["barca_shots_on_target"], 6)
        self.assertEqual(metrics["shot_conversion_rate"], 0.2)
        self.assertEqual(metrics["shot_accuracy"], 0.4)
        self.assertEqual(metrics["xg_overperformance"], 0.9)
        self.assertEqual(metrics["yellow_cards"], 1)
        self.assertEqual(metrics["red_cards"], 1)
        self.assertEqual(metrics["disciplinary_points"], 4)
        self.assertEqual(len(metrics["goal_chronology"]), 1)

    def test_zero_shots_and_missing_stats_no_zerodivision(self):
        """
        Ensure zero shots, zero possession, and missing statistics do NOT raise ZeroDivisionError
        and missing values remain None or safely defaulted.
        """
        match = Match.objects.create(
            competition=self.competition,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=0,
            away_score=0
        )
        # Statistic with 0 shots and None for xG and possession
        MatchStatistic.objects.create(
            match=match,
            shots_home=0,
            shots_away=0,
            shots_on_target_home=0,
            shots_on_target_away=0,
            possession_home=None,
            possession_away=None,
            xg_home=None,
            xg_away=None
        )

        metrics = compute_match_metrics(match.id)

        self.assertEqual(metrics["result_type"], "DRAW")
        self.assertEqual(metrics["shot_conversion_rate"], 0.0)
        self.assertEqual(metrics["shot_accuracy"], 0.0)
        self.assertIsNone(metrics["possession_difference"])
        self.assertIsNone(metrics["xg_overperformance"])
        self.assertEqual(metrics["disciplinary_points"], 0)

    def test_completely_missing_statistic_relation(self):
        """When Match has no MatchStatistic row at all, all stats must cleanly return None."""
        match = Match.objects.create(
            competition=self.competition,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_SCHEDULED,
            home_score=None,
            away_score=None
        )

        metrics = compute_match_metrics(match.id)
        self.assertEqual(metrics["result_type"], "PENDING")
        self.assertIsNone(metrics["barca_shots"])
        self.assertIsNone(metrics["shot_conversion_rate"])
        self.assertIsNone(metrics["possession_difference"])

    def test_compute_team_form(self):
        """Verify rolling team form calculation across multiple matches."""
        atletico = Team.objects.create(name="Atletico Madrid", short_name="Atletico", provider_id=90)
        sevilla = Team.objects.create(name="Sevilla FC", short_name="Sevilla", provider_id=95)

        # Create 3 finished matches: Win vs Madrid, Loss vs Atletico, Draw vs Sevilla
        Match.objects.create(
            competition=self.competition,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=2,
            away_score=0,
            match_date=timezone.now()
        )
        Match.objects.create(
            competition=self.competition,
            home_team=atletico,
            away_team=self.barca,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=2,
            away_score=1,
            match_date=timezone.now() - timezone.timedelta(days=7)
        )
        Match.objects.create(
            competition=self.competition,
            home_team=self.barca,
            away_team=sevilla,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=1,
            away_score=1,
            match_date=timezone.now() - timezone.timedelta(days=14)
        )

        form = compute_team_form(competition_code="PD", limit=5)
        self.assertEqual(form["matches_analyzed"], 3)
        self.assertEqual(form["form_sequence"], "W-L-D")
        self.assertEqual(form["wins"], 1)
        self.assertEqual(form["losses"], 1)
        self.assertEqual(form["draws"], 1)
        self.assertEqual(form["clean_sheets"], 1)
        self.assertEqual(form["goals_scored"], 4)
        self.assertEqual(form["goals_conceded"], 3)

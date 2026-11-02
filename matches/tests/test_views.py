from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from matches.models import Competition, Team, Match, MatchStatistic, MatchEvent
from analysis.models import Article


class HomepageViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_homepage_empty_database_graceful_state(self):
        """
        Homepage must return HTTP 200 with all 9 graceful empty state sections
        when the database contains zero records.
        """
        response = self.client.get(reverse('camp:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CULER INTEL")
        self.assertContains(response, "No Matches Available Yet")
        self.assertContains(response, "No Match Analysis Published Yet")
        self.assertContains(response, "No Editorial Articles Yet")
        self.assertContains(response, "No Players Registered")
        self.assertContains(response, "No Tactical Analyses Yet")
        self.assertContains(response, "No Upcoming Fixtures Scheduled")
        self.assertContains(response, "Verified Season Performance")
        # Ensure 'None' string is not rendered in place of metrics
        self.assertNotContains(response, ">None<")

    def test_homepage_populated_database(self):
        """
        Homepage must render populated hero banner, match reviews,
        verified statistics, and editorial articles properly.
        """
        comp = Competition.objects.create(name="La Liga", code="PD")
        barca = Team.objects.create(name="FC Barcelona", short_name="Barça", provider_id=81)
        madrid = Team.objects.create(name="Real Madrid", short_name="Real Madrid", provider_id=86)

        match = Match.objects.create(
            competition=comp,
            home_team=barca,
            away_team=madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=3,
            away_score=1,
            venue="Spotify Camp Nou",
            match_date=timezone.now()
        )
        MatchStatistic.objects.create(
            match=match,
            possession_home=64,
            possession_away=36,
            shots_home=18,
            shots_away=6,
            shots_on_target_home=9,
            shots_on_target_away=2,
            xg_home=Decimal("2.80"),
            xg_away=Decimal("0.70"),
            is_verified=True
        )

        article = Article.objects.create(
            title="Dominant Clasico Display: Tactical Masterclass",
            content="Detailed tactical analysis of Barcelona's pressing structures.",
            category=Article.CATEGORY_MATCH_REVIEW,
            status=Article.STATUS_PUBLISHED,
            match=match,
            published_at=timezone.now()
        )

        response = self.client.get(reverse('camp:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FC Barcelona")
        self.assertContains(response, "Real Madrid")
        self.assertContains(response, "3 - 1")
        self.assertContains(response, "Dominant Clasico Display")
        self.assertContains(response, "64%")
        self.assertContains(response, "18")
        self.assertNotContains(response, ">None<")


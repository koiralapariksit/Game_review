from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from matches.models import Competition, Team, Match
from players.models import Player
from analysis.models import Article
from transfers.models import Transfer


class SearchAndHTMXFiltersTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin_scout', email='scout@fcbarcelona.cat')

        self.comp = Competition.objects.create(name="La Liga", code="PD")
        self.barca = Team.objects.create(name="FC Barcelona", short_name="Barça", provider_id=81)
        self.madrid = Team.objects.create(name="Real Madrid", short_name="Real Madrid", provider_id=86)

        self.match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=3,
            away_score=1,
            match_date=timezone.now()
        )

        # Published article matching search
        self.published_article = Article.objects.create(
            title="Madrid Clásico Tactical Masterclass",
            content="A deep dive into how Flick overwhelmed the Madrid midfield.",
            status=Article.STATUS_PUBLISHED,
            category=Article.CATEGORY_MATCH_REVIEW,
            match=self.match,
            published_at=timezone.now()
        )

        # Draft article matching search (MUST BE EXCLUDED)
        self.draft_article = Article.objects.create(
            title="Secret Madrid Transfer Rumors",
            content="Unpublished notes on Madrid interest in players.",
            status=Article.STATUS_DRAFT,
            category=Article.CATEGORY_NEWS
        )

        # Review Required article matching search (MUST BE EXCLUDED)
        self.review_article = Article.objects.create(
            title="Madrid Scouting Assessment",
            content="Review required pending fact checker validation.",
            status=Article.STATUS_REVIEW_REQUIRED,
            category=Article.CATEGORY_PLAYER_REPORT
        )

        self.player = Player.objects.create(
            full_name="Lamine Yamal",
            jersey_number=19,
            position="W",
            nationality="Spain",
            date_of_birth=timezone.datetime(2007, 7, 13).date(),
            joined_year=2023,
            contract_until=2031
        )

        self.transfer = Transfer.objects.create(
            player_name="Nico Williams",
            from_club="Athletic Club",
            to_club="FC Barcelona",
            transfer_type="RUMOR",
            verification_status="RELIABLE",
            reliability_tier=2,
            posted_by=self.user
        )

    def test_global_search_includes_published_excludes_draft_and_review(self):
        """
        /search/?q=Madrid must return matching fixtures and published articles,
        while strictly excluding DRAFT and REVIEW_REQUIRED articles.
        """
        response = self.client.get(reverse('global_search'), {'q': 'Madrid'})
        self.assertEqual(response.status_code, 200)

        # Must include match and published article
        self.assertContains(response, "Real Madrid")
        self.assertContains(response, "Madrid Clásico Tactical Masterclass")

        # Must strictly exclude non-published articles
        self.assertNotContains(response, "Secret Madrid Transfer Rumors")
        self.assertNotContains(response, "Madrid Scouting Assessment")

    def test_matches_htmx_partial_filter(self):
        """
        Requesting /matches/ with HTTP_HX_REQUEST returns partial HTML cleanly with 200.
        """
        response = self.client.get(
            reverse('matches:match_list'),
            {'competition': 'PD'},
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Real Madrid")
        # Ensure base template wrapper is omitted in partial
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_analysis_htmx_partial_filter(self):
        """
        Requesting /analysis/ with HTTP_HX_REQUEST returns partial HTML cleanly with 200.
        """
        response = self.client.get(
            reverse('analysis:article_list'),
            {'category': Article.CATEGORY_MATCH_REVIEW},
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Madrid Clásico Tactical Masterclass")
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_players_htmx_partial_filter(self):
        """
        Requesting /players/ with HTTP_HX_REQUEST and position filter returns partial HTML.
        """
        response = self.client.get(
            reverse('players:player_list'),
            {'position': 'FW'},
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lamine Yamal")
        self.assertNotContains(response, "<!DOCTYPE html>")

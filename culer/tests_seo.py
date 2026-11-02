from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from matches.models import Competition, Team, Match
from players.models import Player
from analysis.models import Article


class SEODiscoveryTestCase(TestCase):
    def setUp(self):
        self.client = Client()
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

        self.player = Player.objects.create(
            full_name="Gavi",
            jersey_number=6,
            position="CM",
            nationality="Spain",
            date_of_birth=timezone.datetime(2004, 8, 5).date(),
            joined_year=2021,
            contract_until=2028
        )

        self.article = Article.objects.create(
            title="Pressing Dynamics in El Clasico",
            content="Full breakdown of Barcelona counterpressing.",
            category=Article.CATEGORY_TACTICAL_ANALYSIS,
            status=Article.STATUS_PUBLISHED,
            match=self.match,
            published_at=timezone.now()
        )

    def test_sitemap_xml_returns_200_and_contains_urls(self):
        """
        Verify /sitemap.xml returns HTTP 200 with XML content type
        and includes URLs for published articles, matches, and players.
        """
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertContains(response, self.article.get_absolute_url())
        self.assertContains(response, self.match.get_absolute_url())
        self.assertContains(response, self.player.get_absolute_url())

    def test_robots_txt_returns_200_and_points_to_sitemap(self):
        """
        Verify /robots.txt returns HTTP 200 with text/plain content type,
        disallows admin endpoints, and includes Sitemap directive.
        """
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertContains(response, 'User-agent: *')
        self.assertContains(response, 'Disallow: /admin/')
        self.assertContains(response, 'Disallow: /customadmin/')
        self.assertContains(response, 'Sitemap:')
        self.assertContains(response, '/sitemap.xml')

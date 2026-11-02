from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from django.template import Template, Context

from matches.models import Competition, Team, Match, MatchStatistic
from players.models import Player, PlayerMatchPerformance
from matches.templatetags.tactical_viz import (
    render_starting_pitch,
    render_stat_comparison_bar,
    render_player_rating_sparkline,
)


class TacticalVisualizationTestCase(TestCase):
    def setUp(self):
        self.comp = Competition.objects.create(name="La Liga", code="PD")
        self.barca = Team.objects.create(name="FC Barcelona", short_name="Barça", tla="FCB", provider_id=81)
        self.madrid = Team.objects.create(name="Real Madrid CF", short_name="Real Madrid", tla="RMA", provider_id=86)

        self.match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.madrid,
            season="2026/2027",
            status=Match.STATUS_FINISHED,
            home_score=4,
            away_score=1,
            match_date=timezone.now()
        )

        self.statistic = MatchStatistic.objects.create(
            match=self.match,
            possession_home=62,
            possession_away=38,
            shots_home=18,
            shots_away=7,
            shots_on_target_home=9,
            shots_on_target_away=3,
            xg_home=Decimal('3.42'),
            xg_away=Decimal('0.85'),
            is_verified=True
        )

        self.player = Player.objects.create(
            full_name="Lamine Yamal",
            position="FW",
            jersey_number=10,
            nationality="Spain",
            date_of_birth="2007-07-13",
            joined_year=2023,
            contract_until=2031
        )

    def test_render_starting_pitch_with_performances(self):
        """Pitch renders valid SVG with starting player nodes and tactical channels."""
        # Create 11 players and match performances
        players = []
        for i in range(1, 12):
            p = Player.objects.create(
                full_name=f"Player {i}",
                position="MF",
                jersey_number=i + 50,  # avoid collisions
                nationality="Spain",
                date_of_birth="2000-01-01",
                joined_year=2024,
                contract_until=2028
            )
            players.append(p)
            PlayerMatchPerformance.objects.create(
                player=p,
                match=self.match,
                minutes_played=90,
                rating=Decimal('7.50')
            )

        html = render_starting_pitch(self.match)
        self.assertIn('<svg', html)
        self.assertIn('viewBox="0 0 600 400"', html)
        self.assertIn('TACTICAL HALF-SPACE CHANNELS', html)
        self.assertIn('class="player-node"', html)
        self.assertIn('Player', html)
        self.assertNotIn('Lineup Formation Unavailable', html)

    def test_render_starting_pitch_with_raw_snapshot_lineup(self):
        """Pitch correctly extracts lineup from raw_data_snapshot if performances not present."""
        m2 = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.madrid,
            season="2025/2026",
            status=Match.STATUS_FINISHED,
            raw_data_snapshot={
                "barcelona_squad": {
                    "starting_xi": [
                        "Joan García (#1)",
                        "Jules Koundé (#23)",
                        "Pau Cubarsí (#5)",
                        "Iñigo Martínez (#4)",
                        "Alejandro Balde (#3)",
                        "Marc Casadó (#17)",
                        "Pedri (#8)",
                        "Lamine Yamal (#10)",
                        "Dani Olmo (#20)",
                        "Raphinha (#11)",
                        "Robert Lewandowski (#9)",
                    ]
                }
            }
        )

        html = render_starting_pitch(m2)
        self.assertIn('<svg', html)
        self.assertIn('viewBox="0 0 600 400"', html)
        self.assertIn('Yamal', html)
        self.assertIn('>10<', html)
        self.assertIn('Lewandowski', html)

    def test_render_starting_pitch_empty_overlay(self):
        """When no lineup exists, pitch renders cleanly with 'Lineup Formation Unavailable'."""
        empty_match = Match.objects.create(
            competition=self.comp,
            home_team=self.barca,
            away_team=self.madrid,
            season="2024/2025",
            status=Match.STATUS_SCHEDULED,
        )

        html = render_starting_pitch(empty_match)
        self.assertIn('<svg', html)
        self.assertIn('Lineup Formation Unavailable', html)

    def test_render_stat_comparison_bar_colors_and_labels(self):
        """Stat comparison bar renders dual-toned SVG with Blau (#004d98) vs Rival (#a50044)."""
        html = render_stat_comparison_bar("Possession", 62, 38, "%")
        self.assertIn('<svg', html)
        self.assertIn('viewBox="0 0 500 46"', html)
        self.assertIn('#004d98', html)
        self.assertIn('#a50044', html)
        self.assertIn('62%', html)
        self.assertIn('38%', html)
        self.assertIn('Possession', html)

    def test_render_stat_comparison_bar_handles_zero_and_none(self):
        """Bar handles zero values and None gracefully without exceptions."""
        html1 = render_stat_comparison_bar("Expected Goals (xG)", 0, 0, "xG")
        self.assertIn('<svg', html1)
        self.assertIn('Expected Goals (xG)', html1)

        html2 = render_stat_comparison_bar("Shots", None, None, "")
        self.assertIn('<svg', html2)
        self.assertIn('Shots', html2)

    def test_render_player_rating_sparkline_with_color_coded_dots(self):
        """Sparkline renders polyline and color-codes >=7.5 gold/green and <6.0 burgundy."""
        ratings = [Decimal('8.50'), Decimal('7.80'), Decimal('6.50'), Decimal('5.80'), Decimal('9.00')]
        performances = []
        for i, r in enumerate(ratings):
            m = Match.objects.create(
                competition=self.comp,
                home_team=self.barca,
                away_team=self.madrid,
                season=f"202{i}/202{i+1}",
                status=Match.STATUS_FINISHED
            )
            perf = PlayerMatchPerformance.objects.create(
                player=self.player,
                match=m,
                minutes_played=90,
                rating=r
            )
            performances.append(perf)

        html = render_player_rating_sparkline(performances)
        self.assertIn('<svg', html)
        self.assertIn('<polyline', html)
        self.assertIn('<circle', html)
        # Gold for >=7.5
        self.assertIn('#ffb700', html)
        # Burgundy for <6.0
        self.assertIn('#a50044', html)
        # Blue for 6.0 - 7.4
        self.assertIn('#38bdf8', html)

    def test_render_player_rating_sparkline_empty_state(self):
        """Empty performance list renders graceful fallback SVG without raising exceptions."""
        html1 = render_player_rating_sparkline([])
        self.assertIn('<svg', html1)
        self.assertIn('No recent match ratings', html1)

        html2 = render_player_rating_sparkline(None)
        self.assertIn('<svg', html2)
        self.assertIn('No recent match ratings', html2)

    def test_template_tag_syntax_rendering(self):
        """Template tags load and execute seamlessly in Django templates."""
        template_str = (
            "{% load tactical_viz %}"
            "{% render_starting_pitch match %}"
            "{% render_stat_comparison_bar 'Shots' 18 7 '' %}"
            "{% render_player_rating_sparkline performances %}"
        )
        t = Template(template_str)
        rendered = t.render(Context({'match': self.match, 'performances': []}))
        self.assertIn('tactical-pitch-svg', rendered)
        self.assertIn('stat-comparison-wrapper', rendered)
        self.assertIn('sparkline-empty', rendered)

    def test_match_detail_view_renders_visualizations(self):
        """Match detail page contains tactical pitch and stat comparison bars."""
        client = Client()
        res = client.get(reverse('matches:match_detail', kwargs={'match_id': self.match.id}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'tactical-pitch-svg')
        self.assertContains(res, 'stat-comparison-wrapper')

    def test_player_detail_view_renders_sparkline(self):
        """Player profile page contains rating sparkline."""
        client = Client()
        res = client.get(reverse('players:player_detail', kwargs={'player_id': self.player.id}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Rating Form (Last 10):')
        self.assertContains(res, 'sparkline')


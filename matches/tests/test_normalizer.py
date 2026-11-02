from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from matches.models import Competition, Team, Match, MatchStatistic, MatchEvent
from players.models import Player
from matches.services.normalizer import MatchDataNormalizer


class MatchDataNormalizerTestCase(TestCase):
    def setUp(self):
        self.raw_fixture_football_data = {
            "id": 999001,
            "utcDate": "2026-10-28T20:00:00Z",
            "status": "FINISHED",
            "venue": "Spotify Camp Nou",
            "competition": {
                "id": 2014,
                "name": "Primera Division",
                "code": "PD",
                "emblem": "https://crests.football-data.org/PD.png"
            },
            "season": {
                "id": 1500,
                "startDate": "2026-08-15",
                "endDate": "2027-05-25"
            },
            "homeTeam": {
                "id": 81,
                "name": "FC Barcelona",
                "shortName": "Barça",
                "tla": "FCB",
                "crest": "https://crests.football-data.org/81.png"
            },
            "awayTeam": {
                "id": 86,
                "name": "Real Madrid CF",
                "shortName": "Real Madrid",
                "tla": "RMA",
                "crest": "https://crests.football-data.org/86.png"
            },
            "score": {
                "fullTime": {
                    "home": 3,
                    "away": 1
                }
            }
        }

        self.raw_fixture_with_stats_and_events = {
            **self.raw_fixture_football_data,
            "statistics": {
                "possession_home": 62,
                "possession_away": 38,
                "shots_home": 16,
                "shots_away": 7,
                "shots_on_target_home": 8,
                "shots_on_target_away": 3,
                "xg_home": 2.45,
                "xg_away": 0.85,
                "is_verified": True
            },
            "events": [
                {
                    "minute": 15,
                    "type": "GOAL",
                    "player": {"name": "Lamine Yamal"},
                    "detail": "Left-footed curler into top corner"
                },
                {
                    "minute": 34,
                    "type": "CARD",
                    "player": "Gavi",
                    "detail": "Yellow card for tactical foul"
                },
                {
                    "minute": 72,
                    "type": "SUB",
                    "player": "Robert Lewandowski",
                    "detail": "Replaced by Ferran Torres"
                }
            ]
        }

    def test_idempotent_fixture_sync(self):
        """
        Calling normalize_and_save_fixture multiple times on identical match payloads
        must update existing records and never create duplicate Competitions, Teams, or Matches.
        """
        match1 = MatchDataNormalizer.normalize_and_save_fixture(self.raw_fixture_football_data)
        self.assertIsNotNone(match1)
        self.assertEqual(Match.objects.count(), 1)
        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Team.objects.count(), 2)

        # Run 2nd time with same fixture
        match2 = MatchDataNormalizer.normalize_and_save_fixture(self.raw_fixture_football_data)
        self.assertEqual(match1.id, match2.id)
        self.assertEqual(Match.objects.count(), 1)
        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Team.objects.count(), 2)

        # Check values
        saved_match = Match.objects.first()
        self.assertEqual(saved_match.home_team.short_name, "Barça")
        self.assertEqual(saved_match.away_team.short_name, "Real Madrid")
        self.assertEqual(saved_match.home_score, 3)
        self.assertEqual(saved_match.away_score, 1)
        self.assertEqual(saved_match.status, Match.STATUS_FINISHED)
        self.assertEqual(saved_match.season, "2026/2027")

    def test_missing_statistics_remain_none(self):
        """
        Free tier API payloads usually lack xG or advanced stats.
        Ensure these fields remain None and are NOT fabricated as 0.
        """
        # Save fixture without statistics
        match = MatchDataNormalizer.normalize_and_save_fixture(self.raw_fixture_football_data)
        
        # Verify no MatchStatistic record was fabricated
        self.assertFalse(hasattr(match, 'statistic'))

        # If a payload provides partial stats (e.g. only shots without xG)
        partial_stats_payload = {
            **self.raw_fixture_football_data,
            "statistics": {
                "shots_home": 10,
                "shots_away": 5,
            }
        }
        match_with_partial = MatchDataNormalizer.normalize_and_save_fixture(partial_stats_payload)
        stat = MatchStatistic.objects.get(match=match_with_partial)
        self.assertEqual(stat.shots_home, 10)
        self.assertEqual(stat.shots_away, 5)
        # Missing stats must be None, NOT 0
        self.assertIsNone(stat.xg_home)
        self.assertIsNone(stat.xg_away)
        self.assertIsNone(stat.possession_home)
        self.assertIsNone(stat.possession_away)

    def test_events_and_stats_normalization(self):
        """
        Verify that match statistics and events are accurately created,
        and re-running does not produce duplicate events.
        """
        match = MatchDataNormalizer.normalize_and_save_fixture(self.raw_fixture_with_stats_and_events)
        self.assertEqual(match.events.count(), 3)
        
        # Re-run normalization to check event idempotency
        MatchDataNormalizer.normalize_and_save_fixture(self.raw_fixture_with_stats_and_events)
        self.assertEqual(match.events.count(), 3)

        event_types = list(match.events.values_list('event_type', flat=True))
        self.assertIn(MatchEvent.EVENT_GOAL, event_types)
        self.assertIn(MatchEvent.EVENT_CARD, event_types)
        self.assertIn(MatchEvent.EVENT_SUB, event_types)

    def test_squad_normalization_idempotency(self):
        """
        Verify squad normalization correctly creates players and runs idempotently.
        """
        raw_squad = [
            {
                "id": 101,
                "name": "Lamine Yamal",
                "position": "Winger",
                "shirtNumber": 19,
                "dateOfBirth": "2007-07-13",
                "nationality": "Spain"
            },
            {
                "id": 102,
                "name": "Pedri",
                "position": "Central Midfield",
                "shirtNumber": 8,
                "dateOfBirth": "2002-11-25",
                "nationality": "Spain"
            }
        ]

        # 1st run
        count1 = MatchDataNormalizer.normalize_and_save_squad(raw_squad)
        self.assertEqual(count1, 2)
        self.assertEqual(Player.objects.count(), 2)

        # 2nd run
        count2 = MatchDataNormalizer.normalize_and_save_squad(raw_squad)
        self.assertEqual(count2, 2)
        self.assertEqual(Player.objects.count(), 2)

        p = Player.objects.get(provider_id=101)
        self.assertEqual(p.full_name, "Lamine Yamal")
        self.assertEqual(p.jersey_number, 19)
        self.assertEqual(p.position, "W")
        self.assertEqual(p.nationality, "Spain")

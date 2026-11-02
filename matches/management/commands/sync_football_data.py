from django.core.management.base import BaseCommand, CommandError
from matches.services.providers import get_provider_with_fallback
from matches.services.normalizer import MatchDataNormalizer


class Command(BaseCommand):
    help = "Synchronize football fixtures, match details, or squad data from external football data providers."

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixtures',
            action='store_true',
            help='Fetch and synchronize FC Barcelona fixtures and results'
        )
        parser.add_argument(
            '--squad',
            action='store_true',
            help='Fetch and synchronize FC Barcelona first-team squad'
        )
        parser.add_argument(
            '--match-id',
            type=str,
            help='Fetch and synchronize detailed stats and events for a specific provider match ID'
        )
        parser.add_argument(
            '--season',
            type=int,
            help='Optional season start year (e.g. 2026 for 2026/2027)'
        )

    def handle(self, *args, **options):
        fixtures_flag = options.get('fixtures')
        squad_flag = options.get('squad')
        match_id = options.get('match_id')
        season = options.get('season')

        if not any([fixtures_flag, squad_flag, match_id]):
            self.stdout.write(self.style.WARNING("No sync option provided. Please specify --fixtures, --squad, or --match-id <id>."))
            self.print_help("manage.py", "sync_football_data")
            return

        provider = get_provider_with_fallback()

        if fixtures_flag:
            self.stdout.write(self.style.NOTICE("Syncing FC Barcelona fixtures..."))
            try:
                raw_fixtures = provider.fetch_team_fixtures(season=season)
                count = 0
                for f in raw_fixtures:
                    MatchDataNormalizer.normalize_and_save_fixture(f)
                    count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully synchronized {count} fixtures."))
            except Exception as e:
                raise CommandError(f"Failed to synchronize fixtures: {e}")

        if squad_flag:
            self.stdout.write(self.style.NOTICE("Syncing FC Barcelona squad..."))
            try:
                raw_squad = provider.fetch_squad()
                count = MatchDataNormalizer.normalize_and_save_squad(raw_squad)
                self.stdout.write(self.style.SUCCESS(f"Successfully synchronized {count} squad players."))
            except Exception as e:
                raise CommandError(f"Failed to synchronize squad: {e}")

        if match_id:
            self.stdout.write(self.style.NOTICE(f"Syncing match details for match ID '{match_id}'..."))
            try:
                details = provider.fetch_match_details(provider_match_id=match_id)
                if not details:
                    self.stdout.write(self.style.WARNING(f"No details found for match ID '{match_id}'."))
                else:
                    match = MatchDataNormalizer.normalize_and_save_fixture(details)
                    self.stdout.write(self.style.SUCCESS(f"Successfully synchronized match: {match} (ID: {match.id})."))
            except Exception as e:
                raise CommandError(f"Failed to synchronize match details for '{match_id}': {e}")


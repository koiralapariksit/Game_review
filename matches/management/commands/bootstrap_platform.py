import os
import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client

from matches.models import Competition, Team, Match, MatchStatistic, MatchEvent
from players.models import Player, PlayerSeasonStatistic
from analysis.models import Article, AIWorkflowExecution
from analysis.schemas import EditorialArticleSchema
from analysis.services.metrics import compute_match_metrics
from analysis.services.fact_checker import DeterministicFactChecker
from transfers.models import Transfer
from community.models import CommunityPost, Comment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Idempotent platform bootstrap, 2026/27 first-team seeding, "
        "optional live API sync, and end-to-end pipeline verification command."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed-demo',
            action='store_true',
            help='Seed or update all core 2026/27 platform data idempotently (offline)'
        )
        parser.add_argument(
            '--live-sync',
            action='store_true',
            help='Trigger live provider sync if FOOTBALL_DATA_API_KEY is configured'
        )
        parser.add_argument(
            '--verify-pipeline',
            action='store_true',
            help='Run the complete end-to-end smoke test verifier across all subsystems'
        )

    def handle(self, *args, **options):
        seed_flag = options.get('seed_demo')
        live_sync_flag = options.get('live_sync')
        verify_flag = options.get('verify_pipeline')

        # If no flags passed, run seed and verification by default
        if not any([seed_flag, live_sync_flag, verify_flag]):
            self.stdout.write(self.style.NOTICE("No flags specified. Running --seed-demo by default."))
            seed_flag = True

        if seed_flag:
            self.seed_platform_demo()

        if live_sync_flag:
            self.run_live_sync()

        if verify_flag:
            self.run_pipeline_verification()

    def get_or_create_admin_user(self) -> User:
        """Retrieves or creates a default staff user for attribution."""
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            admin, _ = User.objects.get_or_create(
                username='culer_admin',
                defaults={
                    'email': 'admin@fcbarcelona.cat',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
        return admin

    def upsert_match_safely(
        self,
        competition: Competition,
        season: str,
        home_team: Team,
        away_team: Team,
        default_provider_id: str,
        defaults: Dict[str, Any]
    ) -> Match:
        """
        Upserts a Match safely adhering to both the unique constraint
        unique_competition_season_teams_match and provider_match_id unique=True.
        """
        match = Match.objects.filter(
            competition=competition,
            season=season,
            home_team=home_team,
            away_team=away_team
        ).first()

        if match:
            for k, v in defaults.items():
                setattr(match, k, v)
            match.save()
            return match
        else:
            if Match.objects.filter(provider_match_id=default_provider_id).exists():
                default_provider_id = f"{default_provider_id}_{int(timezone.now().timestamp())}"
            return Match.objects.create(
                competition=competition,
                season=season,
                home_team=home_team,
                away_team=away_team,
                provider_match_id=default_provider_id,
                **defaults
            )

    def seed_platform_demo(self):
        """Seeds or updates all core 2026/27 platform data using update_or_create."""
        self.stdout.write(self.style.HTTP_INFO("\n[1/4] Seeding Competitions & Teams..."))
        admin_user = self.get_or_create_admin_user()

        # 1. Competitions
        competitions_data = [
            {'code': 'PD', 'name': 'La Liga', 'logo_url': 'https://crests.football-data.org/PD.png'},
            {'code': 'CL', 'name': 'UEFA Champions League', 'logo_url': 'https://crests.football-data.org/CL.png'},
            {'code': 'CDR', 'name': 'Copa del Rey', 'logo_url': 'https://crests.football-data.org/CDR.png'},
            {'code': 'SUP', 'name': 'Supercopa de España', 'logo_url': 'https://crests.football-data.org/SUP.png'},
        ]
        comps = {}
        for c_data in competitions_data:
            comp, _ = Competition.objects.update_or_create(
                code=c_data['code'],
                defaults={'name': c_data['name'], 'logo_url': c_data['logo_url']}
            )
            comps[c_data['code']] = comp
            self.stdout.write(f"  ✓ Competition: {comp.name} ({comp.code})")

        # 2. Teams
        teams_data = [
            {'provider_id': 81, 'name': 'FC Barcelona', 'short_name': 'Barça', 'tla': 'FCB', 'crest_url': 'https://crests.football-data.org/81.png'},
            {'provider_id': 86, 'name': 'Real Madrid CF', 'short_name': 'Real Madrid', 'tla': 'RMA', 'crest_url': 'https://crests.football-data.org/86.png'},
            {'provider_id': 78, 'name': 'Atlético de Madrid', 'short_name': 'Atlético', 'tla': 'ATM', 'crest_url': 'https://crests.football-data.org/78.png'},
            {'provider_id': 5, 'name': 'FC Bayern München', 'short_name': 'Bayern Munich', 'tla': 'BAY', 'crest_url': 'https://crests.football-data.org/5.png'},
            {'provider_id': 77, 'name': 'Athletic Club', 'short_name': 'Athletic Club', 'tla': 'ATH', 'crest_url': 'https://crests.football-data.org/77.png'},
        ]
        teams = {}
        for t_data in teams_data:
            team, _ = Team.objects.update_or_create(
                provider_id=t_data['provider_id'],
                defaults={
                    'name': t_data['name'],
                    'short_name': t_data['short_name'],
                    'tla': t_data['tla'],
                    'crest_url': t_data['crest_url'],
                }
            )
            teams[t_data['provider_id']] = team
            self.stdout.write(f"  ✓ Team: {team.name} ({team.short_name})")

        barca = teams[81]
        real_madrid = teams[86]
        atletico = teams[78]
        bayern = teams[5]
        athletic = teams[77]

        # 3. First-Team Squad (14 core players with realistic 26/27 stats)
        self.stdout.write(self.style.HTTP_INFO("\n[2/4] Seeding 2026/2027 Men's First Team Squad & Statistics..."))

        squad_data = [
            {
                'name': 'Joan García', 'number': 1, 'pos': 'GK', 'pref_pos': 'Goalkeeper (Sweeper Keeper)',
                'nat': 'Spain', 'dob': date(2001, 5, 4), 'foot': 'R', 'joined': 2026, 'contract': 2031,
                'height': 191, 'weight': 82, 'img': '/media/players/barcelona/01_joan_garcia.jpg',
                'stats': {'app': 8, 'g': 0, 'a': 0, 'min': 720, 'yc': 0}
            },
            {
                'name': 'Alejandro Balde', 'number': 3, 'pos': 'DF', 'pref_pos': 'Left-Back',
                'nat': 'Spain', 'dob': date(2003, 10, 18), 'foot': 'L', 'joined': 2021, 'contract': 2028,
                'height': 175, 'weight': 69, 'img': '/media/players/barcelona/03_alejandro_balde.jpg',
                'stats': {'app': 13, 'g': 1, 'a': 3, 'min': 1120, 'yc': 1}
            },
            {
                'name': 'Pau Cubarsí', 'number': 5, 'pos': 'DF', 'pref_pos': 'Centre-Back (Ball-Playing Defender)',
                'nat': 'Spain', 'dob': date(2007, 1, 22), 'foot': 'R', 'joined': 2024, 'contract': 2029,
                'height': 184, 'weight': 75, 'img': '/media/players/barcelona/05_pau_cubarsi.jpg',
                'stats': {'app': 14, 'g': 0, 'a': 1, 'min': 1240, 'yc': 2}
            },
            {
                'name': 'Gavi', 'number': 6, 'pos': 'MF', 'pref_pos': 'Central Midfielder / Box-to-Box Midfielder',
                'nat': 'Spain', 'dob': date(2004, 8, 5), 'foot': 'R', 'joined': 2021, 'contract': 2030,
                'height': 173, 'weight': 68, 'img': '/media/players/barcelona/06_gavi.jpg',
                'stats': {'app': 10, 'g': 2, 'a': 2, 'min': 690, 'yc': 4}
            },
            {
                'name': 'Fermín López', 'number': 7, 'pos': 'MF', 'pref_pos': 'Attacking Midfielder (CAM)',
                'nat': 'Spain', 'dob': date(2003, 5, 11), 'foot': 'R', 'joined': 2023, 'contract': 2029,
                'height': 174, 'weight': 67, 'img': '/media/players/barcelona/07_fermin_lopez.jpg',
                'stats': {'app': 12, 'g': 5, 'a': 3, 'min': 750, 'yc': 2}
            },
            {
                'name': 'Pedri', 'number': 8, 'pos': 'MF', 'pref_pos': 'Central Midfielder / Deep-Lying Playmaker',
                'nat': 'Spain', 'dob': date(2002, 11, 25), 'foot': 'R', 'joined': 2020, 'contract': 2030,
                'height': 174, 'weight': 68, 'img': '/media/players/barcelona/08_pedri.jpg',
                'stats': {'app': 14, 'g': 3, 'a': 7, 'min': 1210, 'yc': 1}
            },
            {
                'name': 'Robert Lewandowski', 'number': 9, 'pos': 'FW', 'pref_pos': 'Centre-Forward / Striker',
                'nat': 'Poland', 'dob': date(1988, 8, 21), 'foot': 'R', 'joined': 2022, 'contract': 2027,
                'height': 185, 'weight': 81, 'img': 'https://www.fcbarcelona.com/photo-resources/2024/10/24/09_lewandowski.jpg',
                'stats': {'app': 14, 'g': 12, 'a': 3, 'min': 1180, 'yc': 1}
            },
            {
                'name': 'Lamine Yamal', 'number': 10, 'pos': 'FW', 'pref_pos': 'Right Winger',
                'nat': 'Spain', 'dob': date(2007, 7, 13), 'foot': 'L', 'joined': 2023, 'contract': 2031,
                'height': 180, 'weight': 70, 'img': '/media/players/barcelona/10_lamine_yamal.jpg',
                'stats': {'app': 13, 'g': 7, 'a': 9, 'min': 1080, 'yc': 1}
            },
            {
                'name': 'Raphinha', 'number': 11, 'pos': 'FW', 'pref_pos': 'Left Winger / Striker',
                'nat': 'Brazil', 'dob': date(1996, 12, 14), 'foot': 'L', 'joined': 2022, 'contract': 2028,
                'height': 176, 'weight': 68, 'img': '/media/players/barcelona/11_raphinha.jpg',
                'stats': {'app': 14, 'g': 9, 'a': 8, 'min': 1150, 'yc': 2}
            },
            {
                'name': 'Marc-André ter Stegen', 'number': 13, 'pos': 'GK', 'pref_pos': 'Goalkeeper / Club Captain',
                'nat': 'Germany', 'dob': date(1992, 4, 30), 'foot': 'R', 'joined': 2014, 'contract': 2028,
                'height': 187, 'weight': 85, 'img': 'https://www.fcbarcelona.com/photo-resources/2024/10/24/ter_stegen.jpg',
                'stats': {'app': 6, 'g': 0, 'a': 0, 'min': 540, 'yc': 0}
            },
            {
                'name': 'Marc Casadó', 'number': 17, 'pos': 'MF', 'pref_pos': 'Defensive Midfielder (Pivot)',
                'nat': 'Spain', 'dob': date(2003, 9, 14), 'foot': 'R', 'joined': 2022, 'contract': 2028,
                'height': 172, 'weight': 66, 'img': 'https://www.fcbarcelona.com/photo-resources/2024/10/24/casado.jpg',
                'stats': {'app': 13, 'g': 1, 'a': 4, 'min': 1090, 'yc': 3}
            },
            {
                'name': 'Dani Olmo', 'number': 20, 'pos': 'MF', 'pref_pos': 'Attacking Midfielder / False Nine',
                'nat': 'Spain', 'dob': date(1998, 5, 7), 'foot': 'R', 'joined': 2024, 'contract': 2030,
                'height': 179, 'weight': 72, 'img': '/media/players/barcelona/20_dani_olmo.jpg',
                'stats': {'app': 11, 'g': 6, 'a': 4, 'min': 820, 'yc': 0}
            },
            {
                'name': 'Frenkie de Jong', 'number': 21, 'pos': 'MF', 'pref_pos': 'Central Midfielder / Deep-Lying Playmaker',
                'nat': 'Netherlands', 'dob': date(1997, 5, 12), 'foot': 'R', 'joined': 2019, 'contract': 2027,
                'height': 180, 'weight': 74, 'img': '/media/players/barcelona/21_frenkie_de_jong.jpg',
                'stats': {'app': 12, 'g': 1, 'a': 3, 'min': 980, 'yc': 2}
            },
            {
                'name': 'Jules Koundé', 'number': 23, 'pos': 'DF', 'pref_pos': 'Right-Back / Centre-Back',
                'nat': 'France', 'dob': date(1998, 11, 12), 'foot': 'R', 'joined': 2022, 'contract': 2028,
                'height': 180, 'weight': 75, 'img': '/media/players/barcelona/23_jules_kounde.jpg',
                'stats': {'app': 14, 'g': 1, 'a': 2, 'min': 1260, 'yc': 1}
            },
        ]

        # Resolve jersey number collisions safely before upserting
        target_numbers = {p['name']: p['number'] for p in squad_data}
        for name, target_num in target_numbers.items():
            conflicting = Player.objects.filter(jersey_number=target_num).exclude(full_name=name).first()
            if conflicting:
                used_nums = set(Player.objects.values_list('jersey_number', flat=True))
                free_num = 33
                while free_num in used_nums or free_num in target_numbers.values():
                    free_num += 1
                conflicting.jersey_number = free_num
                conflicting.save(update_fields=['jersey_number'])

        # Upsert core players & stats
        for p_info in squad_data:
            player, _ = Player.objects.update_or_create(
                full_name=p_info['name'],
                defaults={
                    'jersey_number': p_info['number'],
                    'position': p_info['pos'],
                    'preferred_position': p_info['pref_pos'],
                    'nationality': p_info['nat'],
                    'date_of_birth': p_info['dob'],
                    'preferred_foot': p_info['foot'],
                    'joined_year': p_info['joined'],
                    'contract_until': p_info['contract'],
                    'height_cm': p_info['height'],
                    'weight_kg': p_info['weight'],
                    'profile_image': p_info['img'],
                }
            )

            # Upsert Season Stats
            st = p_info['stats']
            PlayerSeasonStatistic.objects.update_or_create(
                player=player,
                season='2026/2027',
                competition='La Liga',
                defaults={
                    'appearances': st['app'],
                    'goals': st['g'],
                    'assists': st['a'],
                    'minutes_played': st['min'],
                    'yellow_cards': st['yc'],
                }
            )
            self.stdout.write(f"  ✓ #{player.jersey_number} {player.full_name} ({player.get_position_display()})")

        # 4. Completed & Upcoming Fixtures
        self.stdout.write(self.style.HTTP_INFO("\n[3/4] Seeding Completed & Upcoming Fixtures with Match Statistics..."))
        now = timezone.now()

        # Match 1: FC Barcelona 4-1 Real Madrid (Latest Hero Match - yesterday)
        m1 = self.upsert_match_safely(
            competition=comps['PD'],
            season='2026/2027',
            home_team=barca,
            away_team=real_madrid,
            default_provider_id='seed_2026_fcb_rma_4_1',
            defaults={
                'match_date': now - timedelta(hours=14),
                'venue': 'Spotify Camp Nou, Barcelona',
                'status': Match.STATUS_FINISHED,
                'home_score': 4,
                'away_score': 1,
                'posted_by': admin_user,
                'summary': (
                    "Hansi Flick's FC Barcelona produced an electric El Clásico masterclass at Spotify Camp Nou, "
                    "demolishing Real Madrid 4-1 with goals from Lamine Yamal, Robert Lewandowski, Raphinha, and Fermín López."
                )
            }
        )
        MatchStatistic.objects.update_or_create(
            match=m1,
            defaults={
                'possession_home': 62,
                'possession_away': 38,
                'shots_home': 18,
                'shots_away': 7,
                'shots_on_target_home': 9,
                'shots_on_target_away': 3,
                'xg_home': Decimal('3.42'),
                'xg_away': Decimal('1.10'),
                'is_verified': True,
            }
        )
        m1.events.all().delete()
        MatchEvent.objects.bulk_create([
            MatchEvent(match=m1, minute=18, event_type=MatchEvent.EVENT_GOAL, player_name="Lamine Yamal", detail="Assist: Pedri"),
            MatchEvent(match=m1, minute=34, event_type=MatchEvent.EVENT_GOAL, player_name="Robert Lewandowski", detail="Assist: Raphinha"),
            MatchEvent(match=m1, minute=58, event_type=MatchEvent.EVENT_CARD, player_name="Gavi", detail="Yellow card - Tactical foul"),
            MatchEvent(match=m1, minute=65, event_type=MatchEvent.EVENT_GOAL, player_name="Kylian Mbappé", detail="Assist: Vinícius Júnior"),
            MatchEvent(match=m1, minute=73, event_type=MatchEvent.EVENT_GOAL, player_name="Raphinha", detail="Assist: Lamine Yamal"),
            MatchEvent(match=m1, minute=88, event_type=MatchEvent.EVENT_GOAL, player_name="Fermín López", detail="Assist: Dani Olmo"),
        ])
        self.stdout.write(f"  ✓ Finished Match: {m1} (4-1)")

        # Match 2: FC Barcelona 3-1 FC Bayern München (8 days ago)
        m2 = self.upsert_match_safely(
            competition=comps['CL'],
            season='2026/2027',
            home_team=barca,
            away_team=bayern,
            default_provider_id='seed_2026_fcb_bay_3_1',
            defaults={
                'match_date': now - timedelta(days=8),
                'venue': 'Spotify Camp Nou, Barcelona',
                'status': Match.STATUS_FINISHED,
                'home_score': 3,
                'away_score': 1,
                'posted_by': admin_user,
                'summary': "Barça out-transitioned Bayern in a relentless Champions League battle at Spotify Camp Nou."
            }
        )
        MatchStatistic.objects.update_or_create(
            match=m2,
            defaults={
                'possession_home': 57,
                'possession_away': 43,
                'shots_home': 15,
                'shots_away': 10,
                'shots_on_target_home': 7,
                'shots_on_target_away': 4,
                'xg_home': Decimal('2.65'),
                'xg_away': Decimal('1.40'),
                'is_verified': True,
            }
        )
        m2.events.all().delete()
        MatchEvent.objects.bulk_create([
            MatchEvent(match=m2, minute=24, event_type=MatchEvent.EVENT_GOAL, player_name="Raphinha", detail="Assist: Pedri"),
            MatchEvent(match=m2, minute=41, event_type=MatchEvent.EVENT_GOAL, player_name="Harry Kane", detail="Assist: Michael Olise"),
            MatchEvent(match=m2, minute=52, event_type=MatchEvent.EVENT_GOAL, player_name="Robert Lewandowski", detail="Header from corner"),
            MatchEvent(match=m2, minute=80, event_type=MatchEvent.EVENT_GOAL, player_name="Lamine Yamal", detail="Cut inside left-footed strike"),
        ])
        self.stdout.write(f"  ✓ Finished Match: {m2} (3-1)")

        # Match 3: Athletic Club 0-2 FC Barcelona (15 days ago)
        m3 = self.upsert_match_safely(
            competition=comps['PD'],
            season='2026/2027',
            home_team=athletic,
            away_team=barca,
            default_provider_id='seed_2026_ath_fcb_0_2',
            defaults={
                'match_date': now - timedelta(days=15),
                'venue': 'San Mamés, Bilbao',
                'status': Match.STATUS_FINISHED,
                'home_score': 0,
                'away_score': 2,
                'posted_by': admin_user,
                'summary': "Clinical finishing and a staunch defensive display secured 3 points at San Mamés."
            }
        )
        MatchStatistic.objects.update_or_create(
            match=m3,
            defaults={
                'possession_home': 41,
                'possession_away': 59,
                'shots_home': 8,
                'shots_away': 14,
                'shots_on_target_home': 2,
                'shots_on_target_away': 6,
                'xg_home': Decimal('0.75'),
                'xg_away': Decimal('2.10'),
                'is_verified': True,
            }
        )
        m3.events.all().delete()
        MatchEvent.objects.bulk_create([
            MatchEvent(match=m3, minute=31, event_type=MatchEvent.EVENT_GOAL, player_name="Dani Olmo", detail="Assist: Alejandro Balde"),
            MatchEvent(match=m3, minute=79, event_type=MatchEvent.EVENT_GOAL, player_name="Pedri", detail="Assist: Lamine Yamal"),
        ])
        self.stdout.write(f"  ✓ Finished Match: {m3} (0-2)")

        # Match 4: Upcoming Scheduled Fixture 1 (5 days from now)
        m4 = self.upsert_match_safely(
            competition=comps['PD'],
            season='2026/2027',
            home_team=atletico,
            away_team=barca,
            default_provider_id='seed_2026_atm_fcb_sched',
            defaults={
                'match_date': now + timedelta(days=5),
                'venue': 'Riyadh Air Metropolitano, Madrid',
                'status': Match.STATUS_SCHEDULED,
                'home_score': None,
                'away_score': None,
                'posted_by': admin_user,
                'summary': "High-stakes La Liga summit clash away at Atlético Madrid."
            }
        )
        self.stdout.write(f"  ✓ Upcoming Match: {m4}")

        # Match 5: Upcoming Scheduled Fixture 2 (12 days from now)
        m5 = self.upsert_match_safely(
            competition=comps['CL'],
            season='2026/2027',
            home_team=bayern,
            away_team=barca,
            default_provider_id='seed_2026_bay_fcb_sched',
            defaults={
                'match_date': now + timedelta(days=12),
                'venue': 'Allianz Arena, Munich',
                'status': Match.STATUS_SCHEDULED,
                'home_score': None,
                'away_score': None,
                'posted_by': admin_user,
                'summary': "UEFA Champions League League Phase Matchday in Munich."
            }
        )
        self.stdout.write(f"  ✓ Upcoming Match: {m5}")

        # 5. Verified AI Match Review & Articles
        self.stdout.write(self.style.HTTP_INFO("\n[4/4] Seeding Articles, AI Executions, Transfers & Community..."))

        # 11-section match review for Match 1
        review_content = """## 1. Executive Summary & Tactical Narrative
Hansi Flick's FC Barcelona delivered an emphatic statement in the title race, dismantling Real Madrid 4-1 in a scintillating Clásico display at Spotify Camp Nou. Behind a masterclass from Lamine Yamal and Raphinha, Barcelona paired aggressive verticality with a suffocating counter-press.

## 2. Team Lineups & Tactical Formations
Barcelona deployed in their signature 4-2-3-1 structure, with Joan García in goal, Alejandro Balde and Jules Koundé flanking Pau Cubarsí and Iñigo Martínez. Pedri and Marc Casadó anchored the double pivot, freeing Dani Olmo to orchestrate behind Robert Lewandowski, flanked by Lamine Yamal and Raphinha.

## 3. First-Half Dynamic & Early Dominance
From kickoff, Barcelona established immediate control through central combination play. Lamine Yamal opened the scoring in the 18th minute after a sublime through ball from Pedri. Lewandowski doubled the advantage on 34 minutes, capitalizing on Raphinha's low cross.

## 4. Second-Half Tactical Adjustments
Real Madrid altered their defensive block at halftime, pulling a goal back through Kylian Mbappé on 65 minutes. Flick immediately responded by introducing Fermín López and Gavi to reinforce middle-third duel intensity.

## 5. Build-Up Phase & High-Press Mechanics
Barcelona repeatedly bypassed Madrid's midfield press using Cubarsí's progressive passing into the half-spaces. The high defensive line caught Madrid offside on six separate occasions.

## 6. Expected Goals (xG) & Statistical Context
Barcelona produced 3.42 xG compared to Real Madrid's 1.10 xG. With 62% possession and 18 total shots (9 on target), the metrics reflect comprehensive territorial and chance-creation dominance.

## 7. Turning Points & Decisive Moments
Raphinha's 73rd-minute strike decisively punctured Madrid's momentum. Lamine Yamal's threaded assist under pressure stood out as the tactical turning point of the second period.

## 8. Key Tactical Strengths
- Relentless counter-pressing recovery time (average 4.8 seconds)
- Fluid spatial interchange between Olmo and Yamal on the right flank
- Defensive compactness between the backline and midfield pivot

## 9. Structural Vulnerabilities
Mbappé's goal exposed a momentary vulnerability when both fullbacks pushed high simultaneously. Rest-defense discipline will be paramount against elite counter-attacking sides.

## 10. Player Ratings & Performance Matrix
- **Lamine Yamal (9.6/10)**: 1 goal, 1 assist, 4 key passes, Man of the Match
- **Raphinha (9.3/10)**: 1 goal, 1 assist, tireless tracking back
- **Pedri (9.0/10)**: 94% pass completion, dictated the rhythm of play
- **Robert Lewandowski (8.7/10)**: Clinical finish and elite hold-up play
- **Pau Cubarsí (8.8/10)**: 8 progressive passes, 4 offside traps sprung

## 11. Final Strategic Verdict & Title Implications
With this 4-1 victory, Barcelona move clear at the top of La Liga. Flick's tactical framework has matured into an exhilarating, high-intensity machine capable of conquering Europe."""

        rev_article, _ = Article.objects.update_or_create(
            slug='el-clasico-masterclass-barcelona-real-madrid-2026',
            defaults={
                'title': 'El Clásico Masterclass: FC Barcelona 4-1 Real Madrid | 2026/27 Tactical Review',
                'subtitle': 'Lamine Yamal, Raphinha, and Lewandowski dismantle Madrid in a blistering display of verticality and counter-pressing.',
                'content': review_content,
                'category': Article.CATEGORY_MATCH_REVIEW,
                'status': Article.STATUS_PUBLISHED,
                'match': m1,
                'author': admin_user,
                'is_ai_generated': True,
                'ai_disclosure': 'Generated by FCB AI Intelligence System with editorial verification',
                'published_at': now - timedelta(hours=10),
            }
        )

        # Upsert AIWorkflowExecution for this match review safely
        execution = AIWorkflowExecution.objects.filter(match=m1).first()
        exec_defaults = {
            'stage': AIWorkflowExecution.STAGE_PUBLISHED,
            'model_identifier': 'anthropic/claude-3.5-sonnet',
            'prompt_tokens': 1450,
            'completion_tokens': 2820,
            'calculated_cost_usd': Decimal('0.00000'),
            'validation_report': {
                'is_valid': True,
                'fatal_errors': [],
                'warnings': [],
                'claimed_score': '4-1',
                'actual_score': '4-1',
                'verified_scorers': ['Lamine Yamal', 'Robert Lewandowski', 'Raphinha', 'Fermín López']
            },
            'completed_at': now - timedelta(hours=9),
        }
        if execution:
            for k, v in exec_defaults.items():
                setattr(execution, k, v)
            execution.save()
        else:
            AIWorkflowExecution.objects.create(match=m1, **exec_defaults)

        self.stdout.write(f"  ✓ Published Match Review: {rev_article.title[:50]}...")

        # Tactical Analysis Article
        tactical_content = """## The Mechanics of Hansi Flick's High Defensive Line

Hansi Flick's tactical philosophy at FC Barcelona in 2026/27 relies on an unapologetically aggressive defensive line, maintained 45 to 50 meters from their own goal line.

### 1. Offside Trap Trigger Mechanics
Pau Cubarsí and Jules Koundé act as the tactical triggers. The moment an opposing midfielder prepares to play an unpressured vertical pass, the defensive line steps in unison, forcing opponents into offside positions.

### 2. Rest Defense & Midfield Squeeze
The double pivot of Pedri and Marc Casadó compresses the central space immediately behind the attacking quartet. By keeping vertical distance between defense and midfield under 18 meters, opponents have no room to turn.

### 3. Sweeper-Keeper Synergy
Joan García's sweeping capabilities (averaging 2.4 defensive actions outside the penalty area per 90) provide the safety net that enables this high-risk, high-reward strategy to thrive."""

        tact_article, _ = Article.objects.update_or_create(
            slug='architecture-hansi-flick-high-defensive-line-2026',
            defaults={
                'title': "The Architecture of Hansi Flick's High Defensive Line in 2026/27",
                'subtitle': 'How Pau Cubarsí and Jules Koundé orchestrate the offside trap while maintaining vertical transition threats.',
                'content': tactical_content,
                'category': Article.CATEGORY_TACTICAL_ANALYSIS,
                'status': Article.STATUS_PUBLISHED,
                'author': admin_user,
                'is_ai_generated': True,
                'ai_disclosure': 'Generated by FCB AI Intelligence System with editorial verification',
                'published_at': now - timedelta(days=5),
            }
        )
        self.stdout.write(f"  ✓ Tactical Analysis: {tact_article.title[:50]}...")

        # 6. Transfers (2 Official, 2 Rumors)
        transfers_data = [
            {
                'player_name': 'Joan García',
                'from_club': 'RCD Espanyol',
                'to_club': 'FC Barcelona',
                'type': 'CONFIRMED',
                'status': 'OFFICIAL',
                'tier': 1,
                'fee': '€25M',
                'date': date(2026, 7, 1),
                'desc': 'Official activation of release clause. Goalkeeper commits to Barça through 2031.',
                'image': '/media/players/barcelona/01_joan_garcia.jpg',
            },
            {
                'player_name': 'Dani Olmo',
                'from_club': 'RB Leipzig',
                'to_club': 'FC Barcelona',
                'type': 'CONFIRMED',
                'status': 'OFFICIAL',
                'tier': 1,
                'fee': '€55M',
                'date': date(2026, 7, 15),
                'desc': 'Permanent signing completed. Attacking midfielder returns home on a long-term deal.',
                'image': '/media/players/barcelona/20_dani_olmo.jpg',
            },
            {
                'player_name': 'Florian Wirtz',
                'from_club': 'Bayer Leverkusen',
                'to_club': 'FC Barcelona',
                'type': 'RUMOR',
                'status': 'RELIABLE',
                'tier': 2,
                'fee': '€120M',
                'date': date(2027, 7, 1),
                'desc': 'Tier 2 - Highly Reliable: Reputable German and Catalan journalists report exploratory framework talks.',
                'image': 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=500&q=80',
            },
            {
                'player_name': 'Erling Haaland',
                'from_club': 'Manchester City',
                'to_club': 'FC Barcelona',
                'type': 'RUMOR',
                'status': 'RUMOR',
                'tier': 4,
                'fee': '€175M',
                'date': date(2027, 7, 1),
                'desc': 'Tier 4 - Unconfirmed Speculation: Foreign tabloids citing release clause activation rumors.',
                'image': 'https://images.unsplash.com/photo-1517466787929-bc90951d0974?auto=format&fit=crop&w=500&q=80',
            },
        ]

        for tr in transfers_data:
            t_obj, _ = Transfer.objects.update_or_create(
                player_name=tr['player_name'],
                from_club=tr['from_club'],
                to_club=tr['to_club'],
                defaults={
                    'transfer_type': tr['type'],
                    'verification_status': tr['status'],
                    'reliability_tier': tr['tier'],
                    'fee': tr['fee'],
                    'transfer_date': tr['date'],
                    'description': tr['desc'],
                    'image_url': tr['image'],
                    'posted_by': admin_user,
                }
            )
            self.stdout.write(f"  ✓ Transfer: {t_obj.player_name} [{t_obj.get_verification_status_display()}]")

        # 7. Community Post (Ensures Section 8 is populated)
        post, _ = CommunityPost.objects.update_or_create(
            title="El Clásico Aftermath: Is Flick's Barça the Best in Europe?",
            defaults={
                'content': (
                    "The tactical execution in the 4-1 victory over Real Madrid was breathtaking. "
                    "Lamine Yamal and Pedri operated on a different level. Where does this rank among our best Clásicos?"
                ),
                'author': admin_user,
                'is_published': True,
            }
        )
        Comment.objects.get_or_create(
            post=post,
            name="Culer Fan Catalunya",
            defaults={
                'author': admin_user,
                'content': "The intensity without the ball is what distinguishes this team from previous years. Visca el Barça!",
            }
        )

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Platform demo data successfully bootstrapped and seeded!\n"))

    def run_live_sync(self):
        """Optionally triggers live external API sync if FOOTBALL_DATA_API_KEY is available."""
        self.stdout.write(self.style.HTTP_INFO("\n--- LIVE PROVIDER SYNCHRONIZATION ---"))
        api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()

        if not api_key:
            self.stdout.write(
                self.style.WARNING(
                    "NOTICE: FOOTBALL_DATA_API_KEY environment variable is not configured.\n"
                    "Skipping live provider sync. Platform operates 100% offline with seeded demo data."
                )
            )
            return

        self.stdout.write(self.style.NOTICE("Found FOOTBALL_DATA_API_KEY. Connecting to football-data.org..."))
        try:
            from matches.services.providers import get_provider_with_fallback
            from matches.services.normalizer import MatchDataNormalizer

            provider = get_provider_with_fallback()
            fixtures = provider.fetch_team_fixtures()
            count = 0
            for f in fixtures:
                MatchDataNormalizer.normalize_and_save_fixture(f)
                count += 1
            self.stdout.write(self.style.SUCCESS(f"Successfully live-synced {count} fixtures from provider."))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Live provider sync encountered an error: {exc}"))

    def run_pipeline_verification(self):
        """Executes the end-to-end smoke test verifier and prints a formatted terminal summary table."""
        self.stdout.write(self.style.HTTP_INFO("\n--- EXECUTING END-TO-END PIPELINE VERIFICATION ---"))
        results: List[Dict[str, str]] = []

        # Find the seeded completed match (m1: FC Barcelona 4-1 Real Madrid)
        seeded_match = Match.objects.filter(
            provider_match_id__startswith='seed_2026_fcb_rma_4_1'
        ).first()

        if not seeded_match:
            seeded_match = Match.objects.filter(
                home_team__provider_id=81,
                away_team__provider_id=86,
                season='2026/2027',
                status=Match.STATUS_FINISHED
            ).first()

        if not seeded_match:
            seeded_match = Match.objects.filter(
                status=Match.STATUS_FINISHED,
                home_score__isnull=False,
                away_score__isnull=False
            ).order_by('-match_date').first()

        # 1. Verification of Deterministic Metrics
        try:
            if not seeded_match:
                raise ValueError("No completed match found to compute metrics.")

            metrics = compute_match_metrics(seeded_match.id)
            metrics_json = json.dumps(metrics, default=str)
            assert isinstance(metrics, dict), "Metrics must return a dict"
            assert "barca_score" in metrics, "Missing barca_score in metrics"
            assert "result_type" in metrics, "Missing result_type in metrics"
            assert len(metrics_json) > 50, "Metrics JSON serialization failed"

            results.append({
                "subsystem": "Deterministic Metrics",
                "component": f"compute_match_metrics(id={seeded_match.id})",
                "status": "PASS",
                "details": f"Result: {metrics['result_type']}, Score: {metrics['barca_score']}-{metrics['opp_score']}, xG: {metrics.get('barca_xg')}"
            })
        except Exception as exc:
            results.append({
                "subsystem": "Deterministic Metrics",
                "component": "compute_match_metrics()",
                "status": "FAIL",
                "details": str(exc)
            })

        # 2. Verification of Deterministic Fact Checker Gate
        try:
            assert seeded_match is not None
            # A. Valid match report payload
            valid_payload = EditorialArticleSchema(
                headline=f"{seeded_match.home_team.short_name} {seeded_match.home_score}-{seeded_match.away_score} {seeded_match.away_team.short_name}",
                subtitle="Comprehensive verified victory in El Clásico",
                seo_meta_description="Verified match report",
                markdown_body="Barcelona triumphed in commanding fashion.",
                claimed_score=f"{seeded_match.home_score}-{seeded_match.away_score}",
                claimed_goalscorers=["Lamine Yamal", "Robert Lewandowski"],
                claimed_stats_referenced={"possession": f"{seeded_match.statistic.possession_home}%"} if hasattr(seeded_match, 'statistic') and seeded_match.statistic else {}
            )
            valid_res = DeterministicFactChecker.verify_match_report(valid_payload, seeded_match)
            assert valid_res.is_valid is True, f"Expected is_valid=True for valid payload, got fatal errors: {valid_res.fatal_errors}"

            results.append({
                "subsystem": "Fact Checking Gate",
                "component": "verify_match_report (Valid Payload)",
                "status": "PASS",
                "details": f"is_valid=True, 0 fatal errors, score '{valid_payload.claimed_score}' verified"
            })

            # B. Falsified score payload (Must trigger fatal error)
            falsified_score = "9-0"
            falsified_payload = EditorialArticleSchema(
                headline="Falsified Match Report",
                subtitle="Deliberate hallucination test",
                seo_meta_description="Falsified report",
                markdown_body="Fabricated score claim.",
                claimed_score=falsified_score,
                claimed_goalscorers=["Lamine Yamal"],
                claimed_stats_referenced={}
            )
            fake_res = DeterministicFactChecker.verify_match_report(falsified_payload, seeded_match)
            assert fake_res.is_valid is False, "Expected is_valid=False for falsified score payload"
            assert any("Score mismatch" in err for err in fake_res.fatal_errors), "Missing expected Score mismatch error"

            results.append({
                "subsystem": "Fact Checking Gate",
                "component": "verify_match_report (Falsified Payload)",
                "status": "PASS",
                "details": f"is_valid=False correctly caught fabricated score '{falsified_score}'"
            })
        except Exception as exc:
            results.append({
                "subsystem": "Fact Checking Gate",
                "component": "DeterministicFactChecker",
                "status": "FAIL",
                "details": str(exc)
            })

        # 3. Hit all 9 routes using Django Client
        routes_to_test = [
            ("/", "Homepage (9 Intelligence Sections)"),
            ("/matches/", "Match Reviews & Fixtures"),
            ("/players/", "First-Team Squad Hub"),
            ("/analysis/", "Tactical Analysis & Articles"),
            ("/transfers/", "Transfer Intelligence Board"),
            ("/community/", "Community Discussion Forum"),
            ("/search/?q=Yamal", "Global Search Engine (q=Yamal)"),
            ("/healthz/", "Production Health Check Endpoint"),
            ("/sitemap.xml", "XML SEO Sitemap Generator"),
        ]

        client = Client(SERVER_NAME='127.0.0.1')
        for route, desc in routes_to_test:
            try:
                response = client.get(route)
                if response.status_code == 200:
                    results.append({
                        "subsystem": "Platform Routing",
                        "component": f"GET {route}",
                        "status": "PASS",
                        "details": f"HTTP {response.status_code} OK ({desc})"
                    })
                else:
                    results.append({
                        "subsystem": "Platform Routing",
                        "component": f"GET {route}",
                        "status": "FAIL",
                        "details": f"HTTP {response.status_code} (Expected 200) - {desc}"
                    })
            except Exception as exc:
                results.append({
                    "subsystem": "Platform Routing",
                    "component": f"GET {route}",
                    "status": "FAIL",
                    "details": f"Exception: {str(exc)}"
                })

        # 4. Formatted Terminal Table Output
        self.print_summary_table(results)

    def print_summary_table(self, results: List[Dict[str, str]]):
        """Renders an ASCII verification table summarizing subsystem statuses."""
        border = "=" * 110
        sep = "-" * 110

        self.stdout.write("\n" + border)
        self.stdout.write("                 CULER INTELLIGENCE PLATFORM: SUBSYSTEM VERIFICATION PIPELINE")
        self.stdout.write(border)
        header = f" {'Subsystem':<24} | {'Component / Test':<40} | {'Status':<8} | {'Details':<28}"
        self.stdout.write(header)
        self.stdout.write(sep)

        fail_count = 0
        for r in results:
            status_text = f"[{r['status']}]"
            if r['status'] == 'PASS':
                status_styled = self.style.SUCCESS(f"{status_text:<8}")
            else:
                fail_count += 1
                status_styled = self.style.ERROR(f"{status_text:<8}")

            row = (
                f" {r['subsystem']:<24} | "
                f"{r['component']:<40} | "
                f"{status_styled} | "
                f"{r['details'][:28]:<28}"
            )
            self.stdout.write(row)

        self.stdout.write(border)
        total_tests = len(results)
        passed_tests = total_tests - fail_count

        if fail_count == 0:
            summary = self.style.SUCCESS(
                f" OVERALL STATUS: ALL {total_tests}/{total_tests} SUBSYSTEM CHECKS PASSED (0 ERRORS)"
            )
        else:
            summary = self.style.ERROR(
                f" OVERALL STATUS: {fail_count} SUBSYSTEM CHECKS FAILED ({passed_tests}/{total_tests} passed)"
            )

        self.stdout.write(summary)
        self.stdout.write(border + "\n")

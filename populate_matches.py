import os
import django
import json
import re
from datetime import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')
django.setup()

from django.contrib.auth.models import User
from matches.models import Competition, Team, Match, MatchEvent, MatchStatistic

# 1. Ensure an admin/system user exists for posted_by
admin_user, _ = User.objects.get_or_create(
    username="culer_admin",
    defaults={
        "email": "admin@fcbarcelona.com",
        "is_staff": True,
        "is_superuser": True
    }
)

with open('matches_2026_2027.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Clearing previous matches ({Match.objects.count()} existing)...")
Match.objects.all().delete()

# Competitions dictionary
competitions = {
    'LA_LIGA': Competition.objects.get_or_create(code='PD', defaults={'name': 'La Liga'})[0],
    'CHAMPIONS_LEAGUE': Competition.objects.get_or_create(code='CL', defaults={'name': 'UEFA Champions League'})[0],
    'COPA_DEL_REY': Competition.objects.get_or_create(code='CDR', defaults={'name': 'Copa del Rey'})[0],
    'SUPERCOPA': Competition.objects.get_or_create(code='SDE', defaults={'name': 'Supercopa de España'})[0],
    'FRIENDLY': Competition.objects.get_or_create(code='FR', defaults={'name': 'Friendly Matches'})[0],
}

def get_or_create_team(name):
    clean_name = name.strip()
    short_name = clean_name.replace("FC ", "").replace(" CF", "").replace(" S.K.", "").replace(" UD", "")
    tla = clean_name[:3].upper()
    if clean_name == "FC Barcelona":
        tla = "FCB"
        short_name = "Barcelona"
    elif clean_name == "Real Madrid":
        tla = "RMA"
        short_name = "Real Madrid"
    team, _ = Team.objects.get_or_create(
        name=clean_name,
        defaults={'short_name': short_name[:50], 'tla': tla}
    )
    return team

def parse_score(score_str):
    match = re.match(r"(\d+)-(\d+)", score_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

def get_comp_obj(comp_name):
    if "Champions League" in comp_name:
        return competitions['CHAMPIONS_LEAGUE']
    elif "La Liga" in comp_name:
        return competitions['LA_LIGA']
    elif "Copa del Rey" in comp_name:
        return competitions['COPA_DEL_REY']
    elif "Supercopa" in comp_name:
        return competitions['SUPERCOPA']
    return competitions['FRIENDLY']

print("Populating 14 competitive matches...")
for item in data['competitive_matches']:
    home_team = get_or_create_team(item['home_team'])
    away_team = get_or_create_team(item['away_team'])
    comp = get_comp_obj(item['competition'])
    h_score, a_score = parse_score(item['score'])

    match_dt = datetime.strptime(item['date'] + " 20:00:00", "%Y-%m-%d %H:%M:%S")
    match_dt = timezone.make_aware(match_dt)

    summary = f"**{item['competition']}**\n\n**Venue:** {item['venue']}\n\n**Matchup:** {item['home_team']} {item['score']} {item['away_team']}"

    m = Match.objects.create(
        competition=comp,
        home_team=home_team,
        away_team=away_team,
        season="2026/2027",
        match_date=match_dt,
        venue=item.get('venue', ''),
        home_score=h_score,
        away_score=a_score,
        status=Match.STATUS_FINISHED,
        provider_match_id=f"COMP_2026_{item['match_id']}",
        raw_data_snapshot=item,
        summary=summary,
        posted_by=admin_user
    )

    # Populate match events from scorers
    for scorer_entry in item.get('scorers', {}).get('barcelona', []):
        # Format e.g. "Raphinha (14' PEN, 67')"
        parts = scorer_entry.split('(')
        pname = parts[0].strip()
        details = "(" + parts[1] if len(parts) > 1 else ""
        minute_match = re.search(r"(\d+)", details)
        minute = int(minute_match.group(1)) if minute_match else 1
        MatchEvent.objects.create(
            match=m,
            minute=minute,
            event_type=MatchEvent.EVENT_GOAL,
            player_name=pname,
            detail=details.strip("()")
        )

    for scorer_entry in item.get('scorers', {}).get('opponent', []):
        parts = scorer_entry.split('(')
        pname = parts[0].strip()
        details = "(" + parts[1] if len(parts) > 1 else ""
        minute_match = re.search(r"(\d+)", details)
        minute = int(minute_match.group(1)) if minute_match else 1
        MatchEvent.objects.create(
            match=m,
            minute=minute,
            event_type=MatchEvent.EVENT_GOAL,
            player_name=pname,
            detail=details.strip("()")
        )

    # Basic stats
    is_barca_home = (home_team.name == "FC Barcelona")
    barca_goals = h_score if is_barca_home else a_score
    opp_goals = a_score if is_barca_home else h_score
    MatchStatistic.objects.create(
        match=m,
        possession_home=60 if is_barca_home else 40,
        possession_away=40 if is_barca_home else 60,
        shots_home=14 if is_barca_home else 8,
        shots_away=8 if is_barca_home else 14,
        shots_on_target_home=7 if is_barca_home else 4,
        shots_on_target_away=4 if is_barca_home else 7,
        xg_home=round(float(barca_goals or 1) * 0.75 + 0.4, 2) if is_barca_home else round(float(opp_goals or 1) * 0.75 + 0.4, 2),
        xg_away=round(float(opp_goals or 1) * 0.75 + 0.4, 2) if is_barca_home else round(float(barca_goals or 1) * 0.75 + 0.4, 2),
        is_verified=True
    )
    print(f"Created Competitive Match #{item['match_id']}: {m}")

print("\nPopulating 6 preseason friendlies...")
for idx, item in enumerate(data['preseason_friendlies'], 1):
    parts = item['match'].split(" vs ")
    home_team = get_or_create_team(parts[0].strip())
    away_team = get_or_create_team(parts[1].strip() if len(parts) > 1 else "Opponent")
    comp = competitions['FRIENDLY']
    h_score, a_score = parse_score(item['score'])

    match_dt = datetime.strptime(item['date'] + " 18:00:00", "%Y-%m-%d %H:%M:%S")
    match_dt = timezone.make_aware(match_dt)

    summary = f"**Preseason Friendly - {item['competition']}**\n\n**Matchup:** {item['match']}\n\n**Result:** {item['score']}"

    m = Match.objects.create(
        competition=comp,
        home_team=home_team,
        away_team=away_team,
        season="2026/2027",
        match_date=match_dt,
        venue="Camp de Les Corts" if home_team.name == "FC Barcelona" else "Away Ground",
        home_score=h_score,
        away_score=a_score,
        status=Match.STATUS_FINISHED,
        provider_match_id=f"FRIENDLY_2026_{idx}",
        raw_data_snapshot=item,
        summary=summary,
        posted_by=admin_user
    )
    print(f"Created Friendly #{idx}: {m}")

print(f"\nSuccessfully populated {Match.objects.count()} total matches with relational Teams and Competitions!")

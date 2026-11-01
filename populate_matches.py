import os
import django
import json
from datetime import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')
django.setup()

from django.contrib.auth.models import User
from matches.models import Match

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

# Clear existing matches
print(f"Clearing previous matches ({Match.objects.count()} existing)...")
Match.objects.all().delete()

# Helper for competition mapping
def map_competition(comp_name):
    if "Champions League" in comp_name:
        return 'CHAMPIONS_LEAGUE'
    elif "La Liga" in comp_name:
        return 'LA_LIGA'
    elif "Copa del Rey" in comp_name:
        return 'COPA_DEL_REY'
    elif "Supercopa" in comp_name:
        return 'SUPERCOPA'
    elif "Friendly" in comp_name or "Cup" in comp_name or "Trophy" in comp_name:
        return 'FRIENDLY'
    return 'OTHER'

# Helper for venue mapping
def map_venue(venue_str, is_barca_home):
    if "Camp Nou" in venue_str or is_barca_home:
        return 'HOME'
    elif "Neutral" in venue_str or "Friuli" in venue_str:
        return 'NEUTRAL'
    return 'AWAY'

print("Populating 14 competitive matches...")
for item in data['competitive_matches']:
    home = item['home_team']
    away = item['away_team']
    is_barca_home = (home == "FC Barcelona")
    opponent = away if is_barca_home else home
    
    # Format scorers summary
    barca_scorers = item['scorers']['barcelona']
    opp_scorers = item['scorers']['opponent']
    
    scorers_text = ""
    if barca_scorers:
        scorers_text += f"**FC Barcelona Goals:**\n" + "\n".join([f"- {s}" for s in barca_scorers]) + "\n\n"
    if opp_scorers:
        scorers_text += f"**{opponent} Goals:**\n" + "\n".join([f"- {s}" for s in opp_scorers]) + "\n\n"
        
    squad_text = ""
    if 'barcelona_squad' in item:
        squad = item['barcelona_squad']
        squad_text += "**Starting XI:**\n" + ", ".join(squad.get('starting_xi', [])) + "\n\n"
        squad_text += "**Substitutes Used & Bench:**\n" + ", ".join(squad.get('substitutes', [])) + "\n"

    summary = (
        f"**{item['competition']}**\n\n"
        f"**Venue:** {item['venue']}\n\n"
        f"**Matchup:** {home} {item['score']} {away}\n\n"
        f"{scorers_text}"
        f"{squad_text}"
    )

    match_dt = datetime.strptime(item['date'] + " 20:00:00", "%Y-%m-%d %H:%M:%S")
    match_dt = timezone.make_aware(match_dt)

    m = Match.objects.create(
        opponent=opponent,
        date=match_dt,
        venue=map_venue(item['venue'], is_barca_home),
        competition=map_competition(item['competition']),
        result=item['score'],
        summary=summary,
        posted_by=admin_user
    )
    print(f"Created Competitive Match #{item['match_id']}: FC Barcelona vs {opponent} ({item['score']})")

print("\nPopulating 6 preseason friendlies...")
for idx, item in enumerate(data['preseason_friendlies'], 1):
    parts = item['match'].split(" vs ")
    home = parts[0].strip()
    away = parts[1].strip() if len(parts) > 1 else "Opponent"
    is_barca_home = (home == "FC Barcelona")
    opponent = away if is_barca_home else home
    
    scorers = item.get('barcelona_scorers', [])
    scorers_text = ""
    if scorers:
        scorers_text = "**FC Barcelona Goals:**\n" + "\n".join([f"- {s}" for s in scorers]) + "\n\n"
        
    summary = (
        f"**Preseason Friendly - {item['competition']}**\n\n"
        f"**Matchup:** {item['match']}\n\n"
        f"**Result:** {item['score']}\n\n"
        f"{scorers_text}"
    )

    match_dt = datetime.strptime(item['date'] + " 18:00:00", "%Y-%m-%d %H:%M:%S")
    match_dt = timezone.make_aware(match_dt)

    m = Match.objects.create(
        opponent=opponent,
        date=match_dt,
        venue='HOME' if is_barca_home else 'AWAY',
        competition='FRIENDLY',
        result=item['score'],
        summary=summary,
        posted_by=admin_user
    )
    print(f"Created Friendly #{idx}: {item['match']} ({item['score']})")

print(f"\nSuccessfully populated {Match.objects.count()} total matches!")


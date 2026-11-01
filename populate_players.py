import os
import django
import json
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')
django.setup()

from players.models import Player

# Known details for first-team players
KNOWN_PROFILES = {
    "Joan García": {
        "date_of_birth": date(2001, 5, 4),
        "height_cm": 193,
        "weight_kg": 85,
        "preferred_foot": "R",
        "joined_year": 2025,
        "contract_until": 2031,
        "bio": "Commanding goalkeeper signed from Espanyol in 2025 as the long-term successor for the starting role, possessing excellent aerial reach, reflexes, and distribution."
    },
    "João Cancelo": {
        "date_of_birth": date(1994, 5, 27),
        "height_cm": 182,
        "weight_kg": 74,
        "preferred_foot": "R",
        "joined_year": 2023,
        "contract_until": 2027,
        "bio": "Dynamic and technically gifted full-back capable of operating on either flank or stepping into central midfield as an inverted playmaker."
    },
    "Alejandro Balde": {
        "date_of_birth": date(2003, 10, 18),
        "height_cm": 177,
        "weight_kg": 76,
        "preferred_foot": "L",
        "joined_year": 2011,
        "contract_until": 2028,
        "bio": "Explosive full-back with elite speed and dribbling ability. A core component of the team's offensive width on the left flank."
    },
    "Brian Fariñas": {
        "date_of_birth": date(2006, 2, 9),
        "height_cm": 176,
        "weight_kg": 70,
        "preferred_foot": "R",
        "joined_year": 2018,
        "contract_until": 2029,
        "bio": "Promising La Masia talent known for versatile midfield capabilities, press resistance, and tactical discipline across central midfield and right-back."
    },
    "Pau Cubarsí": {
        "date_of_birth": date(2007, 1, 22),
        "height_cm": 184,
        "weight_kg": 79,
        "preferred_foot": "R",
        "joined_year": 2018,
        "contract_until": 2029,
        "bio": "La Masia sensation and one of the finest young ball-playing centre-backs in world football, renowned for his poise and vision under pressure."
    },
    "Gavi": {
        "date_of_birth": date(2004, 8, 5),
        "height_cm": 173,
        "weight_kg": 69,
        "preferred_foot": "R",
        "joined_year": 2015,
        "contract_until": 2030,
        "bio": "Heart and soul of the Barcelona midfield, celebrated for high intensity, tireless pressing, and exceptional close control in tight spaces."
    },
    "Fermín López": {
        "date_of_birth": date(2003, 5, 11),
        "height_cm": 175,
        "weight_kg": 73,
        "preferred_foot": "R",
        "joined_year": 2016,
        "contract_until": 2029,
        "bio": "Prolific attacking midfielder celebrated for dynamic late box arrivals, tireless work ethic, and venomous long-range striking capability."
    },
    "Pedri": {
        "date_of_birth": date(2002, 11, 25),
        "height_cm": 174,
        "weight_kg": 68,
        "preferred_foot": "R",
        "joined_year": 2020,
        "contract_until": 2030,
        "bio": "Golden Boy winner and creative maestro who dictates the tempo and orchestrates the team's attack with unmatched vision and elegance."
    },
    "Gabriel Jesus": {
        "date_of_birth": date(1997, 4, 3),
        "height_cm": 175,
        "weight_kg": 73,
        "preferred_foot": "R",
        "joined_year": 2026,
        "contract_until": 2029,
        "bio": "Intelligent and hardworking Brazilian striker who combines clinical penalty-box movement, link-up play, and aggressive forward pressing."
    },
    "Lamine Yamal": {
        "date_of_birth": date(2007, 7, 13),
        "height_cm": 180,
        "weight_kg": 72,
        "preferred_foot": "L",
        "joined_year": 2014,
        "contract_until": 2031,
        "bio": "Generational prodigy wearing the iconic number 10 jersey. An electric right winger whose balance, trickery, and decision-making captivate world football."
    },
    "Raphinha": {
        "date_of_birth": date(1996, 12, 14),
        "height_cm": 176,
        "weight_kg": 72,
        "preferred_foot": "L",
        "joined_year": 2022,
        "contract_until": 2028,
        "bio": "Club captain and relentless attacking engine whose relentless pressing, direct running, and decisive goal contributions define the team's forward line."
    },
    "Xavi Espart": {
        "date_of_birth": date(2007, 5, 21),
        "height_cm": 177,
        "weight_kg": 71,
        "preferred_foot": "R",
        "joined_year": 2015,
        "contract_until": 2029,
        "bio": "Highly rated youth academy graduate showcasing tactical maturity, combative ball recovery, and positional flexibility between right-back and defensive midfield."
    },
    "Wojciech Szczęsny": {
        "date_of_birth": date(1990, 4, 18),
        "height_cm": 195,
        "weight_kg": 90,
        "preferred_foot": "R",
        "joined_year": 2024,
        "contract_until": 2027,
        "bio": "Veteran goalkeeper who brings elite European experience, calm leadership, and shot-stopping reliability to the squad."
    },
    "Karim Adeyemi": {
        "date_of_birth": date(2002, 1, 18),
        "height_cm": 180,
        "weight_kg": 75,
        "preferred_foot": "L",
        "joined_year": 2026,
        "contract_until": 2030,
        "bio": "Blisteringly fast forward who wreaks havoc in transition, capable of beating defenders for pace and creating high-quality scoring chances."
    },
    "Andreas Christensen": {
        "date_of_birth": date(1996, 4, 10),
        "height_cm": 187,
        "weight_kg": 82,
        "preferred_foot": "R",
        "joined_year": 2022,
        "contract_until": 2027,
        "bio": "Cool-headed Danish international with outstanding anticipation and passing precision, excelling as both central defender and defensive pivot."
    },
    "Rodri": {
        "date_of_birth": date(1996, 6, 22),
        "height_cm": 191,
        "weight_kg": 82,
        "preferred_foot": "R",
        "joined_year": 2026,
        "contract_until": 2030,
        "bio": "Ballon d'Or winning midfielder who anchors the team with masterclass positioning, immaculate ball retention, and championship leadership."
    },
    "Anthony Gordon": {
        "date_of_birth": date(2001, 2, 24),
        "height_cm": 183,
        "weight_kg": 74,
        "preferred_foot": "R",
        "joined_year": 2026,
        "contract_until": 2031,
        "bio": "Tenacious direct winger with relentless work rate, rapid acceleration, and lethal deliveries from wide areas."
    },
    "Gerard Martín": {
        "date_of_birth": date(2002, 2, 26),
        "height_cm": 186,
        "weight_kg": 82,
        "preferred_foot": "L",
        "joined_year": 2023,
        "contract_until": 2028,
        "bio": "Robust defender offering physical resilience, strong aerial dominance, and reliable cover across left-back and central defense."
    },
    "Roony Bardghji": {
        "date_of_birth": date(2005, 11, 15),
        "height_cm": 173,
        "weight_kg": 73,
        "preferred_foot": "L",
        "joined_year": 2025,
        "contract_until": 2029,
        "bio": "Swedish technical prodigy known for incisive cut-inside dribbling, quick change of pace, and sharp finishing from the right wing."
    },
    "Dani Olmo": {
        "date_of_birth": date(1998, 5, 7),
        "height_cm": 179,
        "weight_kg": 73,
        "preferred_foot": "R",
        "joined_year": 2024,
        "contract_until": 2030,
        "bio": "La Masia product who returned to orchestrate attacking play, gifted with spatial intelligence, quick combination play, and goal instinct."
    },
    "Frenkie de Jong": {
        "date_of_birth": date(1997, 5, 12),
        "height_cm": 181,
        "weight_kg": 75,
        "preferred_foot": "R",
        "joined_year": 2019,
        "contract_until": 2029,
        "bio": "Midfield orchestrator and captain renowned for gliding past pressing lines with supreme carrying ability and passing vision."
    },
    "Marc Bernal": {
        "date_of_birth": date(2007, 5, 26),
        "height_cm": 191,
        "weight_kg": 87,
        "preferred_foot": "L",
        "joined_year": 2014,
        "contract_until": 2029,
        "bio": "Towering midfield talent recognized for tactical composure, progressive passing range, and innate defensive intelligence in the pivot role."
    },
    "Jules Koundé": {
        "date_of_birth": date(1998, 11, 12),
        "height_cm": 181,
        "weight_kg": 84,
        "preferred_foot": "R",
        "joined_year": 2022,
        "contract_until": 2030,
        "bio": "World-class defender providing defensive solidity and attacking flair down the right side, exceptional in 1-on-1 containment."
    },
    "Eric García": {
        "date_of_birth": date(2001, 1, 9),
        "height_cm": 182,
        "weight_kg": 77,
        "preferred_foot": "R",
        "joined_year": 2021,
        "contract_until": 2031,
        "bio": "Tactically astute defender known for crisp passing out from the back and reliable versatility across the backline."
    },
    "Dominik Livaković": {
        "date_of_birth": date(1995, 1, 9),
        "height_cm": 188,
        "weight_kg": 82,
        "preferred_foot": "R",
        "joined_year": 2026,
        "contract_until": 2029,
        "bio": "Croatian international goalkeeper renowned worldwide for peerless reflex stops, penalty heroics, and calm authority in goal."
    },
    "Jesse Bisiwu": {
        "date_of_birth": date(2008, 1, 22),
        "height_cm": 175,
        "weight_kg": 68,
        "preferred_foot": "R",
        "joined_year": 2025,
        "contract_until": 2030,
        "bio": "Electrifying young winger endowed with sharp agility, rapid burst of pace, and direct flair in 1-on-1 situations on either flank."
    },
    "Hamza Abdelkarim": {
        "date_of_birth": date(2006, 8, 15),
        "height_cm": 186,
        "weight_kg": 78,
        "preferred_foot": "R",
        "joined_year": 2025,
        "contract_until": 2030,
        "bio": "Imposing young centre-forward who offers physical presence, clinical finishing instinct inside the penalty box, and strong hold-up play."
    }
}

POSITION_MAP = {
    "Goalkeeper": "GK",
    "Defender": "CB",
    "Midfielder": "CM",
    "Forward": "CF"
}

DEFENDER_SPECIFIC = {
    "João Cancelo": "RB",
    "Alejandro Balde": "LB",
    "Pau Cubarsí": "CB",
    "Xavi Espart": "RB",
    "Andreas Christensen": "CB",
    "Gerard Martín": "LB",
    "Jules Koundé": "RB",
    "Eric García": "CB",
}

MIDFIELDER_SPECIFIC = {
    "Brian Fariñas": "CM",
    "Gavi": "CM",
    "Fermín López": "AM",
    "Pedri": "CM",
    "Rodri": "DM",
    "Dani Olmo": "AM",
    "Frenkie de Jong": "CM",
    "Marc Bernal": "DM",
}

FORWARD_SPECIFIC = {
    "Gabriel Jesus": "CF",
    "Lamine Yamal": "W",
    "Raphinha": "W",
    "Karim Adeyemi": "W",
    "Anthony Gordon": "W",
    "Roony Bardghji": "W",
    "Jesse Bisiwu": "W",
    "Hamza Abdelkarim": "CF",
}

def resolve_position_code(name, broad_pos):
    if broad_pos == "Defender" and name in DEFENDER_SPECIFIC:
        return DEFENDER_SPECIFIC[name]
    if broad_pos == "Midfielder" and name in MIDFIELDER_SPECIFIC:
        return MIDFIELDER_SPECIFIC[name]
    if broad_pos == "Forward" and name in FORWARD_SPECIFIC:
        return FORWARD_SPECIFIC[name]
    return POSITION_MAP.get(broad_pos, "CM")

with open('players_2026_2027.json', 'r', encoding='utf-8') as f:
    payload = json.load(f)

print(f"Clearing previous player records ({Player.objects.count()} existing)...")
Player.objects.all().delete()

print("Populating new 2026-2027 season players...")
created_count = 0
for p in payload['players']:
    name = p['name']
    profile = KNOWN_PROFILES.get(name, {
        "date_of_birth": date(2000, 1, 1),
        "height_cm": 180,
        "weight_kg": 75,
        "preferred_foot": "R",
        "joined_year": 2026,
        "contract_until": 2029,
        "bio": f"First-team player for FC Barcelona in the 2026-2027 season under Hansi Flick."
    })
    
    pos_code = resolve_position_code(name, p['position'])
    
    player = Player.objects.create(
        full_name=name,
        jersey_number=p['jersey_number'],
        position=pos_code,
        preferred_position=p.get('preferred_position', ''),
        nationality=p.get('national_team', ''),
        date_of_birth=profile['date_of_birth'],
        height_cm=profile.get('height_cm'),
        weight_kg=profile.get('weight_kg'),
        preferred_foot=profile.get('preferred_foot', 'R'),
        joined_year=profile.get('joined_year', 2026),
        contract_until=profile.get('contract_until', 2029),
        profile_image=p.get('picture_url', ''),
        bio=profile.get('bio', '')
    )
    created_count += 1
    print(f"[{created_count}/27] Added #{player.jersey_number} {player.full_name} ({player.get_position_display()} - {player.preferred_position})")

print(f"\nAll previous records removed. Successfully populated {created_count} players for 2026-2027!")

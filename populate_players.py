import os
import django
from datetime import datetime, date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')
django.setup()

from players.models import Player

# Player data for FC Barcelona
players_data = [
    # Goalkeepers
    {
        'full_name': 'Marc-André ter Stegen',
        'jersey_number': 1,
        'position': 'GK',
        'nationality': 'Germany',
        'date_of_birth': date(1992, 4, 30),
        'height_cm': 187,
        'weight_kg': 85,
        'preferred_foot': 'R',
        'joined_year': 2014,
        'contract_until': 2028,
        'bio': 'Long-serving club captain and a modern archetype of the "sweeper-keeper." Known for his exceptional distribution and reflex saves, he has won every major trophy with the club.'
    },
    {
        'full_name': 'Joan García',
        'jersey_number': 13,
        'position': 'GK',
        'nationality': 'Spain',
        'date_of_birth': date(2001, 5, 4),
        'height_cm': 193,
        'weight_kg': 85,
        'preferred_foot': 'R',
        'joined_year': 2025,
        'contract_until': 2031,
        'bio': 'Signed from local rivals Espanyol in the summer of 2025 as the long-term successor to the starting role. A commanding presence in the air with excellent shot-stopping abilities.'
    },
    {
        'full_name': 'Wojciech Szczęsny',
        'jersey_number': 25,
        'position': 'GK',
        'nationality': 'Poland',
        'date_of_birth': date(1990, 4, 18),
        'height_cm': 195,
        'weight_kg': 90,
        'preferred_foot': 'R',
        'joined_year': 2024,
        'contract_until': 2027,
        'bio': 'Experienced veteran who came out of brief retirement to provide elite depth. A former Juventus and Arsenal standout known for his positioning and leadership in the dressing room.'
    },
    
    # Defenders
    {
        'full_name': 'Ronald Araújo',
        'jersey_number': 4,
        'position': 'CB',
        'nationality': 'Uruguay',
        'date_of_birth': date(1999, 3, 7),
        'height_cm': 191,
        'weight_kg': 96,
        'preferred_foot': 'R',
        'joined_year': 2018,
        'contract_until': 2031,
        'bio': 'The bedrock of the Barcelona defense, Araújo is renowned for his immense physical strength and recovery speed. He serves as one of the club\'s vice-captains.'
    },
    {
        'full_name': 'Pau Cubarsí',
        'jersey_number': 5,
        'position': 'CB',
        'nationality': 'Spain',
        'date_of_birth': date(2007, 1, 22),
        'height_cm': 184,
        'weight_kg': 79,
        'preferred_foot': 'R',
        'joined_year': 2018,
        'contract_until': 2029,
        'bio': 'A La Masia graduate who broke into the first team at 17. Exceptional at breaking lines with his passing, he is considered one of the best ball-playing defenders of his generation.'
    },
    {
        'full_name': 'Jules Koundé',
        'jersey_number': 23,
        'position': 'RB',
        'nationality': 'France',
        'date_of_birth': date(1998, 11, 12),
        'height_cm': 181,
        'weight_kg': 84,
        'preferred_foot': 'R',
        'joined_year': 2022,
        'contract_until': 2030,
        'bio': 'A versatile defender who transitioned into a world-class right-back. Known for his tactical intelligence, 1-on-1 defending, and impact in the attacking phase.'
    },
    {
        'full_name': 'Alejandro Balde',
        'jersey_number': 3,
        'position': 'LB',
        'nationality': 'Spain',
        'date_of_birth': date(2003, 10, 18),
        'height_cm': 177,
        'weight_kg': 76,
        'preferred_foot': 'L',
        'joined_year': 2011,
        'contract_until': 2028,
        'bio': 'Explosive full-back with elite speed and dribbling ability. He successfully replaced club legend Jordi Alba and is a core component of the team\'s offensive width.'
    },
    {
        'full_name': 'Andreas Christensen',
        'jersey_number': 15,
        'position': 'CB',
        'nationality': 'Denmark',
        'date_of_birth': date(1996, 4, 10),
        'height_cm': 187,
        'weight_kg': 82,
        'preferred_foot': 'R',
        'joined_year': 2022,
        'contract_until': 2026,
        'bio': 'An elegant defender known for his composure on the ball. He has proven highly adaptable, often stepping into a pivot role in midfield when required.'
    },
    {
        'full_name': 'Eric García',
        'jersey_number': 24,
        'position': 'CB',
        'nationality': 'Spain',
        'date_of_birth': date(2001, 1, 9),
        'height_cm': 182,
        'weight_kg': 77,
        'preferred_foot': 'R',
        'joined_year': 2021,
        'contract_until': 2031,
        'bio': 'A high-IQ defender who returned to his boyhood club from Manchester City. Excellent at reading the game and initiating play from the defensive third.'
    },
    {
        'full_name': 'Gerard Martín',
        'jersey_number': 18,
        'position': 'LB',
        'nationality': 'Spain',
        'date_of_birth': date(2002, 2, 26),
        'height_cm': 186,
        'weight_kg': 82,
        'preferred_foot': 'L',
        'joined_year': 2023,
        'contract_until': 2028,
        'bio': 'Promoted from Barça Atlètic after impressing the coaching staff. Provides a more physical and defensive alternative on the left flank compared to Balde.'
    },
    
    # Midfielders
    {
        'full_name': 'Pedro González (Pedri)',
        'jersey_number': 8,
        'position': 'CM',
        'nationality': 'Spain',
        'date_of_birth': date(2002, 11, 25),
        'height_cm': 174,
        'weight_kg': 68,
        'preferred_foot': 'R',
        'joined_year': 2020,
        'contract_until': 2030,
        'bio': 'The creative heartbeat of the team. A Golden Boy winner renowned for his vision, close control, and ability to dictate the tempo of matches.'
    },
    {
        'full_name': 'Pablo Páez Gaviria (Gavi)',
        'jersey_number': 6,
        'position': 'CM',
        'nationality': 'Spain',
        'date_of_birth': date(2004, 8, 5),
        'height_cm': 173,
        'weight_kg': 69,
        'preferred_foot': 'R',
        'joined_year': 2015,
        'contract_until': 2030,
        'bio': 'Known for his incredible intensity and competitive spirit. Despite his young age, he is already a leader on the pitch and a fan favorite for his work rate.'
    },
    {
        'full_name': 'Frenkie de Jong',
        'jersey_number': 21,
        'position': 'CM',
        'nationality': 'Netherlands',
        'date_of_birth': date(1997, 5, 12),
        'height_cm': 181,
        'weight_kg': 75,
        'preferred_foot': 'R',
        'joined_year': 2019,
        'contract_until': 2029,
        'bio': 'A world-class ball-carrier who excels at transitioning play from defense to attack. He is one of the club\'s primary captains and most experienced midfielders.'
    },
    {
        'full_name': 'Dani Olmo',
        'jersey_number': 20,
        'position': 'AM',
        'nationality': 'Spain',
        'date_of_birth': date(1998, 5, 7),
        'height_cm': 179,
        'weight_kg': 73,
        'preferred_foot': 'R',
        'joined_year': 2024,
        'contract_until': 2030,
        'bio': 'Rejoined the club after a successful stint in Germany. A versatile attacking threat capable of playing between the lines and scoring crucial goals.'
    },
    {
        'full_name': 'Fermín López',
        'jersey_number': 16,
        'position': 'AM',
        'nationality': 'Spain',
        'date_of_birth': date(2003, 5, 11),
        'height_cm': 175,
        'weight_kg': 73,
        'preferred_foot': 'R',
        'joined_year': 2016,
        'contract_until': 2029,
        'bio': 'A late bloomer who rose to stardom following a prolific 2024 season. Noted for his off-the-ball movement and long-range shooting ability.'
    },
    {
        'full_name': 'Marc Casadó',
        'jersey_number': 17,
        'position': 'DM',
        'nationality': 'Spain',
        'date_of_birth': date(2003, 9, 14),
        'height_cm': 172,
        'weight_kg': 66,
        'preferred_foot': 'R',
        'joined_year': 2016,
        'contract_until': 2028,
        'bio': 'A disciplined tactical midfielder who specializes in defensive positioning and recycling possession. Emerged as a reliable pivot option in the first team.'
    },
    {
        'full_name': 'Marc Bernal',
        'jersey_number': 22,
        'position': 'DM',
        'nationality': 'Spain',
        'date_of_birth': date(2007, 5, 26),
        'height_cm': 191,
        'weight_kg': 87,
        'preferred_foot': 'L',
        'joined_year': 2014,
        'contract_until': 2029,
        'bio': 'A tall, physical defensive midfielder with a high ceiling. Despite an early injury setback, he is viewed as the natural heir to the holding midfield role.'
    },
    
    # Forwards
    {
        'full_name': 'Robert Lewandowski',
        'jersey_number': 9,
        'position': 'CF',
        'nationality': 'Poland',
        'date_of_birth': date(1988, 8, 21),
        'height_cm': 185,
        'weight_kg': 81,
        'preferred_foot': 'R',
        'joined_year': 2022,
        'contract_until': 2026,
        'bio': 'One of the greatest strikers of all time. His clinical finishing and elite movement continue to make him the primary goalscoring threat for the Blaugrana.'
    },
    {
        'full_name': 'Lamine Yamal',
        'jersey_number': 10,
        'position': 'W',
        'nationality': 'Spain',
        'date_of_birth': date(2007, 7, 13),
        'height_cm': 180,
        'weight_kg': 72,
        'preferred_foot': 'L',
        'joined_year': 2014,
        'contract_until': 2031,
        'bio': 'The crown jewel of La Masia. Inherited the legendary number 10 shirt after becoming the youngest player to dominate at both club and international levels.'
    },
    {
        'full_name': 'Raphinha',
        'jersey_number': 11,
        'position': 'W',
        'nationality': 'Brazil',
        'date_of_birth': date(1996, 12, 14),
        'height_cm': 176,
        'weight_kg': 72,
        'preferred_foot': 'L',
        'joined_year': 2022,
        'contract_until': 2028,
        'bio': 'A tireless worker on the wing with exceptional output in terms of goals and assists. He has grown into a leader and the club\'s fourth captain.'
    },
    {
        'full_name': 'Marcus Rashford',
        'jersey_number': 14,
        'position': 'W',
        'nationality': 'England',
        'date_of_birth': date(1997, 10, 31),
        'height_cm': 188,
        'weight_kg': 80,
        'preferred_foot': 'R',
        'joined_year': 2025,
        'contract_until': 2026,
        'bio': 'Joined on a high-profile loan from Manchester United in the summer of 2025. Known for his blistering pace and directness when cutting inside from the left.'
    },
    {
        'full_name': 'Ferran Torres',
        'jersey_number': 7,
        'position': 'W',
        'nationality': 'Spain',
        'date_of_birth': date(2000, 2, 29),
        'height_cm': 184,
        'weight_kg': 80,
        'preferred_foot': 'R',
        'joined_year': 2022,
        'contract_until': 2027,
        'bio': 'A versatile attacker capable of playing across the front three. Known for his intelligent movement off the ball and clinical finishing in the box.'
    },
    {
        'full_name': 'Roony Bardghji',
        'jersey_number': 28,
        'position': 'W',
        'nationality': 'Sweden',
        'date_of_birth': date(2005, 11, 15),
        'height_cm': 173,
        'weight_kg': 73,
        'preferred_foot': 'L',
        'joined_year': 2025,
        'contract_until': 2029,
        'bio': 'A Swedish prodigy signed from Copenhagen. A technical dribbler with a dangerous left foot, brought in to provide depth and competition on the wings.'
    },
]

# Clear existing players
Player.objects.all().delete()

# Create players
created_count = 0
for player_info in players_data:
    player = Player.objects.create(**player_info)
    created_count += 1
    print(f"Created: {player.full_name} (#{player.jersey_number})")

print(f"\n✓ Successfully created {created_count} players!")

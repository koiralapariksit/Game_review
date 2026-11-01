import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')
django.setup()

from django.contrib.auth.models import User
from transfers.models import Transfer
from players.models import Player

# Ensure admin user
admin_user, _ = User.objects.get_or_create(
    username="culer_admin",
    defaults={
        "email": "admin@fcbarcelona.com",
        "is_staff": True,
        "is_superuser": True
    }
)

with open('transfers_2026_2027.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Clear existing transfers
print(f"Clearing previous transfers ({Transfer.objects.count()} existing)...")
Transfer.objects.all().delete()

# Map player image if present in Player table
player_images = {p.full_name: p.profile_image for p in Player.objects.all() if p.profile_image}

print("Populating 10 Arrivals (Confirmed)...")
for item in data['arrivals']:
    date_obj = datetime.strptime(item['date_completed'], "%Y-%m-%d").date()
    p_name = item['player']
    img = player_images.get(p_name, "")
    
    desc = (
        f"Position: {item.get('position', 'N/A')}\n"
        f"Age: {item.get('age', 'N/A')}\n"
        f"Transfer Type: {item.get('transfer_type', 'N/A')}\n"
        f"Assigned Jersey: #{item.get('assigned_jersey', 'N/A')}\n"
        f"Fee: {item.get('fee', 'N/A')}"
    )
    
    t = Transfer.objects.create(
        player_name=p_name,
        from_club=item['from_club'],
        to_club="FC Barcelona",
        transfer_type='CONFIRMED',
        transfer_date=date_obj,
        fee=item.get('fee', ''),
        image_url=img,
        description=desc,
        posted_by=admin_user
    )
    print(f"Added Arrival: {p_name} from {item['from_club']} ({item.get('fee')})")

print("\nPopulating 13 Departures (Confirmed / Outgoing)...")
for item in data['departures']:
    date_obj = datetime.strptime(item['date_completed'], "%Y-%m-%d").date()
    p_name = item['player']
    
    desc = (
        f"Transfer Type: {item.get('transfer_type', 'N/A')}\n"
        f"Fee: {item.get('fee', 'N/A')}\n"
        f"Completed: {item['date_completed']}"
    )
    
    t = Transfer.objects.create(
        player_name=p_name,
        from_club="FC Barcelona",
        to_club=item['to_club'],
        transfer_type='CONFIRMED',
        transfer_date=date_obj,
        fee=item.get('fee', ''),
        description=desc,
        posted_by=admin_user
    )
    print(f"Added Departure: {p_name} to {item['to_club']} ({item.get('fee')})")

print(f"\nSuccessfully populated {Transfer.objects.count()} total transfers for Summer 2026 window!")


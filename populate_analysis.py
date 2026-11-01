import os
import django
import json
from datetime import datetime
from django.utils import timezone
from django.utils.text import slugify

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')
django.setup()

from django.contrib.auth.models import User
from analysis.models import Article

# Ensure admin user
admin_user, _ = User.objects.get_or_create(
    username="culer_admin",
    defaults={
        "email": "admin@fcbarcelona.com",
        "is_staff": True,
        "is_superuser": True
    }
)

with open('analysis_2026_2027.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Clear existing analysis articles
print(f"Clearing previous articles ({Article.objects.count()} existing)...")
Article.objects.all().delete()

print("Populating 14 Tactical Analyses for Competitive Matches...")
for item in data['competitive_game_analyses']:
    title = f"Tactical Breakdown: {item['fixture']} ({item['competition']})"
    slug = slugify(f"tactical-{item['match_id']}-{item['fixture']}")
    
    # Format metrics block
    metrics_str = "\n".join([f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in item['key_metrics'].items()])
    
    content = (
        f"## Match Overview\n\n"
        f"- **Date:** {item['date']}\n"
        f"- **Competition:** {item['competition']}\n"
        f"- **Formation Used:** {item['formation_used']}\n"
        f"- **Man of the Match:** {item['man_of_the_match']}\n\n"
        f"### Key Tactical Metrics\n\n"
        f"{metrics_str}\n\n"
        f"### Tactical Analysis\n\n"
        f"{item['tactical_analysis']}"
    )

    pub_date = datetime.strptime(item['date'] + " 22:00:00", "%Y-%m-%d %H:%M:%S")
    pub_date = timezone.make_aware(pub_date)

    art = Article.objects.create(
        title=title,
        slug=slug,
        author=admin_user,
        content=content,
        article_type='tactical_analysis',
        published_at=pub_date
    )
    print(f"Created Tactical Analysis #{item['match_id']}: {item['fixture']}")

print("\nPopulating 5 Pre-season Tactical Opinions & Reviews...")
for idx, item in enumerate(data['preseason_analyses_summary'], 1):
    title = f"Pre-season Review: {item['fixture']}"
    slug = slugify(f"preseason-review-{idx}")
    
    content = (
        f"## Pre-season Tactical Observations\n\n"
        f"**Fixture:** {item['fixture']}\n\n"
        f"### Observations\n\n"
        f"{item['analysis']}"
    )

    pub_date = timezone.now()

    art = Article.objects.create(
        title=title,
        slug=slug,
        author=admin_user,
        content=content,
        article_type='opinion',
        published_at=pub_date
    )
    print(f"Created Pre-season Review #{idx}: {item['fixture']}")

print(f"\nSuccessfully populated {Article.objects.count()} total articles in analysis app!")


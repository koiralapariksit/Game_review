from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q, Sum

from matches.models import Match, Competition, Team
from analysis.models import Article
from players.models import Player, PlayerSeasonStatistic
from transfers.models import Transfer
from community.models import CommunityPost
from analysis.services.metrics import compute_match_metrics, compute_team_form


def home(request):
    """
    Renders the 9-Section Intelligence Homepage using real database queries
    with N+1 query optimization and graceful empty states.
    """
    now = timezone.now()

    # SECTION 1 — Match Hero: Latest finished match (or next scheduled fixture if none finished)
    latest_finished_match = Match.objects.select_related(
        'competition', 'home_team', 'away_team', 'statistic'
    ).prefetch_related('events').filter(
        status=Match.STATUS_FINISHED,
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-match_date').first()

    next_scheduled_match = None
    if not latest_finished_match:
        next_scheduled_match = Match.objects.select_related(
            'competition', 'home_team', 'away_team', 'statistic'
        ).filter(
            Q(status=Match.STATUS_SCHEDULED) | Q(match_date__gte=now)
        ).order_by('match_date').first()

    hero_match = latest_finished_match or next_scheduled_match

    # SECTION 2 — Latest Match Analysis
    # Get the latest published match review article (ideally for hero match or most recent)
    latest_match_article = None
    hero_metrics = None
    if hero_match:
        latest_match_article = Article.objects.filter(
            match=hero_match,
            status=Article.STATUS_PUBLISHED
        ).select_related('match', 'player', 'author').first()
        try:
            hero_metrics = compute_match_metrics(hero_match.id)
        except Exception:
            hero_metrics = None

    if not latest_match_article:
        latest_match_article = Article.objects.filter(
            category=Article.CATEGORY_MATCH_REVIEW,
            status=Article.STATUS_PUBLISHED
        ).select_related('match', 'player', 'author', 'match__home_team', 'match__away_team', 'match__statistic').first()

    # SECTION 3 — Latest News & Editorial (4 articles)
    recent_articles = Article.objects.filter(
        status=Article.STATUS_PUBLISHED
    ).select_related('author', 'match', 'player').order_by('-published_at', '-created_at')[:4]

    # SECTION 4 — Player Spotlight (A standout first-team player)
    featured_player = Player.objects.prefetch_related(
        'season_statistics', 'match_performances'
    ).filter(
        profile_image__isnull=False
    ).order_by('jersey_number').first() or Player.objects.prefetch_related(
        'season_statistics', 'match_performances'
    ).order_by('jersey_number').first()

    player_stats_summary = None
    if featured_player:
        stats = featured_player.season_statistics.all()
        if stats.exists():
            player_stats_summary = {
                'appearances': sum(s.appearances for s in stats),
                'goals': sum(s.goals for s in stats),
                'assists': sum(s.assists for s in stats),
                'minutes_played': sum(s.minutes_played for s in stats),
            }

    # SECTION 5 — Tactical Intelligence (Highlight articles)
    tactical_articles = Article.objects.filter(
        category=Article.CATEGORY_TACTICAL_ANALYSIS,
        status=Article.STATUS_PUBLISHED
    ).select_related('author', 'match', 'player').order_by('-published_at', '-created_at')[:3]

    # SECTION 6 — Upcoming Fixtures (Next 5 matches)
    upcoming_fixtures = Match.objects.select_related(
        'competition', 'home_team', 'away_team'
    ).filter(
        Q(status=Match.STATUS_SCHEDULED) | Q(match_date__gte=now)
    ).order_by('match_date')[:5]

    # SECTION 7 — Transfer Intelligence (Confirmed vs Rumors)
    confirmed_transfers = Transfer.objects.select_related('posted_by').filter(
        transfer_type='CONFIRMED'
    ).order_by('-transfer_date', '-created_at')[:3]

    transfer_rumors = Transfer.objects.select_related('posted_by').filter(
        transfer_type='RUMOR'
    ).order_by('reliability_tier', '-transfer_date')[:4]

    # SECTION 8 — Community Pulse (Top recent discussion threads)
    community_posts = CommunityPost.objects.filter(
        is_published=True
    ).select_related('author').prefetch_related('comments').order_by('-created_at')[:4]

    # SECTION 9 — Verified Season Statistics
    team_form = compute_team_form(limit=5)
    
    # Top scorers from PlayerSeasonStatistic
    top_scorers = PlayerSeasonStatistic.objects.select_related('player').filter(
        goals__gt=0
    ).order_by('-goals')[:5]

    context = {
        'hero_match': hero_match,
        'hero_metrics': hero_metrics,
        'latest_match_article': latest_match_article,
        'recent_articles': recent_articles,
        'featured_player': featured_player,
        'player_stats_summary': player_stats_summary,
        'tactical_articles': tactical_articles,
        'upcoming_fixtures': upcoming_fixtures,
        'confirmed_transfers': confirmed_transfers,
        'transfer_rumors': transfer_rumors,
        'community_posts': community_posts,
        'team_form': team_form,
        'top_scorers': top_scorers,
        'last_synced_at': now,
    }

    return render(request, 'camp/home.html', context)


def media(request):
    return render(request, 'camp/media.html')

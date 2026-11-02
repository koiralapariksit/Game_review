from django.shortcuts import render
from django.db import connection
from django.db.models import Q

from matches.models import Match
from players.models import Player
from analysis.models import Article
from transfers.models import Transfer


def global_search_view(request):
    """
    Central search and discovery view.
    Searches across Matches, Players, published Articles, and Transfers.
    Uses PostgreSQL SearchVector when available, with an automatic Q() fallback for SQLite.
    """
    query = request.GET.get('q', '').strip()

    matches = []
    players = []
    articles = []
    transfers = []

    if query:
        is_postgres = connection.vendor == 'postgresql'

        if is_postgres:
            try:
                from django.contrib.postgres.search import SearchVector
                articles = Article.objects.annotate(
                    search=SearchVector('title', 'subtitle', 'content')
                ).filter(search=query, status=Article.STATUS_PUBLISHED).select_related('match', 'player', 'author')[:10]
            except Exception:
                articles = Article.objects.filter(
                    Q(title__icontains=query) | Q(subtitle__icontains=query) | Q(content__icontains=query),
                    status=Article.STATUS_PUBLISHED
                ).select_related('match', 'player', 'author')[:10]
        else:
            articles = Article.objects.filter(
                Q(title__icontains=query) | Q(subtitle__icontains=query) | Q(content__icontains=query),
                status=Article.STATUS_PUBLISHED
            ).select_related('match', 'player', 'author')[:10]

        matches = Match.objects.filter(
            Q(home_team__name__icontains=query) |
            Q(home_team__short_name__icontains=query) |
            Q(away_team__name__icontains=query) |
            Q(away_team__short_name__icontains=query) |
            Q(competition__name__icontains=query) |
            Q(venue__icontains=query)
        ).select_related('competition', 'home_team', 'away_team', 'statistic')[:10]

        players = Player.objects.filter(
            Q(full_name__icontains=query) |
            Q(nickname__icontains=query) |
            Q(nationality__icontains=query) |
            Q(position__icontains=query)
        ).prefetch_related('season_statistics')[:10]

        transfers = Transfer.objects.filter(
            Q(player_name__icontains=query) |
            Q(from_club__icontains=query) |
            Q(to_club__icontains=query)
        ).select_related('posted_by')[:10]

    total_results = len(matches) + len(players) + len(articles) + len(transfers)

    context = {
        'query': query,
        'matches': matches,
        'players': players,
        'articles': articles,
        'transfers': transfers,
        'total_results': total_results,
    }

    return render(request, 'search/search_results.html', context)

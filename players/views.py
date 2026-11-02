from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Player


def player_list(request):
    """Display all first-team players with optimized performance prefetching and HTMX position filtering"""
    position_filter = request.GET.get('position', '').upper().strip()
    
    players_qs = Player.objects.prefetch_related('season_statistics', 'match_performances').all().order_by('jersey_number')
    
    if position_filter:
        if position_filter == 'DF':
            players_qs = players_qs.filter(position__in=['CB', 'RB', 'LB'])
        elif position_filter == 'MF':
            players_qs = players_qs.filter(position__in=['CM', 'DM', 'AM'])
        elif position_filter == 'FW':
            players_qs = players_qs.filter(position__in=['CF', 'W'])
        else:
            players_qs = players_qs.filter(position=position_filter)

    players = list(players_qs)

    gk_players = [p for p in players if p.position == 'GK']
    cb_players = [p for p in players if p.position == 'CB']
    rb_players = [p for p in players if p.position == 'RB']
    lb_players = [p for p in players if p.position == 'LB']
    def_players = cb_players + rb_players + lb_players
    
    cm_players = [p for p in players if p.position == 'CM']
    dm_players = [p for p in players if p.position == 'DM']
    am_players = [p for p in players if p.position == 'AM']
    mid_players = cm_players + dm_players + am_players
    
    cf_players = [p for p in players if p.position == 'CF']
    w_players = [p for p in players if p.position == 'W']
    fwd_players = cf_players + w_players
    
    context = {
        'players': players,
        'position_filter': position_filter,
        'gk_players': gk_players,
        'gk_count': len(gk_players),
        'def_players': def_players,
        'def_count': len(def_players),
        'mid_players': mid_players,
        'mid_count': len(mid_players),
        'fwd_players': fwd_players,
        'fwd_count': len(fwd_players),
    }

    if request.headers.get('HX-Request') or request.META.get('HTTP_HX_REQUEST') == 'true':
        return render(request, 'players/partials/player_grid.html', context)

    return render(request, 'players/player_list.html', context)


def player_detail(request, player_id):
    """Display detailed player intelligence profile with pre-fetched performances and linked AI reports"""
    player = get_object_or_404(
        Player.objects.prefetch_related(
            'season_statistics',
            'match_performances__match__home_team',
            'match_performances__match__away_team',
            'match_performances__match__competition'
        ),
        pk=player_id
    )
    
    recent_performances = player.match_performances.all().order_by('-match__match_date')[:10]
    season_stats = player.season_statistics.all().order_by('-season')

    # Linked AI Player Intelligence Report
    latest_player_report = player.analysis_articles.filter(
        status='PUBLISHED'
    ).select_related('author').first()
    
    context = {
        'player': player,
        'recent_performances': recent_performances,
        'season_stats': season_stats,
        'latest_player_report': latest_player_report,
    }
    return render(request, 'players/player_detail.html', context)

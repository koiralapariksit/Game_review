from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Player


def player_list(request):
    """Display all first-team players with optimized performance and season statistic prefetching"""
    players = Player.objects.prefetch_related('season_statistics', 'match_performances').all().order_by('jersey_number')
    
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
        'gk_players': gk_players,
        'gk_count': len(gk_players),
        'def_players': def_players,
        'def_count': len(def_players),
        'mid_players': mid_players,
        'mid_count': len(mid_players),
        'fwd_players': fwd_players,
        'fwd_count': len(fwd_players),
    }
    return render(request, 'players/player_list.html', context)


def player_detail(request, player_id):
    """Display detailed player intelligence profile with pre-fetched performances"""
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
    
    context = {
        'player': player,
        'recent_performances': recent_performances,
        'season_stats': season_stats,
    }
    return render(request, 'players/player_detail.html', context)

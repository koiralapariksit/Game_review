from django.shortcuts import render, get_object_or_404
from .models import Player

def player_list(request):
    """Display all players grouped by position"""
    gk_players = Player.objects.filter(position='GK').order_by('jersey_number')
    cb_players = Player.objects.filter(position='CB').order_by('jersey_number')
    rb_players = Player.objects.filter(position='RB').order_by('jersey_number')
    lb_players = Player.objects.filter(position='LB').order_by('jersey_number')
    def_players = list(cb_players) + list(rb_players) + list(lb_players)
    
    cm_players = Player.objects.filter(position='CM').order_by('jersey_number')
    dm_players = Player.objects.filter(position='DM').order_by('jersey_number')
    am_players = Player.objects.filter(position='AM').order_by('jersey_number')
    mid_players = list(cm_players) + list(dm_players) + list(am_players)
    
    cf_players = Player.objects.filter(position='CF').order_by('jersey_number')
    w_players = Player.objects.filter(position='W').order_by('jersey_number')
    fwd_players = list(cf_players) + list(w_players)
    
    context = {
        'players': Player.objects.all(),
        'gk_players': gk_players,
        'gk_count': gk_players.count(),
        'def_players': def_players,
        'def_count': len(def_players),
        'mid_players': mid_players,
        'mid_count': len(mid_players),
        'fwd_players': fwd_players,
        'fwd_count': len(fwd_players),
    }
    return render(request, 'players/player_list.html', context)

def player_detail(request, player_id):
    """Display detailed information for a specific player"""
    player = get_object_or_404(Player, pk=player_id)
    
    context = {
        'player': player,
    }
    return render(request, 'players/player_detail.html', context)

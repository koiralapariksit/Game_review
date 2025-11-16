from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Player

def player_list(request):
    """Display all players with pagination"""
    players = Player.objects.all()
    
    # Add pagination
    paginator = Paginator(players, 12)  # Show 12 players per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'players': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'players/player_list.html', context)

def player_detail(request, player_id):
    """Display detailed information for a specific player"""
    player = get_object_or_404(Player, pk=player_id)
    
    context = {
        'player': player,
    }
    return render(request, 'players/player_detail.html', context)

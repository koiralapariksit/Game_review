from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django_ratelimit.decorators import ratelimit

from community.models import CommunityPost, Comment as CommunityComment
from matches.models import Match, Comment as MatchComment
from players.models import Player
from transfers.models import Transfer


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def admin_login(request):
    """Rate-limited login view strictly for staff members."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('customadmin:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                next_url = request.GET.get('next') or 'customadmin:dashboard'
                return redirect(next_url)
            else:
                messages.error(request, 'Access denied: Staff privileges required.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm(request)

    return render(request, 'customadmin/login.html', {'form': form})


def admin_logout(request):
    """Staff logout view."""
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('customadmin:login')


@staff_member_required(login_url='customadmin:login')
def admin_dashboard(request):
    """Staff dashboard protected by @staff_member_required."""
    total_posts = CommunityPost.objects.count()
    total_comments = CommunityComment.objects.count() + MatchComment.objects.count()
    total_matches = Match.objects.count()
    total_players = Player.objects.count()
    total_transfers = Transfer.objects.count()

    recent_posts = CommunityPost.objects.select_related('author').order_by('-created_at')[:5]
    recent_comments = CommunityComment.objects.select_related('author', 'post').order_by('-created_at')[:5]

    context = {
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_matches': total_matches,
        'total_players': total_players,
        'total_transfers': total_transfers,
        'recent_posts': recent_posts,
        'recent_comments': recent_comments,
        'user': request.user,
    }
    return render(request, 'customadmin/dashboard.html', context)

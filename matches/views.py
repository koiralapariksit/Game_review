from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Match, Comment


def match_list(request):
    """Display all matches, newest first"""
    matches = Match.objects.select_related('posted_by').all()
    
    # Optional filtering by competition
    competition_filter = request.GET.get('competition')
    if competition_filter:
        matches = matches.filter(competition=competition_filter)
    
    # Optional search functionality
    search_query = request.GET.get('search')
    if search_query:
        matches = matches.filter(
            Q(opponent__icontains=search_query) |
            Q(summary__icontains=search_query) |
            Q(competition__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(matches, 10)  # Show 10 matches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all competitions for filter dropdown
    competitions = Match.COMPETITION_CHOICES
    
    context = {
        'page_obj': page_obj,
        'competitions': competitions,
        'current_competition': competition_filter,
        'search_query': search_query,
        'total_matches': matches.count(),
    }
    
    return render(request, 'matches/match_list.html', context)


def match_detail(request, match_id):
    """Display detailed match information"""
    match = get_object_or_404(
        Match.objects.select_related('posted_by'), 
        pk=match_id
    )
    
    # Get approved comments for this match
    comments = Comment.objects.filter(
        match=match,
        is_approved=True
    ).order_by('-created_at')
    
    # Get related matches (same opponent, excluding current match)
    related_matches = Match.objects.filter(
        opponent=match.opponent
    ).exclude(pk=match.pk).order_by('-date')[:3]
    
    context = {
        'match': match,
        'comments': comments,
        'related_matches': related_matches,
    }
    
    return render(request, 'matches/match_detail.html', context)


def post_comment(request, match_id):
    """Handle comment posting for a specific match"""
    match = get_object_or_404(Match, pk=match_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        comment_text = request.POST.get('comment', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Basic validation
        if not name or not comment_text:
            messages.error(request, 'Please fill in both your name and comment.')
            return render(request, 'matches/post_comment.html', {
                'match': match,
                'form_data': {
                    'name': name,
                    'comment': comment_text,
                    'email': email
                }
            })
        
        if len(name) < 2:
            messages.error(request, 'Please enter a name with at least 2 characters.')
            return render(request, 'matches/post_comment.html', {
                'match': match,
                'form_data': {
                    'name': name,
                    'comment': comment_text,
                    'email': email
                }
            })
        
        if len(comment_text) < 10:
            messages.error(request, 'Please write a comment with at least 10 characters.')
            return render(request, 'matches/post_comment.html', {
                'match': match,
                'form_data': {
                    'name': name,
                    'comment': comment_text,
                    'email': email
                }
            })
        
        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Create the comment
        try:
            comment = Comment.objects.create(
                match=match,
                name=name,
                comment=comment_text,
                email=email if email else None,
                ip_address=ip_address,
                is_approved=True  # Auto-approve for now, change to False if you want moderation
            )
            
            messages.success(request, 'Your comment has been posted successfully!')
            return HttpResponseRedirect(reverse('matches:match_detail', kwargs={'match_id': match.pk}) + f'#comment-{comment.pk}')
            
        except Exception as e:
            messages.error(request, 'There was an error posting your comment. Please try again.')
            return render(request, 'matches/post_comment.html', {
                'match': match,
                'form_data': {
                    'name': name,
                    'comment': comment_text,
                    'email': email
                }
            })
    
    # GET request - show the comment form
    context = {
        'match': match,
    }
    
    return render(request, 'matches/post_comment.html', context)


def upcoming_matches(request):
    """Display upcoming matches (no result or future dates)"""
    upcoming = Match.objects.select_related('posted_by').filter(
        Q(result__isnull=True) | Q(result__exact='') | Q(date__gt=timezone.now())
    ).order_by('date')
    
    # Optional filtering by competition
    competition_filter = request.GET.get('competition')
    if competition_filter:
        upcoming = upcoming.filter(competition=competition_filter)
    
    # Pagination
    paginator = Paginator(upcoming, 8)  # Show 8 upcoming matches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all competitions for filter dropdown
    competitions = Match.COMPETITION_CHOICES
    
    context = {
        'page_obj': page_obj,
        'competitions': competitions,
        'current_competition': competition_filter,
        'total_upcoming': upcoming.count(),
    }
    
    return render(request, 'matches/upcoming_matches.html', context)


def completed_matches(request):
    """Display completed matches with results"""
    completed = Match.objects.select_related('posted_by').filter(
        result__isnull=False,
        date__lte=timezone.now()
    ).exclude(result__exact='').order_by('-date')
    
    # Optional filtering by competition
    competition_filter = request.GET.get('competition')
    if competition_filter:
        completed = completed.filter(competition=competition_filter)
    
    # Pagination
    paginator = Paginator(completed, 10)  # Show 10 completed matches per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all competitions for filter dropdown
    competitions = Match.COMPETITION_CHOICES
    
    context = {
        'page_obj': page_obj,
        'competitions': competitions,
        'current_competition': competition_filter,
        'total_completed': completed.count(),
    }
    
    return render(request, 'matches/completed_matches.html', context)
# community/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, Http404
from django_ratelimit.decorators import ratelimit

from .models import CommunityPost, Comment, Reaction, ContentReport
from .forms import CommunityPostForm, CommentForm
from culer.sanitizers import sanitize_plain_text


def _get_post_reactions_dict(post, user=None):
    """Helper to compute aggregated reaction counts and active user states for a post."""
    upvotes = post.reactions.filter(reaction_type=Reaction.TYPE_UPVOTE).count()
    insights = post.reactions.filter(reaction_type=Reaction.TYPE_TACTICAL_INSIGHT).count()
    agrees = post.reactions.filter(reaction_type=Reaction.TYPE_AGREE).count()
    user_reactions = []
    if user and user.is_authenticated:
        user_reactions = list(post.reactions.filter(user=user).values_list('reaction_type', flat=True))

    return {
        'upvotes': upvotes,
        'insights': insights,
        'agrees': agrees,
        'total': upvotes + insights + agrees,
        'user_reactions': user_reactions,
    }


def post_list(request):
    """
    Display published community posts with author and reactions prefetching.
    Hides posts with moderation_status='HIDDEN'.
    Supports category filtering and keyword search.
    """
    posts = (
        CommunityPost.objects.filter(is_published=True)
        .exclude(moderation_status=CommunityPost.MODERATION_STATUS_HIDDEN)
        .select_related('author', 'related_match', 'related_player')
        .prefetch_related('comments__author', 'reactions')
    )

    # Category filter
    category = request.GET.get('category', '').strip()
    if category:
        posts = posts.filter(category=category)

    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(author__username__icontains=search_query)
        )
    
    # Pagination (12 posts per page)
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_category': category,
        'category_choices': CommunityPost.CATEGORY_CHOICES,
        'total_posts': posts.count(),
    }
    
    return render(request, 'community/post_list.html', context)


def post_detail(request, pk):
    """Display individual post detail with pre-fetched comments and reactions."""
    post = get_object_or_404(
        CommunityPost.objects.select_related('author', 'related_match', 'related_player')
        .prefetch_related('comments__author', 'reactions'),
        pk=pk,
        is_published=True
    )

    # Strictly hide HIDDEN posts from public viewing unless staff
    if post.moderation_status == CommunityPost.MODERATION_STATUS_HIDDEN:
        if not (request.user.is_authenticated and request.user.is_staff):
            raise Http404("This post has been hidden by moderators.")

    # Get related posts (same author, excluding current post)
    related_posts = (
        CommunityPost.objects.filter(author=post.author, is_published=True)
        .exclude(pk=post.pk)
        .exclude(moderation_status=CommunityPost.MODERATION_STATUS_HIDDEN)
        .order_by('-created_at')[:3]
    )

    comments = post.comments.all().select_related('author').order_by('-created_at')
    comment_form = CommentForm()
    reactions = _get_post_reactions_dict(post, request.user)
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'comments': comments,
        'comment_form': comment_form,
        'reactions': reactions,
    }
    
    return render(request, 'community/post_detail.html', context)


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def post_create(request):
    """Create a new community post with rate limiting and input sanitization."""
    initial_data = {}
    if request.method == 'GET':
        if 'match_id' in request.GET:
            initial_data['related_match'] = request.GET.get('match_id')
            initial_data['category'] = CommunityPost.CATEGORY_MATCH_DISCUSSION
        if 'player_id' in request.GET:
            initial_data['related_player'] = request.GET.get('player_id')
            initial_data['category'] = CommunityPost.CATEGORY_PLAYER_DISCUSSION
        if 'category' in request.GET:
            initial_data['category'] = request.GET.get('category')

    if request.method == 'POST':
        form = CommunityPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            if request.user.is_authenticated:
                post.author = request.user
            else:
                author = User.objects.filter(is_active=True).first()
                if not author:
                    author = User.objects.create_user(username='barca_fan', email='fan@fcbarcelona.cat')
                post.author = author
            post.save()
            messages.success(request, 'Your post has been published to the supporter intelligence hub!')
            return redirect('community:post_detail', pk=post.pk)
    else:
        form = CommunityPostForm(initial=initial_data)
    
    context = {
        'form': form,
        'page_title': 'Start a New Supporter Discussion'
    }
    return render(request, 'community/post_form.html', context)


@ratelimit(key='ip', rate='15/m', method='POST', block=True)
def add_comment(request, pk):
    """Create a comment on a community post with rate limiting and sanitization."""
    post = get_object_or_404(
        CommunityPost.objects.exclude(moderation_status=CommunityPost.MODERATION_STATUS_HIDDEN),
        pk=pk,
        is_published=True
    )
    
    if post.is_locked:
        messages.error(request, 'This discussion thread has been locked by moderators. Further comments are disabled.')
        return redirect('community:post_detail', pk=post.pk)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            if request.user.is_authenticated:
                comment.author = request.user
            else:
                author = User.objects.filter(is_active=True).first()
                if not author:
                    author = User.objects.create_user(username='barca_fan', email='fan@fcbarcelona.cat')
                comment.author = author
            comment.save()
            messages.success(request, 'Comment added successfully!')
            return redirect('community:post_detail', pk=post.pk)
    
    return redirect('community:post_detail', pk=post.pk)


comment_create = add_comment


@login_required
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def toggle_reaction(request, post_id):
    """
    HTMX Endpoint: Toggles a supporter reaction (UPVOTE, TACTICAL_INSIGHT, AGREE)
    and returns an updated HTML badge snippet without full page reload.
    """
    post = get_object_or_404(
        CommunityPost.objects.exclude(moderation_status=CommunityPost.MODERATION_STATUS_HIDDEN),
        pk=post_id,
        is_published=True
    )
    
    reaction_type = request.POST.get('reaction_type', Reaction.TYPE_UPVOTE)
    valid_types = [Reaction.TYPE_UPVOTE, Reaction.TYPE_TACTICAL_INSIGHT, Reaction.TYPE_AGREE]
    if reaction_type not in valid_types:
        reaction_type = Reaction.TYPE_UPVOTE

    existing_reaction = Reaction.objects.filter(
        post=post,
        user=request.user,
        reaction_type=reaction_type
    ).first()

    if existing_reaction:
        existing_reaction.delete()
    else:
        Reaction.objects.create(
            post=post,
            user=request.user,
            reaction_type=reaction_type
        )

    reactions = _get_post_reactions_dict(post, request.user)

    if request.headers.get('HX-Request') or 'hx-request' in request.headers:
        return render(request, 'community/partials/reaction_badges.html', {
            'post': post,
            'reactions': reactions
        })

    return render(request, 'community/partials/reaction_badges.html', {
        'post': post,
        'reactions': reactions
    })


@login_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def report_content(request, post_id):
    """
    Supporter report endpoint for flagging spam/abuse.
    If a post receives 3+ unresolved reports, it automatically transitions to FLAGGED.
    """
    post = get_object_or_404(CommunityPost, pk=post_id)
    
    reason = request.POST.get('reason', ContentReport.REASON_SPAM)
    valid_reasons = [choice[0] for choice in ContentReport.REASON_CHOICES]
    if reason not in valid_reasons:
        reason = ContentReport.REASON_SPAM

    details = sanitize_plain_text(request.POST.get('details', '').strip())

    ContentReport.objects.create(
        post=post,
        reported_by=request.user,
        reason=reason,
        details=details
    )

    # Check unresolved reports threshold
    unresolved_count = post.reports.filter(resolved=False).count()
    if unresolved_count >= 3 and post.moderation_status != CommunityPost.MODERATION_STATUS_HIDDEN:
        post.moderation_status = CommunityPost.MODERATION_STATUS_FLAGGED
        post.save(update_fields=['moderation_status'])

    if request.headers.get('HX-Request') or 'hx-request' in request.headers:
        return HttpResponse(
            f'<div class="alert alert-warning" style="font-size: 0.85rem; padding: 0.5rem 0.75rem; margin-top: 0.5rem; border-radius: var(--radius-sm);">'
            f'<i class="fa-solid fa-flag"></i> Thank you. Your report has been submitted for moderation review.'
            f'</div>'
        )

    messages.info(request, 'Thank you. Your report has been submitted to the moderation team.')
    return redirect('community:post_detail', pk=post.pk)

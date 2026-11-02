# community/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.models import User
from django_ratelimit.decorators import ratelimit

from .models import CommunityPost, Comment
from .forms import CommunityPostForm, CommentForm


def post_list(request):
    """Display all published community posts with author prefetching and pagination"""
    posts = CommunityPost.objects.filter(is_published=True).select_related('author').prefetch_related('comments__author')
    
    # Search functionality
    search_query = request.GET.get('search', '')
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
        'total_posts': posts.count(),
    }
    
    return render(request, 'community/post_list.html', context)


def post_detail(request, pk):
    """Display individual post detail with pre-fetched comments and authors"""
    post = get_object_or_404(
        CommunityPost.objects.select_related('author').prefetch_related('comments__author'),
        pk=pk,
        is_published=True
    )
    
    # Get related posts (same author, excluding current post)
    related_posts = CommunityPost.objects.filter(
        author=post.author,
        is_published=True
    ).exclude(pk=post.pk).order_by('-created_at')[:3]

    comments = post.comments.all().select_related('author').order_by('-created_at')
    comment_form = CommentForm()
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'comments': comments,
        'comment_form': comment_form,
    }
    
    return render(request, 'community/post_detail.html', context)


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def post_create(request):
    """Create a new community post with rate limiting and input sanitization."""
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
            messages.success(request, 'Your post has been published to the community!')
            return redirect('community:post_detail', pk=post.pk)
    else:
        form = CommunityPostForm()
    
    context = {
        'form': form,
        'page_title': 'Start a New Discussion'
    }
    return render(request, 'community/post_form.html', context)


@ratelimit(key='ip', rate='15/m', method='POST', block=True)
def add_comment(request, pk):
    """Create a comment on a community post with rate limiting and sanitization."""
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    
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


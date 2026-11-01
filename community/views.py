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
    """Display all published community posts with pagination and search"""
    posts = CommunityPost.objects.filter(is_published=True).select_related('author')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(author__username__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(posts, 6)  # 6 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_posts': posts.count(),
    }
    
    return render(request, 'community/post_list.html', context)


def post_detail(request, pk):
    """Display individual post detail with comments"""
    post = get_object_or_404(
        CommunityPost.objects.select_related('author'),
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
            messages.success(request, 'Post created successfully!')
            return redirect('community:post_detail', pk=post.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CommunityPostForm()

    return render(request, 'community/post_form.html', {
        'form': form,
        'title': 'Create New Post'
    })


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def add_comment(request, pk):
    """Submit a comment on a community post with rate limiting and input sanitization."""
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            if request.user.is_authenticated:
                comment.author = request.user
                if not comment.name:
                    comment.name = request.user.username
            comment.save()
            messages.success(request, 'Comment added successfully!')
        else:
            messages.error(request, 'Please correct the errors in your comment.')
    return redirect('community:post_detail', pk=post.pk)

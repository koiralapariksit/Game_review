# community/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import CommunityPost


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
    """Display individual post detail"""
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
    
    context = {
        'post': post,
        'related_posts': related_posts,
    }
    
    return render(request, 'community/post_detail.html', context)
# analysis/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Article


def article_list(request):
    """Display all published articles with optimized relations and pagination"""
    articles = Article.objects.filter(
        status=Article.STATUS_PUBLISHED
    ).select_related('match', 'player', 'author', 'match__home_team', 'match__away_team', 'match__competition')
    
    search_query = request.GET.get('search')
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(subtitle__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    paginator = Paginator(articles, 12)  # 12 articles per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'page_title': 'All Analysis & Intelligence Articles'
    }
    return render(request, 'analysis/article_list.html', context)


def article_detail(request, slug):
    """Display a single article with optimized relations"""
    article = get_object_or_404(
        Article.objects.select_related(
            'match', 'player', 'author', 'match__home_team', 'match__away_team', 'match__competition', 'match__statistic'
        ).prefetch_related('match__events'),
        slug=slug,
        status=Article.STATUS_PUBLISHED
    )
    
    # Get related articles (same category or match, excluding current)
    related_articles = Article.objects.filter(
        category=article.category,
        status=Article.STATUS_PUBLISHED
    ).select_related('match', 'player', 'author').exclude(id=article.id)[:3]
    
    context = {
        'article': article,
        'related_articles': related_articles,
        'page_title': article.title
    }
    return render(request, 'analysis/article_detail.html', context)


def tactical_analysis_list(request):
    """Display only tactical analysis articles"""
    articles = Article.objects.filter(
        category=Article.CATEGORY_TACTICAL_ANALYSIS,
        status=Article.STATUS_PUBLISHED
    ).select_related('match', 'player', 'author', 'match__home_team', 'match__away_team')
    
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'Tactical Analysis',
        'article_type': 'tactical_analysis'
    }
    return render(request, 'analysis/tactical_analysis_list.html', context)


def opinion_list(request):
    """Display only opinion and editorial articles"""
    articles = Article.objects.filter(
        category__in=[Article.CATEGORY_OPINION, Article.CATEGORY_NEWS],
        status=Article.STATUS_PUBLISHED
    ).select_related('match', 'player', 'author')
    
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'Editorial & Opinions',
        'article_type': 'opinion'
    }
    return render(request, 'analysis/opinion_list.html', context)

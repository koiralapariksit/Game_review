
# analysis/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Article


def article_list(request):
    """Display all articles with pagination"""
    articles = Article.objects.all()
    paginator = Paginator(articles, 6)  # Show 6 articles per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'All Analysis Articles'
    }
    return render(request, 'analysis/article_list.html', context)


def article_detail(request, slug):
    """Display a single article"""
    article = get_object_or_404(Article, slug=slug)
    
    # Get related articles (same type, excluding current)
    related_articles = Article.objects.filter(
        article_type=article.article_type
    ).exclude(id=article.id)[:3]
    
    context = {
        'article': article,
        'related_articles': related_articles,
        'page_title': article.title
    }
    return render(request, 'analysis/article_detail.html', context)


def tactical_analysis_list(request):
    """Display only tactical analysis articles"""
    articles = Article.objects.filter(article_type='tactical_analysis')
    paginator = Paginator(articles, 6)
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'Tactical Analysis',
        'article_type': 'tactical_analysis'
    }
    return render(request, 'analysis/tactical_analysis_list.html', context)


def opinion_list(request):
    """Display only opinion articles"""
    articles = Article.objects.filter(article_type='opinion')
    paginator = Paginator(articles, 6)
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'Fan Opinions',
        'article_type': 'opinion'
    }
    return render(request, 'analysis/opinion_list.html', context)


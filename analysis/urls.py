# analysis/urls.py
from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.article_list, name='article_list'),
    path('tactics/', views.tactical_analysis_list, name='tactical_analysis_list'),
    path('opinions/', views.opinion_list, name='opinion_list'),
    path('<slug:slug>/', views.article_detail, name='article_detail'),
]

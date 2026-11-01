"""
URL configuration for culer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('camp.urls')),         # Homepage, countdown, highlights, etc.
    path('matches/', include('matches.urls')),  # Match reviews, fixtures
    path('players/', include('players.urls')),  # Player profiles
    path('transfers/', include('transfers.urls')),  # Transfer rumors
    path('analysis/', include('analysis.urls')),    # Tactical analysis, blogs
    path('community/', include('community.urls')),  # Polls, comments, quizzes
    path('about/', include('about.urls')),          # Club info, history, etc.
    path('customadmin/', include('customadmin.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

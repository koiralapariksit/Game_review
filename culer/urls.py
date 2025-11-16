"""
URL configuration for culer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
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
    # path('customadmin/', include('customadmin.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

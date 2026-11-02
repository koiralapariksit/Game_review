from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

from .search_views import global_search_view
from .sitemaps import PublishedArticleSitemap, MatchSitemap, PlayerSitemap, StaticViewSitemap

sitemaps = {
    'articles': PublishedArticleSitemap,
    'matches': MatchSitemap,
    'players': PlayerSitemap,
    'static': StaticViewSitemap,
}


def robots_txt(request):
    """Generates dynamic robots.txt pointing to sitemap."""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /customadmin/",
        "Allow: /",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('search/', global_search_view, name='global_search'),
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

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from matches.models import Match
from players.models import Player
from analysis.models import Article


class PublishedArticleSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Article.objects.filter(status=Article.STATUS_PUBLISHED).order_by('-published_at', '-created_at')

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at or obj.created_at


class MatchSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Match.objects.all().order_by('-match_date')

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at


class PlayerSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Player.objects.all().order_by('jersey_number')

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "hourly"

    def items(self):
        return ['camp:home', 'matches:match_list', 'players:player_list', 'analysis:article_list', 'transfers:transfer_list']

    def location(self, item):
        return reverse(item)


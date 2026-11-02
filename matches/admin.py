# matches/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Competition, Team, Match, MatchStatistic, MatchEvent, Comment


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'logo_url']
    search_fields = ['name', 'code']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'tla', 'provider_id', 'crest_url']
    search_fields = ['name', 'short_name', 'tla']
    list_filter = ['tla']


class MatchStatisticInline(admin.StackedInline):
    model = MatchStatistic
    extra = 0
    can_delete = False


class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 1


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        '__str__',
        'competition',
        'season',
        'match_date',
        'status',
        'home_score',
        'away_score',
        'venue',
        'posted_by',
        'created_at',
    ]
    list_filter = [
        'competition',
        'season',
        'status',
        'match_date',
    ]
    search_fields = [
        'home_team__name',
        'away_team__name',
        'home_team__short_name',
        'away_team__short_name',
        'venue',
        'provider_match_id',
    ]
    raw_id_fields = ['home_team', 'away_team', 'competition']
    readonly_fields = [
        'created_at',
        'updated_at',
        'match_status_display',
    ]
    inlines = [MatchStatisticInline, MatchEventInline]
    date_hierarchy = 'match_date'
    ordering = ['-match_date']

    def match_status_display(self, obj):
        if obj.status == Match.STATUS_SCHEDULED:
            return format_html('<span style="color: #2196F3; font-weight: bold;">📅 Scheduled</span>')
        elif obj.status == Match.STATUS_LIVE:
            return format_html('<span style="color: #FF9800; font-weight: bold;">🔴 Live</span>')
        elif obj.status == Match.STATUS_FINISHED:
            return format_html('<span style="color: #4CAF50; font-weight: bold;">✅ Finished</span>')
        elif obj.status == Match.STATUS_POSTPONED:
            return format_html('<span style="color: #9C27B0; font-weight: bold;">⏸ Postponed</span>')
        elif obj.status == Match.STATUS_CANCELLED:
            return format_html('<span style="color: #F44336; font-weight: bold;">❌ Cancelled</span>')
        return obj.status
    match_status_display.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not change and not obj.posted_by_id:
            obj.posted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MatchStatistic)
class MatchStatisticAdmin(admin.ModelAdmin):
    list_display = [
        'match',
        'possession_home',
        'possession_away',
        'shots_home',
        'shots_away',
        'shots_on_target_home',
        'shots_on_target_away',
        'xg_home',
        'xg_away',
        'is_verified',
    ]
    list_filter = ['is_verified']
    search_fields = ['match__home_team__name', 'match__away_team__name']
    raw_id_fields = ['match']


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ['match', 'minute', 'event_type', 'player_name', 'detail']
    list_filter = ['event_type']
    search_fields = ['player_name', 'detail', 'match__home_team__name', 'match__away_team__name']
    raw_id_fields = ['match']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_comment', 'match', 'is_approved', 'is_featured', 'created_at')
    list_filter = ('is_approved', 'is_featured', 'created_at')
    search_fields = ('name', 'comment', 'email', 'ip_address')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    actions = ['approve_comments', 'unapprove_comments', 'feature_comments', 'unfeature_comments']

    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} comment(s) approved.')
    approve_comments.short_description = 'Approve selected comments'

    def unapprove_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} comment(s) unapproved.')
    unapprove_comments.short_description = 'Unapprove selected comments'

    def feature_comments(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} comment(s) marked as featured.')
    feature_comments.short_description = 'Feature selected comments'

    def unfeature_comments(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} comment(s) unmarked as featured.')
    unfeature_comments.short_description = 'Unfeature selected comments'

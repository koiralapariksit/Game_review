# players/admin.py
from django.contrib import admin
from .models import Player, PlayerSeasonStatistic, PlayerMatchPerformance


class PlayerSeasonStatisticInline(admin.TabularInline):
    model = PlayerSeasonStatistic
    extra = 0


class PlayerMatchPerformanceInline(admin.TabularInline):
    model = PlayerMatchPerformance
    extra = 0
    raw_id_fields = ['match']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        'jersey_number',
        'full_name',
        'position',
        'nationality',
        'joined_year',
        'contract_until',
        'provider_id',
    ]
    list_filter = ['position', 'nationality', 'preferred_foot']
    search_fields = ['full_name', 'nickname', 'jersey_number', 'provider_id', 'nationality']
    list_per_page = 25
    inlines = [PlayerSeasonStatisticInline, PlayerMatchPerformanceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'nickname', 'jersey_number', 'position', 'preferred_position', 'provider_id')
        }),
        ('Personal Details', {
            'fields': ('nationality', 'date_of_birth', 'height_cm', 'weight_kg', 'preferred_foot')
        }),
        ('Career Information', {
            'fields': ('joined_year', 'contract_until')
        }),
        ('Profile & Bio', {
            'fields': ('profile_image', 'bio')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PlayerSeasonStatistic)
class PlayerSeasonStatisticAdmin(admin.ModelAdmin):
    list_display = [
        'player',
        'season',
        'competition',
        'appearances',
        'goals',
        'assists',
        'minutes_played',
        'yellow_cards',
    ]
    list_filter = ['season', 'competition']
    search_fields = ['player__full_name', 'season', 'competition']
    raw_id_fields = ['player']
    list_per_page = 30


@admin.register(PlayerMatchPerformance)
class PlayerMatchPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'player',
        'match',
        'minutes_played',
        'rating',
        'goals',
        'assists',
        'shots',
    ]
    list_filter = ['rating', 'goals', 'assists']
    search_fields = ['player__full_name', 'match__home_team__name', 'match__away_team__name']
    raw_id_fields = ['player', 'match']
    list_per_page = 30

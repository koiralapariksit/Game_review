from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Match, Comment


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        'opponent', 
        'date', 
        'competition_display', 
        'venue_display', 
        'result', 
        'match_status_display',
        'posted_by',
        'created_at'
    ]
    list_filter = [
        'competition', 
        'venue', 
        'date',
        'posted_by'
    ]
    search_fields = [
        'opponent', 
        'competition', 
        'result',
        'summary'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'match_status_display',
        'image_preview'
    ]
    fieldsets = (
        ('Match Information', {
            'fields': (
                'opponent', 
                'date', 
                'venue', 
                'competition'
            )
        }),
        ('Match Result', {
            'fields': (
                'result',
                'match_status_display'
            ),
            'description': 'Leave result blank for upcoming matches'
        }),
        ('Content', {
            'fields': (
                'summary',
                'image_url',
                'image_preview'
            )
        }),
        ('Metadata', {
            'fields': (
                'posted_by',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'date'
    ordering = ['-date']
    
    def match_status_display(self, obj):
        if obj.is_upcoming:
            return format_html(
                '<span style="color: #2196F3; font-weight: bold;">📅 Upcoming</span>'
            )
        elif obj.is_completed:
            return format_html(
                '<span style="color: #4CAF50; font-weight: bold;">✅ Completed</span>'
            )
        else:
            return format_html(
                '<span style="color: #FF9800; font-weight: bold;">🔴 Live</span>'
            )
    match_status_display.short_description = 'Status'
    
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 150px; border-radius: 8px;" />',
                obj.image_url
            )
        return "No image"
    image_preview.short_description = 'Image Preview'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.posted_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('posted_by')

    actions = ['mark_as_completed', 'mark_as_upcoming']

    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(result__isnull=True).update(result='0-0')
        self.message_user(request, f'{updated} matches marked as completed. Update results manually.')
    mark_as_completed.short_description = "Mark selected matches as completed"

    def mark_as_upcoming(self, request, queryset):
        updated = queryset.update(result=None)
        self.message_user(request, f'{updated} matches marked as upcoming.')
    mark_as_upcoming.short_description = "Mark selected matches as upcoming"


# ✅ Register Comment model with custom admin
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

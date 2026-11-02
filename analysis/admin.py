# analysis/admin.py
from django.contrib import admin
from .models import Article, ArticleRevision, AIWorkflowExecution


class ArticleRevisionInline(admin.TabularInline):
    model = ArticleRevision
    extra = 0
    readonly_fields = ['content_snapshot', 'edited_by', 'edit_summary', 'created_at']
    can_delete = False


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'is_ai_generated', 'published_at', 'author', 'created_at']
    list_filter = ['category', 'status', 'is_ai_generated', 'published_at', 'created_at']
    search_fields = ['title', 'subtitle', 'content']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    inlines = [ArticleRevisionInline]

    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'subtitle', 'slug', 'category', 'status', 'author', 'match', 'player')
        }),
        ('AI Intelligence & Disclosures', {
            'fields': ('is_ai_generated', 'ai_disclosure')
        }),
        ('Content', {
            'fields': ('content', 'image_url')
        }),
        ('Publishing', {
            'fields': ('published_at',)
        }),
    )


@admin.register(ArticleRevision)
class ArticleRevisionAdmin(admin.ModelAdmin):
    list_display = ['article', 'edited_by', 'edit_summary', 'created_at']
    list_filter = ['created_at']
    search_fields = ['article__title', 'edit_summary', 'content_snapshot']
    readonly_fields = ['created_at']


@admin.register(AIWorkflowExecution)
class AIWorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'match', 'stage', 'model_identifier',
        'prompt_tokens', 'completion_tokens', 'calculated_cost_usd',
        'created_at', 'completed_at'
    ]
    list_filter = ['stage', 'model_identifier', 'created_at']
    search_fields = ['match__home_team__name', 'match__away_team__name', 'error_message', 'model_identifier']
    readonly_fields = ['created_at', 'completed_at']

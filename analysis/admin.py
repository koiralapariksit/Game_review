
# analysis/admin.py
from django.contrib import admin
from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'article_type', 'published_at', 'author', 'updated_at']
    list_filter = ['article_type', 'published_at', 'author']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    ordering = ['-published_at']
    
    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'slug', 'author', 'article_type')
        }),
        ('Content', {
            'fields': ('content', 'image_url')
        }),
        ('Publishing', {
            'fields': ('published_at',)
        }),
    )


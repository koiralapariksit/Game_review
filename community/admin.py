# community/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import CommunityPost


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'author', 
        'is_published', 
        'created_at', 
        'updated_at',
        'image_preview'
    ]
    list_filter = [
        'is_published', 
        'created_at', 
        'author'
    ]
    search_fields = [
        'title', 
        'content', 
        'author__username'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at',
        'image_preview'
    ]
    fields = [
        'title',
        'content',
        'image',
        'image_preview',
        'author',
        'is_published',
        'created_at',
        'updated_at'
    ]
    
    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 8px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Image Preview"
    
    def save_model(self, request, obj, form, change):
        """Auto-assign current user as author if not set"""
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('author')
    
    class Media:
        css = {
            'all': ('admin/css/community_admin.css',)
        }
from django.contrib import admin
from .models import Player

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'age', 'nationality', 'created_at']
    list_filter = ['position', 'nationality', 'age']
    search_fields = ['name', 'nationality']
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'position', 'age', 'nationality')
        }),
        ('Profile', {
            'fields': ('profile_image', 'bio')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

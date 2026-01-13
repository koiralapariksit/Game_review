from django.contrib import admin
from .models import Player

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['jersey_number', 'full_name', 'position', 'nationality', 'joined_year']
    list_filter = ['position', 'nationality', 'preferred_foot']
    search_fields = ['full_name', 'nationality', 'jersey_number']
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'nickname', 'jersey_number', 'position')
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

# transfers/admin.py
from django.contrib import admin
from .models import Transfer


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    """Admin configuration for Transfer model"""
    
    list_display = [
        'player_name', 
        'from_club', 
        'to_club', 
        'transfer_type',
        'reliability_tier',
        'verification_status',
        'is_ai_generated',
        'transfer_date', 
        'fee', 
        'posted_by',
        'created_at'
    ]
    
    list_filter = [
        'transfer_type',
        'reliability_tier',
        'verification_status',
        'is_ai_generated',
        'transfer_date',
        'to_club',
        'created_at',
    ]
    
    search_fields = [
        'player_name',
        'from_club',
        'to_club',
        'source_url',
        'source',
    ]
    
    fields = [
        'player_name',
        'from_club', 
        'to_club',
        'transfer_type',
        'reliability_tier',
        'verification_status',
        'source_url',
        'is_ai_generated',
        'transfer_date',
        'fee',
        'source',
        'image_url',
        'description',
        'posted_by',
    ]
    
    list_per_page = 25
    date_hierarchy = 'transfer_date'
    list_editable = ['verification_status', 'reliability_tier']
    
    def save_model(self, request, obj, form, change):
        """Override save to set posted_by if not provided"""
        if not change and not obj.posted_by_id:
            obj.posted_by = request.user
        super().save_model(request, obj, form, change)

# transfers/admin.py
from django.contrib import admin
from .models import Transfer


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    """Admin configuration for Transfer model"""
    
    # List display configuration
    list_display = [
        'player_name', 
        'from_club', 
        'to_club', 
        'transfer_type', 
        'transfer_date', 
        'fee', 
        'posted_by',
        'created_at'
    ]
    
    # Filters in the right sidebar
    list_filter = [
        'transfer_type',
        'transfer_date',
        'to_club',
        'created_at',
    ]
    
    # Search functionality
    search_fields = [
        'player_name',
        'from_club',
        'to_club',
    ]
    
    # Fields to display in the form
    fields = [
        'player_name',
        'from_club', 
        'to_club',
        'transfer_type',
        'transfer_date',
        'fee',
        'source',
        'image_url',
        'description',
        'posted_by',
    ]
    
    # Additional configurations
    list_per_page = 25
    date_hierarchy = 'transfer_date'
    list_editable = ['transfer_type', 'fee']
    
    def save_model(self, request, obj, form, change):
        """Override save to set posted_by if not provided"""
        if not change:  # If creating new object
            obj.posted_by = request.user
        super().save_model(request, obj, form, change)
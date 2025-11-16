# transfers/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Transfer(models.Model):
    """Model representing a football transfer (rumor, confirmed, or historical)"""
    
    # Transfer type choices
    TRANSFER_TYPE_CHOICES = [
        ('RUMOR', 'Rumor'),
        ('CONFIRMED', 'Confirmed'),
        ('HISTORY', 'History'),
    ]
    
    # Basic transfer information
    player_name = models.CharField(max_length=100, help_text="Name of the player")
    from_club = models.CharField(max_length=100, help_text="Club the player is transferring from")
    to_club = models.CharField(max_length=100, default="FC Barcelona", help_text="Club the player is transferring to")
    transfer_type = models.CharField(
        max_length=10,
        choices=TRANSFER_TYPE_CHOICES,
        help_text="Type of transfer (rumor, confirmed, or history)"
    )
    
    # Transfer details
    transfer_date = models.DateField(
        blank=True, 
        null=True, 
        help_text="Date when the transfer occurred or is expected to occur"
    )
    fee = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Transfer fee (e.g., '€50M', 'Free transfer', 'Loan')"
    )
    source = models.URLField(
        blank=True, 
        null=True, 
        help_text="Source URL for the transfer news"
    )
    image_url = models.URLField(
        blank=True, 
        null=True, 
        help_text="URL to player or transfer-related image"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Additional details about the transfer"
    )
    
    # Metadata
    posted_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        help_text="User who posted this transfer information"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transfer_date', '-created_at']  # Newest transfers first
        verbose_name = "Transfer"
        verbose_name_plural = "Transfers"
    
    def __str__(self):
        """String representation of the transfer"""
        return f"{self.player_name} - {self.transfer_type}"
    
    def get_absolute_url(self):
        """Return the URL for this transfer detail page"""
        return reverse('transfers:transfer_detail', kwargs={'id': self.pk})
    
    # Properties for easy transfer type checking
    @property
    def is_confirmed(self):
        """Check if the transfer is confirmed"""
        return self.transfer_type == 'CONFIRMED'
    
    @property
    def is_rumor(self):
        """Check if the transfer is a rumor"""
        return self.transfer_type == 'RUMOR'
    
    @property
    def is_history(self):
        """Check if the transfer is historical"""
        return self.transfer_type == 'HISTORY'
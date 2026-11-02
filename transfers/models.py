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

    # Reliability Tier Choices
    RELIABILITY_TIER_CHOICES = [
        (1, 'Tier 1 - Official / Here We Go'),
        (2, 'Tier 2 - Highly Reliable'),
        (3, 'Tier 3 - Decent Reliability'),
        (4, 'Tier 4 - Unconfirmed Speculation'),
        (5, 'Tier 5 - Unreliable'),
    ]

    # Verification Status Choices
    VERIFICATION_STATUS_CHOICES = [
        ('RUMOR', 'Rumor'),
        ('RELIABLE', 'Reliable'),
        ('OFFICIAL', 'Official'),
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
    reliability_tier = models.IntegerField(
        choices=RELIABILITY_TIER_CHOICES,
        default=3,
        help_text="1 is Official/Here We Go, 5 is Unreliable"
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='RUMOR',
        help_text="Verification status: RUMOR, RELIABLE, OFFICIAL"
    )
    source_url = models.URLField(
        blank=True,
        default='',
        help_text="Source URL for the transfer news"
    )
    is_ai_generated = models.BooleanField(
        default=False,
        help_text="Whether this entry was AI generated or analyzed"
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
        help_text="Legacy source URL for the transfer news"
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
        related_name='posted_transfers',
        help_text="User who posted this transfer information"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transfer_date', '-created_at']
        verbose_name = "Transfer"
        verbose_name_plural = "Transfers"
    
    def __str__(self):
        """String representation of the transfer"""
        return f"{self.player_name} ({self.from_club} -> {self.to_club}) - {self.get_verification_status_display()}"
    
    def get_absolute_url(self):
        """Return the URL for this transfer detail page"""
        return reverse('transfers:transfer_detail', kwargs={'id': self.pk})
    
    # Properties for easy transfer type checking
    @property
    def is_confirmed(self):
        """Check if the transfer is confirmed"""
        return self.transfer_type == 'CONFIRMED' or self.verification_status == 'OFFICIAL'
    
    @property
    def is_rumor(self):
        """Check if the transfer is a rumor"""
        return self.transfer_type == 'RUMOR'
    
    @property
    def is_history(self):
        """Check if the transfer is historical"""
        return self.transfer_type == 'HISTORY'

    def save(self, *args, **kwargs):
        # Keep source and source_url in sync if one is provided
        if self.source and not self.source_url:
            self.source_url = self.source
        elif self.source_url and not self.source:
            self.source = self.source_url
        super().save(*args, **kwargs)

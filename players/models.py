# players/models.py
from django.db import models
from django.urls import reverse
from datetime import datetime

class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Goalkeeper'),
        ('CB', 'Centre-Back'),
        ('RB', 'Right-Back'),
        ('LB', 'Left-Back'),
        ('CM', 'Central Midfield'),
        ('AM', 'Attacking Midfield'),
        ('DM', 'Defensive Midfield'),
        ('W', 'Winger'),
        ('CF', 'Centre-Forward'),
    ]
    
    FOOT_CHOICES = [
        ('R', 'Right'),
        ('L', 'Left'),
        ('B', 'Both'),
    ]
    
    # Basic Info
    full_name = models.CharField(max_length=150)
    nickname = models.CharField(max_length=100, blank=True, null=True)
    jersey_number = models.PositiveIntegerField(unique=True)
    position = models.CharField(max_length=3, choices=POSITION_CHOICES)
    
    # Personal Details
    nationality = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    height_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Height in centimeters")
    weight_kg = models.PositiveIntegerField(null=True, blank=True, help_text="Weight in kilograms")
    preferred_foot = models.CharField(max_length=1, choices=FOOT_CHOICES, default='R')
    
    # Career Info
    joined_year = models.PositiveIntegerField()
    contract_until = models.PositiveIntegerField()
    
    # Media & Bio
    profile_image = models.URLField(max_length=500, blank=True, null=True, help_text="Enter image URL")
    bio = models.TextField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['jersey_number']
        verbose_name = 'Player'
        verbose_name_plural = 'Players'
    
    def __str__(self):
        return f"#{self.jersey_number} - {self.full_name} ({self.get_position_display()})"
    
    def get_absolute_url(self):
        return reverse('players:player_detail', kwargs={'player_id': self.pk})
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        today = datetime.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

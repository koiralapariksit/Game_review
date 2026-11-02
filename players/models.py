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
        ('DF', 'Defender'),
        ('CM', 'Central Midfield'),
        ('AM', 'Attacking Midfield'),
        ('DM', 'Defensive Midfield'),
        ('MF', 'Midfielder'),
        ('W', 'Winger'),
        ('CF', 'Centre-Forward'),
        ('FW', 'Forward'),
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
    preferred_position = models.CharField(max_length=100, blank=True, null=True, help_text="Detailed preferred position")
    provider_id = models.IntegerField(unique=True, null=True, blank=True, help_text="External API provider ID")
    
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
    bio = models.TextField(blank=True, default='')
    
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


class PlayerSeasonStatistic(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='season_statistics',
        help_text="Player associated with these season statistics"
    )
    season = models.CharField(max_length=20, help_text="Season identifier, e.g. '2026/2027'")
    competition = models.CharField(max_length=100, help_text="Competition name, e.g. 'La Liga'")
    appearances = models.PositiveSmallIntegerField(default=0, help_text="Total matches appeared in")
    goals = models.PositiveSmallIntegerField(default=0, help_text="Total goals scored")
    assists = models.PositiveSmallIntegerField(default=0, help_text="Total assists provided")
    minutes_played = models.PositiveIntegerField(default=0, help_text="Total minutes played across competition")
    yellow_cards = models.PositiveSmallIntegerField(default=0, help_text="Total yellow cards received")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-season', 'competition']
        verbose_name = "Player Season Statistic"
        verbose_name_plural = "Player Season Statistics"
        constraints = [
            models.UniqueConstraint(
                fields=['player', 'season', 'competition'],
                name='unique_player_season_competition'
            )
        ]

    def __str__(self):
        return f"{self.player.full_name} - {self.competition} ({self.season})"


class PlayerMatchPerformance(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='match_performances',
        help_text="Player who participated in this match"
    )
    match = models.ForeignKey(
        'matches.Match',
        on_delete=models.CASCADE,
        related_name='player_performances',
        help_text="Match in which the performance occurred"
    )
    minutes_played = models.PositiveSmallIntegerField(default=0, help_text="Minutes played in this match")
    rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Match performance rating (e.g. 7.50)"
    )
    goals = models.PositiveSmallIntegerField(default=0, help_text="Goals scored in this match")
    assists = models.PositiveSmallIntegerField(default=0, help_text="Assists in this match")
    shots = models.PositiveSmallIntegerField(default=0, help_text="Shots taken in this match")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Player Match Performance"
        verbose_name_plural = "Player Match Performances"
        constraints = [
            models.UniqueConstraint(
                fields=['player', 'match'],
                name='unique_player_match'
            )
        ]

    def __str__(self):
        rating_str = f" [Rating: {self.rating}]" if self.rating is not None else ""
        return f"{self.player.full_name} in {self.match}{rating_str}"

# players/models.py
from django.db import models
from django.urls import reverse

class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Goalkeeper'),
        ('DEF', 'Defender'),
        ('MID', 'Midfielder'),
        ('FWD', 'Forward'),
    ]
    
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=3, choices=POSITION_CHOICES)
    age = models.PositiveIntegerField()
    nationality = models.CharField(max_length=50)
    bio = models.TextField()
    profile_image = models.URLField(max_length=500, blank=True, null=True, help_text="Enter image URL")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Player'
        verbose_name_plural = 'Players'
    
    def __str__(self):
        return f"{self.name} - {self.get_position_display()}"
    
    def get_absolute_url(self):
        return reverse('players:player_detail', kwargs={'player_id': self.pk})

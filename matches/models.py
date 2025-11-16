from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class Match(models.Model):
    VENUE_CHOICES = [
        ('HOME', 'Camp Nou (Home)'),
        ('AWAY', 'Away'),
        ('NEUTRAL', 'Neutral Venue'),
    ]
    
    COMPETITION_CHOICES = [
        ('LA_LIGA', 'La Liga'),
        ('CHAMPIONS_LEAGUE', 'Champions League'),
        ('COPA_DEL_REY', 'Copa del Rey'),
        ('SUPERCOPA', 'Supercopa de España'),
        ('CLUB_WORLD_CUP', 'Club World Cup'),
        ('FRIENDLY', 'Friendly'),
        ('OTHER', 'Other'),
    ]
    
    opponent = models.CharField(max_length=100, help_text="Name of the opposing team")
    date = models.DateTimeField(help_text="Date and time of the match")
    venue = models.CharField(max_length=20, choices=VENUE_CHOICES, default='HOME')
    competition = models.CharField(max_length=20, choices=COMPETITION_CHOICES, default='LA_LIGA')
    result = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        help_text="Match result (e.g., '2-1', '0-0'). Leave blank for upcoming matches."
    )
    summary = models.TextField(
        help_text="Match review for completed matches or preview for upcoming matches"
    )
    image_url = models.URLField(
        blank=True, 
        null=True, 
        help_text="URL of an image hosted externally (e.g., Imgur, CDN)"
    )
    posted_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        help_text="Admin/user who posted this match"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Match"
        verbose_name_plural = "Matches"
    
    def __str__(self):
        return f"FC Barcelona vs {self.opponent} - {self.date.strftime('%Y-%m-%d')}"
    
    def get_absolute_url(self):
        return reverse('matches:match_detail', kwargs={'match_id': self.pk})
    
    @property
    def is_upcoming(self):
        """Check if match is upcoming (no result or future date)"""
        return not self.result or self.date > timezone.now()
    
    @property
    def is_completed(self):
        """Check if match is completed"""
        return bool(self.result) and self.date <= timezone.now()
    
    @property
    def match_status(self):
        """Get human-readable match status"""
        if self.is_upcoming:
            return "Upcoming"
        elif self.is_completed:
            return "Completed"
        else:
            return "Live"
    
    @property
    def competition_display(self):
        """Get human-readable competition name"""
        return dict(self.COMPETITION_CHOICES).get(self.competition, self.competition)
    
    @property
    def venue_display(self):
        """Get human-readable venue name"""
        return dict(self.VENUE_CHOICES).get(self.venue, self.venue)


class Comment(models.Model):
    match = models.ForeignKey(
        Match, 
        on_delete=models.CASCADE, 
        related_name='comments',
        help_text="The match this comment belongs to"
    )
    name = models.CharField(
        max_length=100, 
        help_text="Name of the person commenting"
    )
    comment = models.TextField(
        max_length=1000,
        help_text="The comment content"
    )
    email = models.EmailField(
        blank=True, 
        null=True,
        help_text="Optional email address (not displayed publicly)"
    )
    ip_address = models.GenericIPAddressField(
        blank=True, 
        null=True,
        help_text="IP address of the commenter (for moderation)"
    )
    is_approved = models.BooleanField(
        default=True,
        help_text="Whether the comment is approved for display"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Mark as featured comment"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        indexes = [
            models.Index(fields=['match', '-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.name} on {self.match.opponent} match"
    
    @property
    def short_comment(self):
        """Return truncated comment for admin display"""
        if len(self.comment) > 100:
            return f"{self.comment[:100]}..."
        return self.comment
    
    @property
    def days_since_posted(self):
        """Calculate days since comment was posted"""
        delta = timezone.now() - self.created_at
        return delta.days
    
    def get_absolute_url(self):
        """Get URL to the match detail page with comment anchor"""
        return f"{self.match.get_absolute_url()}#comment-{self.pk}"
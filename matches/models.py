# matches/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from culer.sanitizers import sanitize_plain_text, sanitize_rich_text


class Competition(models.Model):
    name = models.CharField(max_length=100, help_text="Full competition name (e.g. La Liga)")
    code = models.CharField(max_length=20, unique=True, help_text="Unique competition code (e.g. 'PD', 'CL')")
    logo_url = models.URLField(max_length=500, blank=True, null=True, help_text="Optional competition logo URL")

    class Meta:
        ordering = ['name']
        verbose_name = "Competition"
        verbose_name_plural = "Competitions"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Team(models.Model):
    name = models.CharField(max_length=100, help_text="Club name")
    short_name = models.CharField(max_length=50, help_text="Club short name (e.g. Barcelona)")
    tla = models.CharField(max_length=4, blank=True, default='', help_text="Three-letter acronym (e.g. FCB)")
    crest_url = models.URLField(max_length=500, blank=True, null=True, help_text="Optional crest/badge image URL")
    provider_id = models.IntegerField(unique=True, null=True, blank=True, help_text="External API provider ID")

    class Meta:
        ordering = ['name']
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self):
        return self.short_name or self.name


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

    STATUS_SCHEDULED = 'SCHEDULED'
    STATUS_LIVE = 'LIVE'
    STATUS_FINISHED = 'FINISHED'
    STATUS_POSTPONED = 'POSTPONED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_LIVE, 'Live'),
        (STATUS_FINISHED, 'Finished'),
        (STATUS_POSTPONED, 'Postponed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    competition = models.ForeignKey(
        Competition,
        on_delete=models.PROTECT,
        related_name='matches',
        help_text="Competition this match is part of"
    )
    home_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='home_matches',
        help_text="Home team"
    )
    away_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='away_matches',
        help_text="Away team"
    )
    season = models.CharField(
        max_length=20,
        default='2026/2027',
        help_text="Season string, e.g. '2026/2027'"
    )
    match_date = models.DateTimeField(
        db_index=True,
        default=timezone.now,
        help_text="Date and kickoff time"
    )
    venue = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Stadium or venue"
    )
    home_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Home score"
    )
    away_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Away score"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
        help_text="Current match status"
    )
    provider_match_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique match ID from API provider"
    )
    raw_data_snapshot = models.JSONField(
        blank=True,
        null=True,
        help_text="Raw provider payload"
    )

    # Legacy & content fields for backward compatibility
    summary = models.TextField(
        blank=True,
        default='',
        help_text="Match review or preview narrative"
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Match preview/graphic image URL"
    )
    posted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_posted',
        help_text="Admin/user who posted or verified this match"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-match_date']
        verbose_name = "Match"
        verbose_name_plural = "Matches"
        constraints = [
            models.UniqueConstraint(
                fields=['competition', 'season', 'home_team', 'away_team'],
                name='unique_competition_season_teams_match'
            )
        ]

    def __str__(self):
        home = self.home_team.short_name if self.home_team_id and hasattr(self, 'home_team') else 'Home'
        away = self.away_team.short_name if self.away_team_id and hasattr(self, 'away_team') else 'Away'
        date_str = self.match_date.strftime('%Y-%m-%d') if self.match_date else 'TBD'
        return f"{home} vs {away} - {date_str}"

    def get_absolute_url(self):
        return reverse('matches:match_detail', kwargs={'match_id': self.pk})

    @property
    def opponent(self):
        if self.home_team_id and hasattr(self, 'home_team') and self.home_team.name == "FC Barcelona":
            return self.away_team.name if self.away_team_id and hasattr(self, 'away_team') else "Opponent"
        if self.away_team_id and hasattr(self, 'away_team') and self.away_team.name == "FC Barcelona":
            return self.home_team.name if self.home_team_id and hasattr(self, 'home_team') else "Opponent"
        return self.away_team.name if self.away_team_id and hasattr(self, 'away_team') else "Opponent"

    @property
    def date(self):
        return self.match_date

    @property
    def result(self):
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score}-{self.away_score}"
        return None

    @property
    def is_upcoming(self):
        return self.status == self.STATUS_SCHEDULED or (self.match_date and self.match_date > timezone.now())

    @property
    def is_completed(self):
        return self.status == self.STATUS_FINISHED or (self.home_score is not None and self.away_score is not None)

    @property
    def match_status(self):
        if self.status == self.STATUS_LIVE:
            return "Live"
        elif self.is_completed:
            return "Completed"
        elif self.status == self.STATUS_POSTPONED:
            return "Postponed"
        elif self.status == self.STATUS_CANCELLED:
            return "Cancelled"
        return "Upcoming"

    @property
    def competition_display(self):
        return self.competition.name if self.competition_id and hasattr(self, 'competition') else ""

    @property
    def venue_display(self):
        return self.venue

    def clean(self):
        super().clean()
        if self.summary:
            self.summary = sanitize_rich_text(self.summary)

    def save(self, *args, **kwargs):
        if self.summary:
            self.summary = sanitize_rich_text(self.summary)
        super().save(*args, **kwargs)


class MatchStatistic(models.Model):
    match = models.OneToOneField(
        Match,
        on_delete=models.CASCADE,
        related_name='statistic',
        help_text="Match this statistic belongs to"
    )
    possession_home = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Home possession %"
    )
    possession_away = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Away possession %"
    )
    shots_home = models.PositiveSmallIntegerField(null=True, blank=True)
    shots_away = models.PositiveSmallIntegerField(null=True, blank=True)
    shots_on_target_home = models.PositiveSmallIntegerField(null=True, blank=True)
    shots_on_target_away = models.PositiveSmallIntegerField(null=True, blank=True)
    xg_home = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Home expected goals (xG)"
    )
    xg_away = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Away expected goals (xG)"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether stats are verified against official data"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Match Statistic"
        verbose_name_plural = "Match Statistics"

    def __str__(self):
        return f"Statistics: {self.match}"


class MatchEvent(models.Model):
    EVENT_GOAL = 'GOAL'
    EVENT_CARD = 'CARD'
    EVENT_SUB = 'SUB'

    EVENT_TYPE_CHOICES = [
        (EVENT_GOAL, 'Goal'),
        (EVENT_CARD, 'Card'),
        (EVENT_SUB, 'Substitution'),
    ]

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='events',
        help_text="Match this event occurred in"
    )
    minute = models.PositiveIntegerField(help_text="Match minute (e.g. 45, 90)")
    event_type = models.CharField(
        max_length=10,
        choices=EVENT_TYPE_CHOICES,
        help_text="Type of match event"
    )
    player_name = models.CharField(max_length=100, help_text="Player involved")
    detail = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Event detail (e.g., assist, foul, outgoing player)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['minute']
        verbose_name = "Match Event"
        verbose_name_plural = "Match Events"

    def __str__(self):
        return f"{self.minute}' [{self.get_event_type_display()}] {self.player_name} - {self.detail}"


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
        return f"Comment by {self.name} on {self.match}"
    
    @property
    def short_comment(self):
        if len(self.comment) > 100:
            return f"{self.comment[:100]}..."
        return self.comment
    
    @property
    def days_since_posted(self):
        delta = timezone.now() - self.created_at
        return delta.days
    
    def get_absolute_url(self):
        return f"{self.match.get_absolute_url()}#comment-{self.pk}"

    def clean(self):
        super().clean()
        if self.name:
            self.name = sanitize_plain_text(self.name)
        if self.comment:
            self.comment = sanitize_rich_text(self.comment)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = sanitize_plain_text(self.name)
        if self.comment:
            self.comment = sanitize_rich_text(self.comment)
        super().save(*args, **kwargs)

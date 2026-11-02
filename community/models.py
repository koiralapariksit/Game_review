# community/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from culer.sanitizers import sanitize_plain_text, sanitize_rich_text


class CommunityPost(models.Model):
    CATEGORY_MATCH_DISCUSSION = 'MATCH_DISCUSSION'
    CATEGORY_TACTICAL_DEBATE = 'TACTICAL_DEBATE'
    CATEGORY_PLAYER_DISCUSSION = 'PLAYER_DISCUSSION'
    CATEGORY_TRANSFER_TALK = 'TRANSFER_TALK'
    CATEGORY_GENERAL = 'GENERAL'

    CATEGORY_CHOICES = [
        (CATEGORY_MATCH_DISCUSSION, 'Match Discussion'),
        (CATEGORY_TACTICAL_DEBATE, 'Tactical Debate'),
        (CATEGORY_PLAYER_DISCUSSION, 'Player Discussion'),
        (CATEGORY_TRANSFER_TALK, 'Transfer Talk'),
        (CATEGORY_GENERAL, 'General'),
    ]

    MODERATION_STATUS_ACTIVE = 'ACTIVE'
    MODERATION_STATUS_FLAGGED = 'FLAGGED'
    MODERATION_STATUS_HIDDEN = 'HIDDEN'

    MODERATION_STATUS_CHOICES = [
        (MODERATION_STATUS_ACTIVE, 'Active'),
        (MODERATION_STATUS_FLAGGED, 'Flagged'),
        (MODERATION_STATUS_HIDDEN, 'Hidden'),
    ]

    title = models.CharField(max_length=200, help_text="Post title")
    content = models.TextField(help_text="Post content")
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
        db_index=True,
        help_text="Supporter discussion category"
    )
    related_match = models.ForeignKey(
        'matches.Match',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='community_posts',
        help_text="Optional linked match fixture"
    )
    related_player = models.ForeignKey(
        'players.Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='community_posts',
        help_text="Optional linked player"
    )
    image = models.ImageField(
        upload_to='community_posts/', 
        blank=True, 
        null=True,
        help_text="Optional post image"
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        help_text="Post author"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(
        default=True, 
        help_text="Uncheck to hide post from public view"
    )
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pin post to top of discussion feeds"
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Lock post to disable further comments"
    )
    moderation_status = models.CharField(
        max_length=20,
        choices=MODERATION_STATUS_CHOICES,
        default=MODERATION_STATUS_ACTIVE,
        db_index=True,
        help_text="Moderation lifecycle status"
    )
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = "Community Post"
        verbose_name_plural = "Community Posts"
    
    def __str__(self):
        return f"{self.title} [{self.get_moderation_status_display()}]"
    
    def get_absolute_url(self):
        return reverse('community:post_detail', kwargs={'pk': self.pk})
    
    def get_excerpt(self, length=150):
        """Return a truncated version of content for previews"""
        if len(self.content) <= length:
            return self.content
        return self.content[:length].rsplit(' ', 1)[0] + '...'

    def clean(self):
        super().clean()
        if self.title:
            self.title = sanitize_plain_text(self.title)
        if self.content:
            self.content = sanitize_rich_text(self.content)

    def save(self, *args, **kwargs):
        if self.title:
            self.title = sanitize_plain_text(self.title)
        if self.content:
            self.content = sanitize_rich_text(self.content)
        super().save(*args, **kwargs)


class Reaction(models.Model):
    TYPE_UPVOTE = 'UPVOTE'
    TYPE_TACTICAL_INSIGHT = 'TACTICAL_INSIGHT'
    TYPE_AGREE = 'AGREE'

    REACTION_CHOICES = [
        (TYPE_UPVOTE, 'Upvote'),
        (TYPE_TACTICAL_INSIGHT, 'Tactical Insight'),
        (TYPE_AGREE, 'Agree'),
    ]

    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='community_reactions'
    )
    reaction_type = models.CharField(
        max_length=30,
        choices=REACTION_CHOICES,
        default=TYPE_UPVOTE
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user', 'reaction_type'],
                name='unique_post_user_reaction'
            )
        ]
        verbose_name = 'Reaction'
        verbose_name_plural = 'Reactions'

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} on Post #{self.post_id}"


class ContentReport(models.Model):
    REASON_SPAM = 'SPAM'
    REASON_ABUSE = 'ABUSE'
    REASON_MISINFORMATION = 'MISINFORMATION'
    REASON_OFF_TOPIC = 'OFF_TOPIC'

    REASON_CHOICES = [
        (REASON_SPAM, 'Spam'),
        (REASON_ABUSE, 'Abuse / Harassment'),
        (REASON_MISINFORMATION, 'Misinformation'),
        (REASON_OFF_TOPIC, 'Off-Topic'),
    ]

    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    comment = models.ForeignKey(
        'Comment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='content_reports'
    )
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default=REASON_SPAM
    )
    details = models.TextField(blank=True, default='')
    resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Content Report'
        verbose_name_plural = 'Content Reports'

    def __str__(self):
        target = f"Post #{self.post_id}" if self.post else f"Comment #{self.comment_id}"
        return f"Report on {target} ({self.get_reason_display()}) by {self.reported_by.username}"


class Comment(models.Model):
    """Community Post Comment with XSS sanitization"""
    post = models.ForeignKey(
        CommunityPost, 
        on_delete=models.CASCADE, 
        related_name='comments',
        null=True, 
        blank=True
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='community_comments',
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=100, blank=True, default='')
    content = models.TextField(help_text="Comment text")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Community Comment"
        verbose_name_plural = "Community Comments"

    def __init__(self, *args, **kwargs):
        # Support both 'comment' and 'content' attribute names
        if 'comment' in kwargs and 'content' not in kwargs:
            kwargs['content'] = kwargs.pop('comment')
        super().__init__(*args, **kwargs)

    @property
    def comment(self):
        return self.content

    @comment.setter
    def comment(self, value):
        self.content = value

    @property
    def author_name(self):
        return self.name or (self.author.username if self.author else 'Culér Fan')

    def __str__(self):
        author_display = self.name or (self.author.username if self.author else 'Anonymous')
        return f"Comment by {author_display}"

    def clean(self):
        super().clean()
        if self.name:
            self.name = sanitize_plain_text(self.name)
        if self.content:
            self.content = sanitize_rich_text(self.content)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = sanitize_plain_text(self.name)
        if self.content:
            self.content = sanitize_rich_text(self.content)
        super().save(*args, **kwargs)

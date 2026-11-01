# community/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from culer.sanitizers import sanitize_plain_text, sanitize_rich_text


class CommunityPost(models.Model):
    title = models.CharField(max_length=200, help_text="Post title")
    content = models.TextField(help_text="Post content")
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
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Community Post"
        verbose_name_plural = "Community Posts"
    
    def __str__(self):
        return self.title
    
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

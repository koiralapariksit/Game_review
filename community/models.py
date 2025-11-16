# community/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


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
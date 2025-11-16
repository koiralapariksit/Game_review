# analysis/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone


class Article(models.Model):
    ARTICLE_TYPE_CHOICES = [
        ('tactical_analysis', 'Tactical Analysis'),
        ('opinion', 'Opinion'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    content = models.TextField()
    article_type = models.CharField(max_length=20, choices=ARTICLE_TYPE_CHOICES)
    image_url = models.URLField(blank=True, null=True, help_text="Optional external image URL")
    published_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('analysis:article_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_content_preview(self, words=30):
        """Return a preview of the content (first 30 words)"""
        return ' '.join(self.content.split()[:words]) + '...'


# ===== community/forms.py =====
from django import forms
from .models import CommunityPost, Comment
from culer.sanitizers import sanitize_plain_text, sanitize_rich_text


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ['title', 'content', 'category', 'related_match', 'related_player', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter post title...',
                'style': 'background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: white;'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Share your tactical thoughts, debate ideas, or match reactions...',
                'rows': 6,
                'style': 'background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: white; resize: vertical;'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'style': 'background: rgba(20, 24, 40, 0.9); border: 1px solid rgba(255, 255, 255, 0.2); color: white;'
            }),
            'related_match': forms.Select(attrs={
                'class': 'form-select',
                'style': 'background: rgba(20, 24, 40, 0.9); border: 1px solid rgba(255, 255, 255, 0.2); color: white;'
            }),
            'related_player': forms.Select(attrs={
                'class': 'form-select',
                'style': 'background: rgba(20, 24, 40, 0.9); border: 1px solid rgba(255, 255, 255, 0.2); color: white;'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'style': 'background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: white;'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].help_text = 'Choose a catchy title for your post'
        self.fields['content'].help_text = 'Share your thoughts, experiences, or start a discussion'
        self.fields['category'].help_text = 'Select discussion category'
        self.fields['related_match'].help_text = 'Optional: Link this discussion to a match fixture'
        self.fields['related_match'].required = False
        self.fields['related_player'].help_text = 'Optional: Link this discussion to a player'
        self.fields['related_player'].required = False
        self.fields['image'].help_text = 'Optional: Add an image to your post (JPG, PNG, GIF)'
        self.fields['image'].required = False

    def clean_title(self):
        title = self.cleaned_data.get('title', '')
        return sanitize_plain_text(title)

    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        return sanitize_rich_text(content)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['name', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name (optional)...',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write your comment...',
                'rows': 3,
            })
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '')
        return sanitize_plain_text(name)

    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        return sanitize_rich_text(content)

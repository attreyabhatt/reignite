from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class CommunityPost(models.Model):
    CATEGORY_CHOICES = [
        ('success_story', 'Success Story'),
        ('opening_line', 'Opening Line'),
        ('dating_advice', 'Dating Advice'),
        ('app_feedback', 'App Feedback'),
    ]

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='community_posts',
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    image_url = models.URLField(blank=True, default='')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    is_featured = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_deleted', '-created_at']),
            models.Index(fields=['is_featured', 'is_deleted']),
        ]

    def __str__(self):
        return self.title


class PostVote(models.Model):
    VOTE_CHOICES = [('up', 'Up'), ('down', 'Down')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_votes')
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='votes')
    vote_type = models.CharField(max_length=4, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} {self.vote_type}voted post {self.post_id}"


class CommunityComment(models.Model):
    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='community_comments',
    )
    body = models.TextField()
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'is_deleted', 'created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.author_id} on post {self.post_id}"


class CommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(CommunityComment, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')

    def __str__(self):
        return f"{self.user.username} liked comment {self.comment_id}"

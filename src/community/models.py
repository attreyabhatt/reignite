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
    is_anonymous = models.BooleanField(default=False)
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


class ContentReport(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('inappropriate', 'Inappropriate Content'),
        ('other', 'Other'),
    ]
    CONTENT_TYPE_CHOICES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_made',
    )
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    object_id = models.IntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    detail = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reporter', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.reporter.username} reported {self.content_type} {self.object_id}"


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocks_made',
    )
    blocked_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked_user')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked_user.username}"


class PostPoll(models.Model):
    post = models.OneToOneField(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name='poll',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Poll on post {self.post_id}"


class PollVote(models.Model):
    CHOICE_CHOICES = [
        ('send_it', 'Send It'),
        ('dont_send_it', "Don't Send It"),
    ]

    poll = models.ForeignKey(PostPoll, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='poll_votes')
    choice = models.CharField(max_length=15, choices=CHOICE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll', 'user')

    def __str__(self):
        return f"{self.user.username} voted {self.choice} on poll {self.poll_id}"

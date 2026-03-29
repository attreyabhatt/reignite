from django.contrib import admin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html

from .models import CommunityComment, CommunityPost, CommentLike, ContentReport, PollVote, PostPoll, PostVote, UserBlock


def _user_admin_link(user):
    if user is None:
        return '-'
    url = reverse('admin:auth_user_change', args=[user.pk])
    return format_html('<a href="{}">{}</a>', url, user.username)


class CommunityCommentInline(admin.TabularInline):
    model = CommunityComment
    # Keep one blank inline row visible so admins can add comments directly
    # from the CommunityPost admin change page without extra clicks.
    extra = 1
    fields = ('author', 'author_display_name', 'body', 'is_deleted', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('author',)
    show_change_link = True
    ordering = ('created_at',)


class PostVoteInline(admin.TabularInline):
    model = PostVote
    extra = 0
    fields = ('user', 'vote_type', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)


class CommentLikeInline(admin.TabularInline):
    model = CommentLike
    extra = 0
    fields = ('user', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'effective_author_name',
        'author_link',
        'category',
        'vote_score_display',
        'comment_count_display',
        'is_pinned',
        'is_featured',
        'is_deleted',
        'published_at',
    )
    list_filter = ('category', 'is_pinned', 'is_featured', 'is_deleted', 'published_at')
    search_fields = ('title', 'body', 'author__username', 'author_display_name')
    readonly_fields = ('created_at', 'updated_at', 'author_admin_link')
    fields = (
        'author',
        'author_admin_link',
        'author_display_name',
        'title',
        'body',
        'image_url',
        'category',
        'is_anonymous',
        'is_pinned',
        'is_featured',
        'is_deleted',
        'published_at',
        'created_at',
        'updated_at',
    )
    autocomplete_fields = ('author',)
    actions = [
        'pin_posts',
        'unpin_posts',
        'mark_featured',
        'unfeature',
        'remove_posts',
        'restore_posts',
        'clear_votes',
    ]
    inlines = [CommunityCommentInline, PostVoteInline]
    list_select_related = ('author',)
    list_per_page = 50

    def effective_author_name(self, obj):
        if obj.author_display_name:
            return obj.author_display_name
        if obj.author:
            return obj.author.username
        return '[deleted]'
    effective_author_name.short_description = 'Author Name'
    effective_author_name.admin_order_field = 'author_display_name'

    def author_link(self, obj):
        return _user_admin_link(obj.author)
    author_link.short_description = 'Linked User'
    author_link.admin_order_field = 'author__username'

    def author_admin_link(self, obj):
        return _user_admin_link(obj.author)
    author_admin_link.short_description = 'Edit author username'

    def vote_score_display(self, obj):
        result = obj.votes.aggregate(
            up=Count('id', filter=Q(vote_type='up')),
            down=Count('id', filter=Q(vote_type='down')),
        )
        return (result['up'] or 0) - (result['down'] or 0)
    vote_score_display.short_description = 'Score'

    def comment_count_display(self, obj):
        return obj.comments.filter(is_deleted=False).count()
    comment_count_display.short_description = 'Comments'

    @admin.action(description='Pin selected posts to the top of the feed')
    def pin_posts(self, request, queryset):
        queryset.update(is_pinned=True)

    @admin.action(description='Unpin selected posts')
    def unpin_posts(self, request, queryset):
        queryset.update(is_pinned=False)

    @admin.action(description='Mark selected posts as featured')
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description='Remove featured status')
    def unfeature(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description='Remove selected posts (soft delete)')
    def remove_posts(self, request, queryset):
        queryset.update(is_deleted=True)

    @admin.action(description='Restore selected posts')
    def restore_posts(self, request, queryset):
        queryset.update(is_deleted=False)

    @admin.action(description='Clear all votes on selected posts')
    def clear_votes(self, request, queryset):
        deleted, _ = PostVote.objects.filter(post__in=queryset).delete()
        self.message_user(
            request,
            f'Removed {deleted} vote record(s).',
        )


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = (
        'body_preview',
        'effective_author_name',
        'author_link',
        'post_link',
        'like_count_display',
        'is_deleted',
        'created_at',
    )
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('body', 'author__username', 'author_display_name', 'post__title')
    readonly_fields = ('created_at', 'author_admin_link')
    autocomplete_fields = ('author', 'post')
    actions = ['remove_comments', 'restore_comments', 'clear_likes']
    inlines = [CommentLikeInline]
    list_select_related = ('author', 'post')
    list_per_page = 50

    def body_preview(self, obj):
        return obj.body[:80] + '...' if len(obj.body) > 80 else obj.body
    body_preview.short_description = 'Comment'

    def effective_author_name(self, obj):
        if obj.author_display_name:
            return obj.author_display_name
        if obj.author:
            return obj.author.username
        return '[deleted]'
    effective_author_name.short_description = 'Author Name'
    effective_author_name.admin_order_field = 'author_display_name'

    def author_link(self, obj):
        return _user_admin_link(obj.author)
    author_link.short_description = 'Author'
    author_link.admin_order_field = 'author__username'

    def author_admin_link(self, obj):
        return _user_admin_link(obj.author)
    author_admin_link.short_description = 'Edit author username'

    def post_link(self, obj):
        url = reverse('admin:community_communitypost_change', args=[obj.post_id])
        return format_html('<a href="{}">{}</a>', url, obj.post.title[:50])
    post_link.short_description = 'Post'

    def like_count_display(self, obj):
        return obj.likes.count()
    like_count_display.short_description = 'Likes'

    @admin.action(description='Remove selected comments (soft delete)')
    def remove_comments(self, request, queryset):
        queryset.update(is_deleted=True)

    @admin.action(description='Restore selected comments')
    def restore_comments(self, request, queryset):
        queryset.update(is_deleted=False)

    @admin.action(description='Clear likes on selected comments')
    def clear_likes(self, request, queryset):
        deleted, _ = CommentLike.objects.filter(comment__in=queryset).delete()
        self.message_user(
            request,
            f'Removed {deleted} like record(s).',
        )


@admin.register(PostVote)
class PostVoteAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'post_link', 'vote_type', 'created_at')
    list_filter = ('vote_type', 'created_at')
    search_fields = ('user__username', 'post__title')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user', 'post')
    list_select_related = ('user', 'post')
    list_per_page = 100

    def user_link(self, obj):
        return _user_admin_link(obj.user)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def post_link(self, obj):
        url = reverse('admin:community_communitypost_change', args=[obj.post_id])
        return format_html('<a href="{}">{}</a>', url, obj.post.title[:50])
    post_link.short_description = 'Post'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'comment_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'comment__body')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user', 'comment')
    list_select_related = ('user', 'comment')
    list_per_page = 100

    def user_link(self, obj):
        return _user_admin_link(obj.user)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def comment_link(self, obj):
        url = reverse('admin:community_communitycomment_change', args=[obj.comment_id])
        body_preview = obj.comment.body[:50]
        return format_html('<a href="{}">{}</a>', url, body_preview)
    comment_link.short_description = 'Comment'


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ('reporter_link', 'content_type', 'reported_content_link', 'reason', 'detail_preview', 'content_status', 'created_at')
    list_filter = ('content_type', 'reason', 'created_at')
    search_fields = ('reporter__username', 'detail')
    readonly_fields = ('created_at', 'reported_content_preview')
    autocomplete_fields = ('reporter',)
    list_select_related = ('reporter',)
    list_per_page = 50
    actions = ['soft_delete_reported_content', 'dismiss_reports']

    def reporter_link(self, obj):
        return _user_admin_link(obj.reporter)
    reporter_link.short_description = 'Reporter'
    reporter_link.admin_order_field = 'reporter__username'

    def detail_preview(self, obj):
        return obj.detail[:80] + '...' if len(obj.detail) > 80 else obj.detail
    detail_preview.short_description = 'Detail'

    def _get_reported_object(self, obj):
        """Return the reported post or comment, or None."""
        try:
            if obj.content_type == 'post':
                return CommunityPost.objects.get(pk=obj.object_id)
            elif obj.content_type == 'comment':
                return CommunityComment.objects.get(pk=obj.object_id)
        except (CommunityPost.DoesNotExist, CommunityComment.DoesNotExist):
            pass
        return None

    def reported_content_link(self, obj):
        """Clickable link to the reported post or comment in admin."""
        target = self._get_reported_object(obj)
        if target is None:
            return format_html('<em>deleted</em>')
        if obj.content_type == 'post':
            url = reverse('admin:community_communitypost_change', args=[target.pk])
            label = target.title[:50]
        else:
            url = reverse('admin:community_communitycomment_change', args=[target.pk])
            label = target.body[:50]
        return format_html('<a href="{}">{}</a>', url, label)
    reported_content_link.short_description = 'Reported Content'

    def content_status(self, obj):
        """Show whether the reported content is still live or already removed."""
        target = self._get_reported_object(obj)
        if target is None:
            return format_html('<span style="color:#999;">Not found</span>')
        if target.is_deleted:
            return format_html('<span style="color:#999;">Removed</span>')
        return format_html('<span style="color:#c00;">Live</span>')
    content_status.short_description = 'Status'

    def reported_content_preview(self, obj):
        """Full preview of the reported content shown on the detail page."""
        target = self._get_reported_object(obj)
        if target is None:
            return 'Content not found (may have been hard-deleted).'
        if obj.content_type == 'post':
            status = '[REMOVED] ' if target.is_deleted else ''
            return f'{status}Title: {target.title}\n\nBody: {target.body[:500]}'
        else:
            status = '[REMOVED] ' if target.is_deleted else ''
            return f'{status}Comment on post #{target.post_id}: {target.body[:500]}'
    reported_content_preview.short_description = 'Content Preview'

    @admin.action(description='Remove reported content (soft delete)')
    def soft_delete_reported_content(self, request, queryset):
        deleted_posts = 0
        deleted_comments = 0
        for report in queryset:
            target = self._get_reported_object(report)
            if target is not None and not target.is_deleted:
                if report.content_type == 'post':
                    CommunityPost.objects.filter(pk=target.pk).update(is_deleted=True)
                    deleted_posts += 1
                elif report.content_type == 'comment':
                    CommunityComment.objects.filter(pk=target.pk).update(is_deleted=True)
                    deleted_comments += 1
        self.message_user(
            request,
            f'Removed {deleted_posts} post(s) and {deleted_comments} comment(s).',
        )

    @admin.action(description='Dismiss selected reports (delete report records)')
    def dismiss_reports(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Dismissed {count} report(s).')


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker_link', 'blocked_user_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__username', 'blocked_user__username')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('blocker', 'blocked_user')
    list_select_related = ('blocker', 'blocked_user')
    list_per_page = 50

    def blocker_link(self, obj):
        return _user_admin_link(obj.blocker)
    blocker_link.short_description = 'Blocker'
    blocker_link.admin_order_field = 'blocker__username'

    def blocked_user_link(self, obj):
        return _user_admin_link(obj.blocked_user)
    blocked_user_link.short_description = 'Blocked User'
    blocked_user_link.admin_order_field = 'blocked_user__username'


class PollVoteInline(admin.TabularInline):
    model = PollVote
    extra = 0
    fields = ('user', 'choice', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)


@admin.register(PostPoll)
class PostPollAdmin(admin.ModelAdmin):
    list_display = ('post_link', 'send_it_count', 'dont_send_it_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('post__title',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('post',)
    list_select_related = ('post',)
    inlines = [PollVoteInline]
    list_per_page = 50

    def post_link(self, obj):
        url = reverse('admin:community_communitypost_change', args=[obj.post_id])
        return format_html('<a href="{}">{}</a>', url, obj.post.title[:50])
    post_link.short_description = 'Post'

    def send_it_count(self, obj):
        return obj.votes.filter(choice='send_it').count()
    send_it_count.short_description = 'Send It'

    def dont_send_it_count(self, obj):
        return obj.votes.filter(choice='dont_send_it').count()
    dont_send_it_count.short_description = "Don't Send It"

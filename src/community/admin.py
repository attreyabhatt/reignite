from django.contrib import admin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html

from .models import CommunityComment, CommunityPost, CommentLike, PostVote


def _user_admin_link(user):
    if user is None:
        return '-'
    url = reverse('admin:auth_user_change', args=[user.pk])
    return format_html('<a href="{}">{}</a>', url, user.username)


class CommunityCommentInline(admin.TabularInline):
    model = CommunityComment
    extra = 0
    fields = ('author', 'body', 'is_deleted', 'created_at')
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
        'author_link',
        'category',
        'vote_score_display',
        'comment_count_display',
        'is_featured',
        'is_deleted',
        'created_at',
    )
    list_filter = ('category', 'is_featured', 'is_deleted', 'created_at')
    search_fields = ('title', 'body', 'author__username')
    readonly_fields = ('created_at', 'updated_at', 'author_admin_link')
    autocomplete_fields = ('author',)
    actions = [
        'mark_featured',
        'unfeature',
        'remove_posts',
        'restore_posts',
        'clear_votes',
    ]
    inlines = [CommunityCommentInline, PostVoteInline]
    list_select_related = ('author',)
    list_per_page = 50

    def author_link(self, obj):
        return _user_admin_link(obj.author)
    author_link.short_description = 'Author'
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
        'author_link',
        'post_link',
        'like_count_display',
        'is_deleted',
        'created_at',
    )
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('body', 'author__username', 'post__title')
    readonly_fields = ('created_at', 'author_admin_link')
    autocomplete_fields = ('author', 'post')
    actions = ['remove_comments', 'restore_comments', 'clear_likes']
    inlines = [CommentLikeInline]
    list_select_related = ('author', 'post')
    list_per_page = 50

    def body_preview(self, obj):
        return obj.body[:80] + '...' if len(obj.body) > 80 else obj.body
    body_preview.short_description = 'Comment'

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

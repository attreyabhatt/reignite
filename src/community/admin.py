from django.contrib import admin
from .models import CommunityPost, PostVote, CommunityComment, CommentLike


class CommunityCommentInline(admin.TabularInline):
    model = CommunityComment
    extra = 0
    readonly_fields = ('author', 'body', 'is_deleted', 'created_at')
    fields = ('author', 'body', 'is_deleted', 'created_at')
    can_delete = False
    show_change_link = True
    ordering = ('created_at',)


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'vote_score_display',
        'comment_count_display', 'is_featured', 'is_deleted', 'created_at',
    )
    list_filter = ('category', 'is_featured', 'is_deleted', 'created_at')
    search_fields = ('title', 'body', 'author__username')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_featured', 'unfeature', 'remove_posts', 'restore_posts']
    inlines = [CommunityCommentInline]
    list_per_page = 50

    def vote_score_display(self, obj):
        from django.db.models import Count, Q
        result = obj.votes.aggregate(
            up=Count('id', filter=Q(vote_type='up')),
            down=Count('id', filter=Q(vote_type='down')),
        )
        return result['up'] - result['down']
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


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ('body_preview', 'author', 'post_link', 'like_count_display', 'is_deleted', 'created_at')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('body', 'author__username')
    readonly_fields = ('created_at',)
    actions = ['remove_comments', 'restore_comments']
    list_per_page = 50

    def body_preview(self, obj):
        return obj.body[:80] + '...' if len(obj.body) > 80 else obj.body
    body_preview.short_description = 'Comment'

    def post_link(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
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


@admin.register(PostVote)
class PostVoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'vote_type', 'created_at')
    list_filter = ('vote_type', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'post', 'vote_type', 'created_at')
    list_per_page = 100


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    readonly_fields = ('user', 'comment', 'created_at')
    list_per_page = 100

"""
Community API views — forum-style posts, comments, votes, and likes.

Public (no auth): GET posts list, GET post detail.
Auth required: create post, vote, comment, like, delete own content.
"""

import logging
from datetime import datetime, timezone

import cloudinary.uploader
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count, Q
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from community.models import (
    CommentLike,
    CommunityComment,
    CommunityPost,
    PostVote,
)
from conversation.models import ChatCredit

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
# New post = created within this many hours
NEW_HOURS = 6
# Trending = created within 24 h and score >= threshold
TRENDING_HOURS = 24
TRENDING_SCORE_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rate(setting_name):
    def _value(group, request):
        return getattr(settings, setting_name)
    return _value


def _is_pro(user):
    """Return True if the user has an active subscription."""
    try:
        cc = ChatCredit.objects.get(user=user)
        if not cc.is_subscribed:
            return False
        if cc.subscription_expiry and cc.subscription_expiry < datetime.now(tz=timezone.utc):
            return False
        return True
    except ChatCredit.DoesNotExist:
        return False


def _author_payload(user):
    """Serialise the post/comment author into a dict."""
    if user is None:
        return {'username': '[deleted]', 'is_pro': False}
    return {
        'username': user.username,
        'is_pro': _is_pro(user),
    }


def _post_payload(post, user_vote=None, now=None):
    """Serialise a CommunityPost.

    `post` must have been annotated with `upvotes`, `downvotes`,
    and `comment_count` by the calling queryset.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    upvotes = getattr(post, 'upvotes', 0) or 0
    downvotes = getattr(post, 'downvotes', 0) or 0
    vote_score = upvotes - downvotes
    body_text = post.body or ''
    hours_old = max(0, (now - post.created_at).total_seconds() / 3600)

    return {
        'id': post.id,
        'title': post.title or '',
        'body_preview': (
            body_text[:200] + '...' if len(body_text) > 200 else body_text
        ),
        'category': post.category,
        'author': _author_payload(post.author),
        'vote_score': vote_score,
        'comment_count': getattr(post, 'comment_count', 0) or 0,
        'image_url': post.image_url or None,
        'is_featured': post.is_featured,
        'is_trending': (
            hours_old <= TRENDING_HOURS and vote_score >= TRENDING_SCORE_THRESHOLD
        ),
        'is_new': hours_old <= NEW_HOURS,
        'user_vote': user_vote,
        'created_at': post.created_at.isoformat(),
    }


def _comment_payload(comment, user_liked=False):
    like_count = getattr(comment, 'like_count', None)
    if like_count is None:
        like_count = comment.likes.count()
    return {
        'id': comment.id,
        'author': _author_payload(comment.author),
        'body': comment.body,
        'like_count': like_count,
        'user_liked': user_liked,
        'created_at': comment.created_at.isoformat(),
    }


def _annotated_posts_qs(base_qs):
    return base_qs.select_related('author').annotate(
        upvotes=Count('votes', filter=Q(votes__vote_type='up'), distinct=True),
        downvotes=Count('votes', filter=Q(votes__vote_type='down'), distinct=True),
        comment_count=Count(
            'comments',
            filter=Q(comments__is_deleted=False),
            distinct=True,
        ),
    )


def _sort_posts(posts, sort, now):
    """Sort a list of annotated post objects.

    Featured posts always float to the top within each sort bucket.
    """
    def hot_score(p):
        hours = max(0, (now - p.created_at).total_seconds() / 3600)
        return (p.upvotes - p.downvotes) / (hours + 2) ** 1.5

    if sort == 'new':
        key = lambda p: p.created_at.timestamp()
    elif sort == 'top':
        key = lambda p: p.upvotes - p.downvotes
    else:  # hot (default)
        key = hot_score

    featured = sorted([p for p in posts if p.is_featured], key=key, reverse=True)
    normal = sorted([p for p in posts if not p.is_featured], key=key, reverse=True)
    return featured + normal


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def community_post_list(request):
    if request.method == 'GET':
        return _list_posts(request)
    # POST requires auth
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required.'}, status=401)
    return _create_post(request)


def _list_posts(request):
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'hot').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    qs = CommunityPost.objects.filter(is_deleted=False)
    if category:
        qs = qs.filter(category=category)
    qs = _annotated_posts_qs(qs)

    now = datetime.now(tz=timezone.utc)
    posts = list(qs)
    sorted_posts = _sort_posts(posts, sort, now)

    # Pagination
    start = (page - 1) * PAGE_SIZE
    page_posts = sorted_posts[start: start + PAGE_SIZE]

    # Resolve user votes in one query
    user_votes = {}
    if request.user.is_authenticated and page_posts:
        ids = [p.id for p in page_posts]
        user_votes = {
            v.post_id: v.vote_type
            for v in PostVote.objects.filter(user=request.user, post_id__in=ids)
        }

    return Response({
        'posts': [_post_payload(p, user_votes.get(p.id), now) for p in page_posts],
        'page': page,
        'has_more': len(sorted_posts) > start + PAGE_SIZE,
        'total': len(sorted_posts),
    })


@ratelimit(key='user_or_ip', rate=_rate('COMMUNITY_RATELIMIT_POST_CREATE'), block=True)
def _create_post(request):
    title = (request.data.get('title') or '').strip()
    body = (request.data.get('body') or '').strip()
    category = (request.data.get('category') or '').strip()

    if not title:
        return Response({'error': 'title is required.'}, status=400)
    if len(title) > 200:
        return Response({'error': 'title must be 200 characters or fewer.'}, status=400)
    if not body:
        return Response({'error': 'body is required.'}, status=400)

    valid_categories = [c[0] for c in CommunityPost.CATEGORY_CHOICES]
    if category not in valid_categories:
        return Response(
            {'error': f'category must be one of: {", ".join(valid_categories)}'},
            status=400,
        )

    image_url = ''
    if 'image' in request.FILES:
        try:
            result = cloudinary.uploader.upload(
                request.FILES['image'],
                folder='community/posts',
                resource_type='image',
            )
            image_url = result.get('secure_url', '')
        except Exception:
            logger.exception('Cloudinary upload failed')
            return Response({'error': 'Image upload failed. Please try again.'}, status=500)

    post = CommunityPost.objects.create(
        author=request.user,
        title=title,
        body=body,
        category=category,
        image_url=image_url,
    )

    # Return annotated post
    annotated = _annotated_posts_qs(CommunityPost.objects.filter(pk=post.pk)).first()
    return Response(_post_payload(annotated), status=201)


@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def community_post_detail(request, post_id):
    post = _annotated_posts_qs(
        CommunityPost.objects.filter(pk=post_id, is_deleted=False)
    ).select_related('author').first()

    if post is None:
        return Response({'error': 'Post not found.'}, status=404)

    if request.method == 'DELETE':
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=401)
        if post.author_id != request.user.pk:
            return Response({'error': 'You can only delete your own posts.'}, status=403)
        post.is_deleted = True
        CommunityPost.objects.filter(pk=post_id).update(is_deleted=True)
        return Response({'status': 'deleted'})

    # GET — post detail + comments
    user_vote = None
    if request.user.is_authenticated:
        try:
            pv = PostVote.objects.get(user=request.user, post_id=post_id)
            user_vote = pv.vote_type
        except PostVote.DoesNotExist:
            pass

    now = datetime.now(tz=timezone.utc)
    payload = _post_payload(post, user_vote, now)
    payload['body'] = post.body or ''  # include full body in detail

    # Comments
    comments = list(
        CommunityComment.objects.filter(post_id=post_id, is_deleted=False)
        .select_related('author')
        .annotate(like_count=Count('likes'))
    )
    liked_ids = set()
    if request.user.is_authenticated and comments:
        liked_ids = set(
            CommentLike.objects.filter(
                user=request.user, comment_id__in=[c.id for c in comments]
            ).values_list('comment_id', flat=True)
        )

    payload['comments'] = [
        _comment_payload(c, user_liked=(c.id in liked_ids)) for c in comments
    ]
    return Response(payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def community_post_vote(request, post_id):
    """Toggle or change a vote. Sending the same vote_type twice removes the vote."""
    vote_type = (request.data.get('vote_type') or '').strip()
    if vote_type not in ('up', 'down'):
        return Response({'error': 'vote_type must be "up" or "down".'}, status=400)

    try:
        post = CommunityPost.objects.get(pk=post_id, is_deleted=False)
    except CommunityPost.DoesNotExist:
        return Response({'error': 'Post not found.'}, status=404)

    existing = PostVote.objects.filter(user=request.user, post=post).first()

    if existing is None:
        try:
            PostVote.objects.create(user=request.user, post=post, vote_type=vote_type)
            user_vote = vote_type
        except IntegrityError:
            # Rare race: another request created the vote between read and create.
            existing = PostVote.objects.filter(user=request.user, post=post).first()

    if existing is not None:
        if existing.vote_type == vote_type:
            # Same vote -> toggle off
            existing.delete()
            user_vote = None
        else:
            # Switch vote direction
            existing.vote_type = vote_type
            existing.save(update_fields=['vote_type'])
            user_vote = vote_type

    annotated = _annotated_posts_qs(
        CommunityPost.objects.filter(pk=post_id, is_deleted=False)
    ).first()
    if annotated is None:
        return Response({'error': 'Post not found.'}, status=404)
    return Response({
        'vote_score': annotated.upvotes - annotated.downvotes,
        'user_vote': user_vote,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user_or_ip', rate=_rate('COMMUNITY_RATELIMIT_COMMENT_CREATE'), block=True)
def community_post_comment(request, post_id):
    body = (request.data.get('body') or '').strip()
    if not body:
        return Response({'error': 'body is required.'}, status=400)

    try:
        post = CommunityPost.objects.get(pk=post_id, is_deleted=False)
    except CommunityPost.DoesNotExist:
        return Response({'error': 'Post not found.'}, status=404)

    comment = CommunityComment.objects.create(
        post=post,
        author=request.user,
        body=body,
    )
    return Response(_comment_payload(comment), status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def community_comment_delete(request, comment_id):
    try:
        comment = CommunityComment.objects.get(pk=comment_id, is_deleted=False)
    except CommunityComment.DoesNotExist:
        return Response({'error': 'Comment not found.'}, status=404)

    if comment.author_id != request.user.pk:
        return Response({'error': 'You can only delete your own comments.'}, status=403)

    CommunityComment.objects.filter(pk=comment_id).update(is_deleted=True)
    return Response({'status': 'deleted'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def community_comment_like(request, comment_id):
    """Toggle like on a comment."""
    try:
        comment = CommunityComment.objects.get(pk=comment_id, is_deleted=False)
    except CommunityComment.DoesNotExist:
        return Response({'error': 'Comment not found.'}, status=404)

    try:
        CommentLike.objects.create(user=request.user, comment=comment)
        liked = True
    except IntegrityError:
        # Already liked → unlike
        CommentLike.objects.filter(user=request.user, comment=comment).delete()
        liked = False

    return Response({
        'liked': liked,
        'like_count': comment.likes.count(),
    })


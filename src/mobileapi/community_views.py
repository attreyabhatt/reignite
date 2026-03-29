"""
Community API views — forum-style posts, comments, votes, and likes.

Public (no auth): GET posts list, GET post detail.
Auth required: create post, vote, comment, like, delete own content.
"""

import logging
from datetime import datetime, timezone

import cloudinary.uploader
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, ExpressionWrapper, IntegerField, Q
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from community.models import (
    CommentLike,
    ContentReport,
    CommunityComment,
    CommunityPost,
    PollVote,
    PostPoll,
    PostVote,
    UserBlock,
)
from conversation.models import ChatCredit, MobileAppConfig
from .push_notifications import send_post_comment_notification

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
# New post = published within this many hours
NEW_HOURS = 6
# Trending = published within 24 h and score >= threshold
TRENDING_HOURS = 24
TRENDING_SCORE_THRESHOLD = 5
VALID_SORTS = ('new', 'hot', 'top')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rate(setting_name):
    def _value(group, request):
        return getattr(settings, setting_name)
    return _value


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ('true', '1', 'yes', 'on')


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
        return {'id': None, 'username': '[deleted]', 'is_pro': False}
    return {
        'id': user.pk,
        'username': user.username,
        'is_pro': _is_pro(user),
    }


def _post_published_at(post):
    return getattr(post, 'published_at', post.created_at)


def _post_payload(post, user_vote=None, now=None, request_user=None):
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
    published_at = _post_published_at(post)
    hours_old = max(0, (now - published_at).total_seconds() / 3600)

    # If anonymous and the requester is not the author, hide identity
    is_anon = getattr(post, 'is_anonymous', False)
    is_own_post = (
        request_user is not None
        and request_user.is_authenticated
        and post.author_id == request_user.pk
    )
    if is_anon and not is_own_post:
        author = {'id': None, 'username': 'Anonymous', 'is_pro': False}
    else:
        author = _author_payload(post.author)
        custom_author_name = (getattr(post, 'author_display_name', '') or '').strip()
        if custom_author_name:
            author['username'] = custom_author_name

    # Poll data
    poll_data = None
    try:
        poll = post.poll
        send_it = poll.votes.filter(choice='send_it').count()
        dont_send_it = poll.votes.filter(choice='dont_send_it').count()
        user_poll_vote = None
        if request_user and request_user.is_authenticated:
            pv = poll.votes.filter(user=request_user).first()
            if pv:
                user_poll_vote = pv.choice
        poll_data = {
            'send_it_count': send_it,
            'dont_send_it_count': dont_send_it,
            'user_vote': user_poll_vote,
        }
    except PostPoll.DoesNotExist:
        pass

    return {
        'id': post.id,
        'title': post.title or '',
        'body_preview': (
            body_text[:200] + '...' if len(body_text) > 200 else body_text
        ),
        'category': post.category,
        'author': author,
        'vote_score': vote_score,
        'comment_count': getattr(post, 'comment_count', 0) or 0,
        'image_url': post.image_url or None,
        'is_featured': post.is_featured,
        'is_pinned': post.is_pinned,
        'is_anonymous': is_anon,
        'is_trending': (
            hours_old <= TRENDING_HOURS and vote_score >= TRENDING_SCORE_THRESHOLD
        ),
        'is_new': hours_old <= NEW_HOURS,
        'user_vote': user_vote,
        'poll': poll_data,
        # Keep created_at for backward compatibility with clients.
        'created_at': published_at.isoformat(),
        'published_at': published_at.isoformat(),
    }


def _comment_payload(comment, user_liked=False):
    like_count = getattr(comment, 'like_count', None)
    if like_count is None:
        like_count = comment.likes.count()
    author = _author_payload(comment.author)
    custom_author_name = (getattr(comment, 'author_display_name', '') or '').strip()
    if custom_author_name:
        author['username'] = custom_author_name
    return {
        'id': comment.id,
        'author': author,
        'body': comment.body,
        'like_count': like_count,
        'user_liked': user_liked,
        'created_at': comment.created_at.isoformat(),
    }


def _annotated_posts_qs(base_qs):
    upvotes_expr = Count('votes', filter=Q(votes__vote_type='up'), distinct=True)
    downvotes_expr = Count('votes', filter=Q(votes__vote_type='down'), distinct=True)
    return base_qs.select_related('author').annotate(
        upvotes=upvotes_expr,
        downvotes=downvotes_expr,
        vote_score=ExpressionWrapper(
            upvotes_expr - downvotes_expr,
            output_field=IntegerField(),
        ),
        comment_count=Count(
            'comments',
            filter=Q(comments__is_deleted=False),
            distinct=True,
        ),
    )


def _ordered_posts_qs(qs, sort):
    # Pinned posts always appear first, regardless of sort mode.
    # Featured posts float to the top within the non-pinned bucket.
    if sort == 'new':
        return qs.order_by('-is_pinned', '-is_featured', '-published_at', '-vote_score', '-id')
    if sort == 'top':
        return qs.order_by('-is_pinned', '-is_featured', '-vote_score', '-published_at', '-id')
    # hot (default): recency first, then score.
    return qs.order_by('-is_pinned', '-is_featured', '-published_at', '-vote_score', '-id')


def _default_feed_sort():
    try:
        configured = (MobileAppConfig.load().community_default_sort or '').strip().lower()
    except Exception as exc:
        logger.warning('Falling back to community default sort "new": %s', exc)
        return 'new'
    if configured in VALID_SORTS:
        return configured
    return 'new'


def _resolve_feed_sort(raw_sort):
    if raw_sort is None or str(raw_sort).strip() == '':
        return _default_feed_sort()
    normalized = str(raw_sort).strip().lower()
    if normalized in VALID_SORTS:
        return normalized
    return 'hot'


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
    sort = _resolve_feed_sort(request.GET.get('sort'))
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    now = datetime.now(tz=timezone.utc)
    qs = CommunityPost.objects.filter(is_deleted=False)
    if not (request.user.is_authenticated and request.user.is_staff):
        qs = qs.filter(published_at__lte=now)
    if category:
        qs = qs.filter(category=category)
    # Exclude posts from blocked users
    if request.user.is_authenticated:
        blocked_ids = set(
            UserBlock.objects.filter(blocker=request.user).values_list('blocked_user_id', flat=True)
        )
        if blocked_ids:
            qs = qs.exclude(author_id__in=blocked_ids)
    total_posts = qs.count()
    qs = _annotated_posts_qs(qs)
    ordered_qs = _ordered_posts_qs(qs, sort)

    # Pagination
    start = (page - 1) * PAGE_SIZE
    page_posts = list(ordered_qs[start: start + PAGE_SIZE])

    # Resolve user votes in one query
    user_votes = {}
    if request.user.is_authenticated and page_posts:
        ids = [p.id for p in page_posts]
        user_votes = {
            v.post_id: v.vote_type
            for v in PostVote.objects.filter(user=request.user, post_id__in=ids)
        }

    return Response({
        'posts': [_post_payload(p, user_votes.get(p.id), now, request_user=request.user) for p in page_posts],
        'page': page,
        'sort': sort,
        'has_more': total_posts > start + PAGE_SIZE,
        'total': total_posts,
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

    is_anonymous = _parse_bool(request.data.get('is_anonymous', False))
    author_display_name = ''
    published_at = None

    # Staff can seed/schedule posts with custom display names and publish times.
    if request.user.is_staff:
        author_display_name = (request.data.get('author_display_name') or '').strip()
        if len(author_display_name) > 150:
            return Response(
                {'error': 'author_display_name must be 150 characters or fewer.'},
                status=400,
            )

        raw_published_at = request.data.get('published_at')
        if raw_published_at not in (None, ''):
            raw_published_at = str(raw_published_at).strip()
            try:
                published_at = datetime.fromisoformat(raw_published_at.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                    {'error': 'published_at must be a valid ISO-8601 datetime.'},
                    status=400,
                )
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

    post_data = dict(
        author=request.user,
        author_display_name=author_display_name,
        title=title,
        body=body,
        category=category,
        image_url=image_url,
        is_anonymous=is_anonymous,
    )
    if published_at is not None:
        post_data['published_at'] = published_at

    post = CommunityPost.objects.create(**post_data)

    # Create poll if requested
    has_poll = _parse_bool(request.data.get('has_poll', False))
    if has_poll:
        PostPoll.objects.create(post=post)

    # Return annotated post
    annotated = _annotated_posts_qs(CommunityPost.objects.filter(pk=post.pk)).first()
    return Response(_post_payload(annotated, request_user=request.user), status=201)


@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def community_post_detail(request, post_id):
    qs = CommunityPost.objects.filter(pk=post_id, is_deleted=False)
    if request.method == 'GET' and not (
        request.user.is_authenticated and request.user.is_staff
    ):
        qs = qs.filter(published_at__lte=datetime.now(tz=timezone.utc))

    post = _annotated_posts_qs(qs).select_related('author').first()

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
    payload = _post_payload(post, user_vote, now, request_user=request.user)
    payload['body'] = post.body or ''  # include full body in detail

    # Comments (exclude blocked users)
    comments_qs = CommunityComment.objects.filter(post_id=post_id, is_deleted=False)
    if request.user.is_authenticated:
        blocked_ids = set(
            UserBlock.objects.filter(blocker=request.user).values_list('blocked_user_id', flat=True)
        )
        if blocked_ids:
            comments_qs = comments_qs.exclude(author_id__in=blocked_ids)
    comments = list(
        comments_qs.select_related('author')
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
    transaction.on_commit(
        lambda: send_post_comment_notification(
            post_author_id=post.author_id,
            comment_author_id=comment.author_id,
            post_id=post.id,
            comment_id=comment.id,
        )
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

    like, created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment,
    )
    if created:
        liked = True
    else:
        # Already liked -> unlike
        like.delete()
        liked = False

    return Response({
        'liked': liked,
        'like_count': comment.likes.count(),
    })


# ---------------------------------------------------------------------------
# Report / Block endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user_or_ip', rate=_rate('COMMUNITY_RATELIMIT_COMMENT_CREATE'), block=True)
def report_post(request, post_id):
    """Report a community post."""
    try:
        post = CommunityPost.objects.get(pk=post_id, is_deleted=False)
    except CommunityPost.DoesNotExist:
        return Response({'error': 'Post not found.'}, status=404)

    # Cannot report your own post
    if post.author_id == request.user.pk:
        return Response({'error': 'You cannot report your own content.'}, status=400)

    reason = (request.data.get('reason') or '').strip()
    valid_reasons = [c[0] for c in ContentReport.REASON_CHOICES]
    if reason not in valid_reasons:
        return Response({'error': f'reason must be one of: {", ".join(valid_reasons)}'}, status=400)

    detail = (request.data.get('detail') or '').strip()

    _, created = ContentReport.objects.get_or_create(
        reporter=request.user,
        content_type='post',
        object_id=post_id,
        defaults={
            'reason': reason,
            'detail': detail,
        },
    )
    if not created:
        return Response({'error': 'You have already reported this post.'}, status=409)

    return Response({'status': 'reported'}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user_or_ip', rate=_rate('COMMUNITY_RATELIMIT_COMMENT_CREATE'), block=True)
def report_comment(request, comment_id):
    """Report a community comment."""
    try:
        comment = CommunityComment.objects.get(pk=comment_id, is_deleted=False)
    except CommunityComment.DoesNotExist:
        return Response({'error': 'Comment not found.'}, status=404)

    # Cannot report your own comment
    if comment.author_id == request.user.pk:
        return Response({'error': 'You cannot report your own content.'}, status=400)

    reason = (request.data.get('reason') or '').strip()
    valid_reasons = [c[0] for c in ContentReport.REASON_CHOICES]
    if reason not in valid_reasons:
        return Response({'error': f'reason must be one of: {", ".join(valid_reasons)}'}, status=400)

    detail = (request.data.get('detail') or '').strip()

    _, created = ContentReport.objects.get_or_create(
        reporter=request.user,
        content_type='comment',
        object_id=comment_id,
        defaults={
            'reason': reason,
            'detail': detail,
        },
    )
    if not created:
        return Response({'error': 'You have already reported this comment.'}, status=409)

    return Response({'status': 'reported'}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_block_user(request, user_id):
    """Block or unblock a user. Returns the new blocked status."""
    from django.contrib.auth.models import User as AuthUser

    # Cannot block yourself
    if user_id == request.user.pk:
        return Response({'error': 'You cannot block yourself.'}, status=400)

    try:
        target_user = AuthUser.objects.get(pk=user_id)
    except AuthUser.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)

    block, created = UserBlock.objects.get_or_create(
        blocker=request.user,
        blocked_user=target_user,
    )
    if created:
        blocked = True
    else:
        # Already blocked -> unblock
        block.delete()
        blocked = False

    return Response({'blocked': blocked})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blocked_users_list(request):
    """Return the list of user IDs blocked by the current user."""
    blocked_ids = list(
        UserBlock.objects.filter(blocker=request.user).values_list('blocked_user_id', flat=True)
    )
    return Response({'blocked_user_ids': blocked_ids})


# ---------------------------------------------------------------------------
# Poll endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def community_poll_vote(request, post_id):
    """Vote on a post's poll. Toggle: voting the same choice again removes it."""
    choice = (request.data.get('choice') or '').strip()
    if choice not in ('send_it', 'dont_send_it'):
        return Response({'error': 'choice must be "send_it" or "dont_send_it".'}, status=400)

    try:
        poll = PostPoll.objects.select_related('post').get(post__pk=post_id, post__is_deleted=False)
    except PostPoll.DoesNotExist:
        return Response({'error': 'Poll not found.'}, status=404)

    existing = PollVote.objects.filter(poll=poll, user=request.user).first()

    if existing is None:
        try:
            PollVote.objects.create(poll=poll, user=request.user, choice=choice)
            user_vote = choice
        except IntegrityError:
            existing = PollVote.objects.filter(poll=poll, user=request.user).first()

    if existing is not None:
        if existing.choice == choice:
            existing.delete()
            user_vote = None
        else:
            existing.choice = choice
            existing.save(update_fields=['choice'])
            user_vote = choice

    send_it = poll.votes.filter(choice='send_it').count()
    dont_send_it = poll.votes.filter(choice='dont_send_it').count()

    return Response({
        'send_it_count': send_it,
        'dont_send_it_count': dont_send_it,
        'user_vote': user_vote,
    })


"""
Replace all comments on the pinned welcome post with emoji-only reactions.
Idempotent — clears existing seed comments before re-adding.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from community.models import CommunityComment, CommunityPost

EMOJI_COMMENTS = [
    "\U0001f525",           # 🔥
    "\U0001f4aa",           # 💪
    "\u2764\ufe0f",         # ❤️
    "\U0001f64c",           # 🙌
    "\U0001f44f",           # 👏
    "\U0001f60d",           # 😍
    "\U0001f680",           # 🚀
    "\u2728",               # ✨
    "\U0001f4af",           # 💯
    "\U0001f44d",           # 👍
    "\U0001f389",           # 🎉
    "\U0001f60a",           # 😊
    "\U0001f92f",           # 🤯
    "\U0001f929",           # 🤩
    "\u26a1",               # ⚡
    "\U0001f525\U0001f525\U0001f525",   # 🔥🔥🔥
    "\u2764\ufe0f\U0001f4aa",           # ❤️💪
    "\U0001f64c\U0001f389",             # 🙌🎉
    "\U0001f525\U0001f4af",             # 🔥💯
    "\U0001f44f\U0001f44f",             # 👏👏
    "\U0001f929\u2728",                 # 🤩✨
    "\U0001f680\U0001f525",             # 🚀🔥
    "\U0001f4aa\U0001f4af",             # 💪💯
]

DUMMY_USERNAMES = [
    "seed_u01", "seed_u02", "seed_u03", "seed_u04", "seed_u05",
    "seed_u06", "seed_u07", "seed_u08", "seed_u09", "seed_u10",
    "seed_u11", "seed_u12", "seed_u13", "seed_u14", "seed_u15",
    "seed_u16", "seed_u17", "seed_u18", "seed_u19", "seed_u20",
    "seed_u21", "seed_u22", "seed_u23",
]


class Command(BaseCommand):
    help = "Seed emoji-only comments on the pinned welcome post."

    def handle(self, *args, **options):
        try:
            post = CommunityPost.objects.get(is_pinned=True)
        except CommunityPost.DoesNotExist:
            self.stdout.write(self.style.ERROR("No pinned post found."))
            return
        except CommunityPost.MultipleObjectsReturned:
            post = CommunityPost.objects.filter(is_pinned=True).order_by('id').first()

        # Remove existing seed-user comments on this post
        seed_users = User.objects.filter(username__in=DUMMY_USERNAMES)
        deleted, _ = CommunityComment.objects.filter(
            post=post, author__in=seed_users
        ).delete()
        self.stdout.write(f"  Cleared {deleted} existing seed comments.")

        # Add emoji comments from as many seed users as we have emojis
        users = list(seed_users.order_by('username'))
        created = 0
        for user, emoji in zip(users, EMOJI_COMMENTS):
            CommunityComment.objects.create(
                post=post,
                author=user,
                author_display_name=user.username.lstrip("seed_u").lstrip("0") or user.username,
                body=emoji,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Added {created} emoji comments to post id={post.pk}."
        ))

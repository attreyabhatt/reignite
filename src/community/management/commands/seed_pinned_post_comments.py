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

DUMMY_USERS = {
    "seed_u01": "jakehm",
    "seed_u02": "tyler_dates",
    "seed_u03": "remi_w",
    "seed_u04": "quietguy_wins",
    "seed_u05": "marcus_f",
    "seed_u06": "dom_texts",
    "seed_u07": "callum_r99",
    "seed_u08": "n8_dating",
    "seed_u09": "alex_t",
    "seed_u10": "gymrat_hoping",
    "seed_u11": "textingcrisis",
    "seed_u12": "overthinking_obv",
    "seed_u13": "second_chance_sam",
    "seed_u14": "tired_of_lol",
    "seed_u15": "week_of_silence",
    "seed_u16": "plan_b_needed",
    "seed_u17": "no_more_games",
    "seed_u18": "convo_coach",
    "seed_u19": "flag_checker",
    "seed_u20": "anti_games",
    "seed_u21": "bumble_respond",
    "seed_u22": "confused_in_DMs",
    "seed_u23": "bio_writer_v3",
}


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
        seed_users = User.objects.filter(username__in=DUMMY_USERS.keys())
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
                author_display_name=DUMMY_USERS.get(user.username, user.username),
                body=emoji,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Added {created} emoji comments to post id={post.pk}."
        ))

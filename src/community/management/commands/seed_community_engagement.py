"""
Seed dummy comments, upvotes, and poll votes on community posts.
Idempotent — safe to run multiple times.
"""
import random
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from community.models import (
    CommunityComment,
    CommunityPost,
    CommentLike,
    PostPoll,
    PostVote,
    PollVote,
)

# ---------------------------------------------------------------------------
# Dummy user pool
# ---------------------------------------------------------------------------

DUMMY_USERS = [
    ("seed_u01", "jakehm"),
    ("seed_u02", "tyler_dates"),
    ("seed_u03", "remi_w"),
    ("seed_u04", "quietguy_wins"),
    ("seed_u05", "marcus_f"),
    ("seed_u06", "dom_texts"),
    ("seed_u07", "callum_r99"),
    ("seed_u08", "n8_dating"),
    ("seed_u09", "alex_t"),
    ("seed_u10", "gymrat_hoping"),
    ("seed_u11", "textingcrisis"),
    ("seed_u12", "overthinking_obv"),
    ("seed_u13", "second_chance_sam"),
    ("seed_u14", "tired_of_lol"),
    ("seed_u15", "week_of_silence"),
    ("seed_u16", "plan_b_needed"),
    ("seed_u17", "no_more_games"),
    ("seed_u18", "convo_coach"),
    ("seed_u19", "flag_checker"),
    ("seed_u20", "anti_games"),
    ("seed_u21", "bumble_respond"),
    ("seed_u22", "confused_in_DMs"),
    ("seed_u23", "bio_writer_v3"),
    ("seed_u24", "too_much_or_enough"),
    ("seed_u25", "zero_matches"),
]

# ---------------------------------------------------------------------------
# Comment banks per category
# ---------------------------------------------------------------------------

WINS_COMMENTS = [
    "This is exactly the energy I needed to see today. Congrats!",
    "Saving this message. That line is genuinely great.",
    "The specificity is everything. Generic compliments are dead.",
    "Ok that message is smooth without being try-hard. Love it.",
    "How long had you been talking before this?",
    "This is the kind of update we need more of in here. Keep us posted!",
    "I've been doing the 'boring hey' thing for months. This is the wake-up call.",
    "That last line is doing SO much work. Well played.",
    "Congrats! How did the date go?",
    "The confidence here is what makes it work. You're not asking, you're inviting.",
    "Did she know you were using an app to help? Or does it not matter lol",
    "Screenshots or it didn't happen jk — but seriously congrats",
    "This is why I come to this community. Real results.",
    "I tried something similar last week. She said yes too. It works.",
    "The fact that she replied in 4 minutes says everything.",
    "Sending this to my mate who sends 'hey' to every match.",
    "The 'give her something to react to' advice is underrated.",
    "Bro this gave me hope. I've been in a dry spell for months.",
    "We need a follow-up post after the date!!",
    "The part about replying too fast is so real. I've been guilty of this.",
    "Matched energy is everything. You clearly came in confident.",
    "Finally a win post with actual details. Thank you for sharing the message.",
    "That 'ping-pong' framing is perfect. Going to use that mindset.",
    "8 months! And one message is all it took. Wild.",
    "The 'leave space' advice is hard to follow when you're anxious but it's so true.",
]

HELP_ME_REPLY_COMMENTS = [
    "Send it. The worst that happens is silence — which is what you already have.",
    "Don't send it. Give it one more day then reach out with something completely fresh.",
    "Option A is the move here. Warm but not desperate.",
    "I've been in this exact situation. I sent it. She replied. You got this.",
    "The tone is right but I'd cut the last sentence. Ends stronger without it.",
    "Voted send it. The worst outcome is she doesn't reply — and you already have that.",
    "This is giving off the right energy honestly. Not too eager.",
    "I'd change 'not sure if' to just 'hey' — it cuts the hedging.",
    "The gym thing is tricky but that opener is actually cute. Send it.",
    "Wait one more day. Two days is nothing, don't overthink it.",
    "Been there. I sent mine and got ghosted. But at least I knew where I stood.",
    "That opener is perfect — acknowledges the context without being weird about it.",
    "Voted don't send. It reads a bit try-hard. Keep it simpler.",
    "The directness in this is actually refreshing. Most guys wouldn't say this.",
    "Option C is the strongest one here. It's warm without being needy.",
    "Honestly she's probably just bad at texting off the app. Meet up sooner.",
    "I would send this 100%. The light touch is exactly right.",
    "If she cancelled with no rescheduling offer that's your answer unfortunately.",
    "Cut the 'no stress' at the end. It undercuts the whole message.",
    "The rescheduling offer is smart — you're leaving the door open without holding it.",
    "Voted send it. Life genuinely does get in the way sometimes.",
    "Had the same situation last month. Sent it. She apologised and we rescheduled.",
    "The voice note response is a great sign honestly, that's engagement.",
    "I've been the girl in this situation before — she's probably just nervous. Send it.",
    "This is exactly what I'd want to receive if I cancelled on someone. Send it.",
]

DATING_ADVICE_COMMENTS = [
    "The 'move off the app quickly' point is huge. People over-invest in chat.",
    "Point 4 about rejection not being personal saved my mental health honestly.",
    "The interview mode thing is so real. I cringe at my old openers.",
    "SOQ framework is going in my notes. Simple and actually useful.",
    "The green flags list is exactly right. I ignored half these signs before.",
    "Hot take on the 24h rule but honestly I agree. Just reply when you have something good.",
    "App fatigue is real and nobody talks about it. Great point.",
    "The 'specific detail' thing works on dating apps and in real life. Universal advice.",
    "I moved off the app after 2 days and we've been on 4 dates now. The timeline is right.",
    "This should be pinned at the top of the dating advice section.",
    "The bad texter point is so valid. My boyfriend was terrible over text at the start.",
    "I sent 'funny' openers for a year. Switched to genuine curiosity. Night and day.",
    "The short replies point is something I needed to hear. Was about to give up on someone.",
    "Point 3 about keeping conversation going is genuinely the hardest part.",
    "The energy about authenticity over game-playing is everything. Real recognises real.",
    "I made every mistake on that list. Now I make different mistakes lol.",
    "The red flag about never asking questions is so easy to miss in the moment.",
    "This is the most practical dating advice post I've seen on here.",
    "The 24h rule is dead. Agreed. The people who wait are usually the ones who lose the match.",
    "SOQ is so simple but it's exactly what's missing from most conversations.",
    "The 'absence creates attraction' thing is real — used it accidentally and it worked.",
    "I screenshot the red/green flag list. Genuinely helpful.",
    "Profile does 80% of the work. This is the hardest truth in dating apps.",
    "The 'one great photo beats five mediocre ones' is advice I needed 2 years ago.",
    "All of this. The people who are 'bad at apps' usually just haven't worked on their profile.",
]

RATE_MY_PROFILE_COMMENTS = [
    "Your second prompt is too vague. 'Have opinions about things' could mean anything.",
    "The travel one is outdated. Drop it or update it to something current.",
    "First photo if you're not looking at the camera. Candid always wins.",
    "Second photo. Direct eye contact in the main photo is important.",
    "Your two truths and a lie is actually good — the TV commercial one is intriguing.",
    "The negroni line works. Keep it. It filters in the right people.",
    "Bio rewrite #3 is better. The specificity is doing the work.",
    "Too try-hard? No. That's a confident bio. Own it.",
    "Your prompts are the problem not the photos if you're getting photo likes but no comments.",
    "The love language prompt is a bit generic. Replace it with something that shows your personality.",
    "The 'roast me' energy in this post already shows good self-awareness. That'll come through.",
    "I'd make the coffee prompt more specific. What coffee? Where? Give people something to latch onto.",
    "Candid photo with natural light always. The rooftop is nice but posed loses to candid.",
    "The negroni line works. It's specific and it signals taste without being pretentious.",
    "Your prompts are safe. Safe = forgettable. Take more risk.",
    "I had the same issue — photo likes but no message likes. Rewrote prompts. Big difference.",
    "Update the travel prompt. 'That was 2 years ago' is doing damage.",
    "The 'we'll get along if' prompt is the weakest. Replace it with something that shows your world.",
    "Two truths and a lie is overused but yours is actually interesting. Keep it.",
    "The confident bio is good. Don't soften it — the right person will appreciate it.",
    "Main photo tip: if you have a photo where you're laughing at something, use that.",
    "The farmers market photo example is perfect. Specific > generic every time.",
    "Profile building is a skill and most people treat it as an afterthought. You're doing the work.",
    "The bio sounds good. The filter it creates is the point — you want to attract the right fit.",
    "Zero matches in 2 months is almost always the main photo. Be ruthless about it.",
]

CATEGORY_COMMENTS = {
    "wins": WINS_COMMENTS,
    "help_me_reply": HELP_ME_REPLY_COMMENTS,
    "dating_advice": DATING_ADVICE_COMMENTS,
    "rate_my_profile": RATE_MY_PROFILE_COMMENTS,
}

# How many comments and votes to seed per post (min, max)
COMMENT_RANGE = {
    "wins": (4, 8),
    "help_me_reply": (5, 10),
    "dating_advice": (4, 8),
    "rate_my_profile": (4, 8),
}
VOTE_RANGE = {
    "wins": (8, 18),
    "help_me_reply": (5, 14),
    "dating_advice": (7, 16),
    "rate_my_profile": (4, 12),
}


class Command(BaseCommand):
    help = "Seed dummy comments, upvotes, and poll votes (idempotent)."

    def handle(self, *args, **options):
        rng = random.Random(42)  # Fixed seed for reproducibility

        # ── 1. Create dummy users ──────────────────────────────────────────
        display_map = {}  # username → display name
        users = []
        for username, display in DUMMY_USERS:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@seed.invalid",
                    "is_active": True,
                },
            )
            users.append(user)
            display_map[username] = display
        self.stdout.write(f"  Users ready: {len(users)}")

        # ── Fix display names on existing seed comments ────────────────────
        fixed = 0
        for username, display in display_map.items():
            fixed += CommunityComment.objects.filter(
                author__username=username,
            ).exclude(author_display_name=display).update(author_display_name=display)
        if fixed:
            self.stdout.write(f"  Fixed {fixed} existing comment display names.")

        # ── 2. Seed per post ───────────────────────────────────────────────
        total_comments = 0
        total_votes = 0
        total_poll_votes = 0

        posts = CommunityPost.objects.filter(is_deleted=False).prefetch_related("comments", "votes")

        for post in posts:
            category = post.category
            comment_bank = CATEGORY_COMMENTS.get(category, WINS_COMMENTS)
            c_min, c_max = COMMENT_RANGE.get(category, (4, 8))
            v_min, v_max = VOTE_RANGE.get(category, (6, 14))

            # Shuffle users differently per post
            post_users = list(users)
            rng.shuffle(post_users)

            # ── Comments ──────────────────────────────────────────────────
            existing_commenter_ids = set(
                post.comments.filter(is_deleted=False, author__isnull=False)
                .values_list("author_id", flat=True)
            )
            eligible_commenters = [u for u in post_users if u.pk not in existing_commenter_ids]
            n_comments = rng.randint(c_min, c_max)
            commenters = eligible_commenters[:n_comments]
            chosen_lines = rng.sample(comment_bank, min(n_comments, len(comment_bank)))

            for user, line in zip(commenters, chosen_lines):
                CommunityComment.objects.get_or_create(
                    post=post,
                    author=user,
                    defaults={
                        "author_display_name": display_map.get(user.username, user.username),
                        "body": line,
                    },
                )
                total_comments += 1

            # ── Upvotes ───────────────────────────────────────────────────
            existing_voter_ids = set(
                post.votes.filter(vote_type="up").values_list("user_id", flat=True)
            )
            eligible_voters = [u for u in post_users if u.pk not in existing_voter_ids]
            n_votes = rng.randint(v_min, v_max)
            voters = eligible_voters[:n_votes]

            for user in voters:
                PostVote.objects.get_or_create(
                    post=post,
                    user=user,
                    defaults={"vote_type": "up"},
                )
                total_votes += 1

            # ── Poll votes ────────────────────────────────────────────────
            try:
                poll = post.poll
            except PostPoll.DoesNotExist:
                continue

            existing_poll_voter_ids = set(
                poll.votes.values_list("user_id", flat=True)
            )
            eligible_poll_voters = [u for u in post_users if u.pk not in existing_poll_voter_ids]
            max_poll = min(18, len(eligible_poll_voters))
            n_poll = rng.randint(min(8, max_poll), max_poll) if max_poll > 0 else 0
            poll_voters = eligible_poll_voters[:n_poll]

            # ~65% send_it, 35% dont_send_it for realism
            for i, user in enumerate(poll_voters):
                choice = "send_it" if (i / len(poll_voters)) < 0.65 else "dont_send_it"
                PollVote.objects.get_or_create(
                    poll=poll,
                    user=user,
                    defaults={"choice": choice},
                )
                total_poll_votes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Added {total_comments} comments, "
                f"{total_votes} upvotes, {total_poll_votes} poll votes."
            )
        )

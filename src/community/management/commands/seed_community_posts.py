from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.models import CommunityPost, PostPoll


POSTS = [
    # ── WINS ────────────────────────────────────────────────────────────────
    {
        "category": "wins",
        "title": "She said yes to the date!! Here's the message that worked",
        "body": (
            "Been using FlirtFix for about 3 weeks and honestly I was skeptical at first. "
            "But last night she said yes to grabbing coffee on Saturday.\n\n"
            "The message I sent after a week of one-word replies:\n\n"
            "\"Ok I need your honest opinion on something — and you seem like someone who actually has good taste. "
            "There's this tiny coffee place that does these insane pour-overs, but I've never had anyone to drag there. "
            "Saturday?\"\n\n"
            "She replied in 4 minutes. Four. Minutes.\n\n"
            "Stop sending the boring 'haha yeah' messages, guys. Give her something to react to."
        ),
        "author_display_name": "jakehm",
        "is_featured": True,
        "days_ago": 3,
    },
    {
        "category": "wins",
        "title": "From ghosted to first date — what actually changed for me",
        "body": (
            "I used to get ghosted constantly. Like, mid-conversation, no warning. "
            "I thought it was my looks or my photos but honestly it was just the way I texted.\n\n"
            "I was being way too available. Replying in 30 seconds, triple-texting when she went quiet, "
            "sending 'you ok?' after 24 hours of silence. Cringe in hindsight.\n\n"
            "What changed: I started treating texting like a ping-pong game. One serve, wait for the return. "
            "Don't over-explain. Leave a little space. It sounds obvious but when you're nervous you forget.\n\n"
            "First date is Wednesday. Wish me luck lol"
        ),
        "author_display_name": "tyler_dates",
        "is_featured": False,
        "days_ago": 7,
    },
    {
        "category": "wins",
        "title": "Matched on Hinge, used FlirtFix, now we've been on 3 dates",
        "body": (
            "Quick update for everyone who's been following my posts — we've now been on 3 dates and she asked "
            "when we're hanging out again before I even had a chance to bring it up.\n\n"
            "The match sat dormant for 5 days before I actually said something worth replying to. "
            "I used the app to help craft a message based on her profile (she had a photo at a farmers market) "
            "and instead of the usual 'do you go there often' nonsense I said something that referenced "
            "a specific detail. She was hooked immediately.\n\n"
            "Moral: specificity > generic compliments every single time."
        ),
        "author_display_name": "remi_w",
        "is_featured": False,
        "days_ago": 11,
    },
    {
        "category": "wins",
        "title": "I was terrible at texting. Not anymore.",
        "body": (
            "Genuine testimony here. I'm an introvert and I overthink every single message. "
            "I'd spend 20 minutes drafting something then delete it and send 'haha' instead.\n\n"
            "Now I use FlirtFix as a starting point, tweak it to sound like me, and send. "
            "The anxiety is basically gone because I'm not starting from a blank page.\n\n"
            "Just got a number from a girl at my gym who I've been too nervous to talk to for 3 months. "
            "Texting her now and it's actually fun. Didn't know texting could be fun."
        ),
        "author_display_name": "quietguy_wins",
        "is_featured": False,
        "days_ago": 14,
    },
    {
        "category": "wins",
        "title": "Finally got out of the friend zone — here's exactly how I replied",
        "body": (
            "Ok so context: I've liked this girl for 8 months. We'd been in the 'talking but not dating' "
            "limbo forever. Every time I tried to push things forward I fumbled it.\n\n"
            "She sent me a meme and instead of just reacting to it I said:\n\n"
            "\"You keep sending me things that make me want to show you more things in person. "
            "When are we actually making that happen?\"\n\n"
            "She called me. On the phone. To say yes.\n\n"
            "It's direct without being desperate. Confident without being weird. "
            "This is the energy I'd been missing for 8 months."
        ),
        "author_display_name": "marcus_f",
        "is_featured": False,
        "days_ago": 18,
    },
    {
        "category": "wins",
        "title": "She double-texted ME for once — I couldn't believe it",
        "body": (
            "I'm not used to being the one who gets chased. Usually I'm the one watching the 'delivered' "
            "status for hours. But yesterday she sent a follow-up message before I'd even replied to her first one.\n\n"
            "Honestly the key was letting the conversation breathe. I stopped trying to keep it going 24/7 "
            "and started only replying when I had something genuinely interesting to say.\n\n"
            "Absence really does create attraction. As annoying as that sounds, it's true."
        ),
        "author_display_name": "dom_texts",
        "is_featured": False,
        "days_ago": 22,
    },
    {
        "category": "wins",
        "title": "Update: the girl I posted about 2 weeks ago — we're official",
        "body": (
            "Two weeks ago I posted here asking for help with a message to a girl I'd been talking to on Bumble. "
            "A bunch of you gave advice and I went with a version that combined a few suggestions.\n\n"
            "We went on a date. Then another. Then last night she asked if we were exclusive and I said yes.\n\n"
            "I genuinely don't think I'd have gotten past that conversation without the help. "
            "Thanks everyone. This community is actually great."
        ),
        "author_display_name": "callum_r99",
        "is_featured": False,
        "days_ago": 28,
    },
    {
        "category": "wins",
        "title": "Tinder match went cold — one message brought her back",
        "body": (
            "She'd gone completely silent for 11 days. I'd basically written it off.\n\n"
            "Then I sent this:\n\n"
            "\"Okay I've been thinking about it and I still have no idea how you feel about pineapple on pizza. "
            "This is information I need.\"\n\n"
            "She replied in an hour with a voice note. A voice note.\n\n"
            "Don't be afraid to restart a dead conversation with something light. "
            "The worst she can do is not reply — which she was already doing anyway."
        ),
        "author_display_name": "n8_dating",
        "is_featured": False,
        "days_ago": 35,
    },

    # ── HELP ME REPLY ────────────────────────────────────────────────────────
    {
        "category": "help_me_reply",
        "title": "She hasn't replied in 2 days — is this too try-hard?",
        "body": (
            "We had a really good conversation going, lots of back and forth, then she just stopped replying "
            "after I asked what she was up to this weekend.\n\n"
            "My planned follow-up:\n\n"
            "\"Hey, not sure if my last message disappeared into the void or you got swept up in something — "
            "either way hope your weekend was good. Still keen to grab that drink if you are.\"\n\n"
            "Does this come across as desperate or is it fine? I feel like doing nothing is also bad. "
            "Vote and drop your thoughts below!"
        ),
        "author_display_name": "alex_t",
        "is_featured": False,
        "days_ago": 2,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "Matched with my gym crush — is this opener too forward?",
        "body": (
            "She goes to my gym and I've seen her around for months. We finally matched on Hinge and I want "
            "to acknowledge that we've seen each other IRL without making it creepy.\n\n"
            "My opener:\n\n"
            "\"Ok I was not expecting to see you here — pretty sure this is the universe's way of telling me "
            "I should've said hi months ago. Hi.\"\n\n"
            "Is this cute or does it come off as a bit much for a first message? Vote!"
        ),
        "author_display_name": "gymrat_hoping",
        "is_featured": False,
        "days_ago": 4,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "She gave me her number but now one-word answers — what do I do?",
        "body": (
            "The conversation on the app was great, she was funny and engaged. I asked for her number and she "
            "gave it no problem. But now over text it's just 'haha', 'yeah', 'lol'.\n\n"
            "I'm thinking of sending:\n\n"
            "\"You were way more interesting on the app, what happened to you\"\n\n"
            "Half-joking, half-real. Will this snap her out of it or backfire badly? Please vote, I need help."
        ),
        "author_display_name": "textingcrisis",
        "is_featured": False,
        "days_ago": 5,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "How do I respond to this without sounding desperate?",
        "body": (
            "She texted: \"I've been so busy lately, sorry for the slow replies!\"\n\n"
            "I want to keep things warm without sounding like I've been waiting by the phone. Options I'm considering:\n\n"
            "A) \"No worries, life gets like that — anything fun keeping you busy?\"\n\n"
            "B) \"Ha, I barely noticed\" (maybe too cold?)\n\n"
            "C) \"You don't owe me explanations, but I'm glad you're back\"\n\n"
            "Which one lands best? Drop a vote and let me know if you have a better option."
        ),
        "author_display_name": "overthinking_obv",
        "is_featured": False,
        "days_ago": 6,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "Reviving a dead Tinder match — does this come across as weird?",
        "body": (
            "We matched 3 weeks ago, had like 5 messages and then both went quiet. I want to restart it "
            "without the awkward 'sorry for disappearing' energy.\n\n"
            "My plan:\n\n"
            "\"Okay hear me out — I just saw something that made me think of our conversation and I'm "
            "choosing to take that as a sign. How have you been?\"\n\n"
            "Or is it better to just open fresh like the gap never happened? Vote!"
        ),
        "author_display_name": "second_chance_sam",
        "is_featured": False,
        "days_ago": 8,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "First message on Bumble after she opened — need help fast",
        "body": (
            "She opened with: \"Ok your third photo immediately made me curious — what's the story there?\"\n\n"
            "(It's a photo of me at a friend's ridiculous themed birthday party, I'm in costume)\n\n"
            "My reply:\n\n"
            "\"Ha, that photo has a lot of lore. Short version: my friend takes birthdays very seriously "
            "and I take my friendships very seriously. Long version involves a scavenger hunt, a rented van, "
            "and a costume I'm not fully ready to explain yet.\"\n\n"
            "Does this hit the right tone or am I overcomplicating it?"
        ),
        "author_display_name": "bumble_respond",
        "is_featured": False,
        "days_ago": 9,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "She liked my photo but didn't reply to my last message — what's the move?",
        "body": (
            "Left on read for 5 days, but then she liked one of my new Instagram photos. "
            "So she's clearly not ignoring me, just not replying to the text.\n\n"
            "Option 1: Ignore the like, send a new text like nothing happened\n"
            "Option 2: Reply to her like on Instagram with a funny comment\n"
            "Option 3: Wait it out and see if she texts\n\n"
            "My lean is Option 2 but I don't want to look like I'm tracking her activity. What would you do? Vote!"
        ),
        "author_display_name": "confused_in_DMs",
        "is_featured": False,
        "days_ago": 10,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "He texts 'lol' to everything I send — what do I actually do here?",
        "body": (
            "He matched with me on Hinge, we had one great 20-minute conversation, and now every single "
            "message I send gets a 'lol' or 'haha yeah'. I've tried being funny, I've tried asking questions, "
            "I've tried being direct. Nothing sticks.\n\n"
            "I want to send:\n\n"
            "\"I feel like I'm getting the slow fade but in slow motion. Just tell me if I'm wasting my time!\"\n\n"
            "Too direct? Not direct enough? Vote on whether I should send this or drop it entirely."
        ),
        "author_display_name": "tired_of_lol",
        "is_featured": False,
        "days_ago": 12,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "Should I double text after being left on read for a week?",
        "body": (
            "The conversation was going well — we'd been talking for about 10 days, made tentative plans "
            "to meet, and then she read my last message and just... nothing. It's been 7 days.\n\n"
            "Planned follow-up:\n\n"
            "\"Hey — I'm going to take a shot in the dark and assume life got crazy. "
            "If you're still down to meet up at some point, I'm around.\"\n\n"
            "My friends are split 50/50. Half say send it, half say move on. Voting closes me out of my misery."
        ),
        "author_display_name": "week_of_silence",
        "is_featured": False,
        "days_ago": 15,
        "poll": True,
    },
    {
        "category": "help_me_reply",
        "title": "She cancelled our date — this is my planned reply, thoughts?",
        "body": (
            "She cancelled 2 hours before we were supposed to meet. Said she had a family thing come up. "
            "Could be real, could be a soft exit. Not sure.\n\n"
            "My planned reply:\n\n"
            "\"No worries at all, hope everything's okay with your family. I'm free most of next week "
            "if you want to reschedule — otherwise no stress.\"\n\n"
            "I want to leave the door open without looking like I'm desperately clinging to it. "
            "Does this do that? Vote!"
        ),
        "author_display_name": "plan_b_needed",
        "is_featured": False,
        "days_ago": 17,
        "poll": True,
    },

    # ── DATING ADVICE ────────────────────────────────────────────────────────
    {
        "category": "dating_advice",
        "title": "Things I wish I knew before I started using dating apps",
        "body": (
            "After 2 years of on-and-off dating apps I've learned a few things the hard way. "
            "Sharing them here because I see a lot of newer people making the same mistakes I did.\n\n"
            "1. Your profile does 80% of the work. If you're getting few matches, fix the profile before "
            "anything else. One great photo beats five mediocre ones.\n\n"
            "2. The first message is a conversation starter, not a performance. Ask something genuine, "
            "not something designed to seem clever.\n\n"
            "3. Move off the app quickly. Two to three days of good conversation then ask to meet. "
            "The longer you wait, the more the connection fades.\n\n"
            "4. Rejection isn't personal. You're a stranger on the internet. It's just pattern matching, "
            "not a verdict on you as a person.\n\n"
            "5. Take breaks. App fatigue is real and it affects your energy in ways you don't notice."
        ),
        "author_display_name": "two_years_in",
        "is_featured": True,
        "days_ago": 6,
    },
    {
        "category": "dating_advice",
        "title": "The texting mistake that's killing your matches (and how to fix it)",
        "body": (
            "It's interview mode. You know the one.\n\n"
            "\"What do you do?\"\n\"What are you into?\"\n\"What kind of music do you like?\"\n\n"
            "One question after another with no personality in between. "
            "She's not applying for a job. She wants to feel something.\n\n"
            "The fix: for every question you ask, share something about yourself first. "
            "\"I've been completely useless this week because I started rewatching a show I've already "
            "seen three times — what's something you're weirdly passionate about right now?\"\n\n"
            "You're giving her something to react to AND asking a question. "
            "That's how a real conversation works."
        ),
        "author_display_name": "no_more_interviews",
        "is_featured": False,
        "days_ago": 10,
    },
    {
        "category": "dating_advice",
        "title": "Why short replies aren't always a bad sign",
        "body": (
            "Hot take: we've all been conditioned to read 'k' as rejection and a paragraph as interest. "
            "But that's not always true.\n\n"
            "Some people are genuinely just bad texters. They're warm, engaged, funny in person "
            "and terrible at sustaining written conversations. I know a few people like this — "
            "I almost wrote off my current girlfriend after 3 days of one-word texts.\n\n"
            "What actually matters: is she still replying? Is she suggesting things or just responding? "
            "Does she seem engaged when you actually talk?\n\n"
            "Suggest moving off the app sooner and you'll know a lot faster than trying to decode message length."
        ),
        "author_display_name": "dont_read_into_it",
        "is_featured": False,
        "days_ago": 16,
    },
    {
        "category": "dating_advice",
        "title": "How to keep the conversation going without running out of things to say",
        "body": (
            "The dreaded dry conversation. Here's a framework that actually works:\n\n"
            "**Statement + Observation + Question (SOQ)**\n\n"
            "Statement: share something about yourself\n"
            "Observation: connect it to something she's said\n"
            "Question: ask something open-ended\n\n"
            "Example: \"I've been trying to cook more at home this year — mostly failing, but it's been "
            "entertaining. You mentioned you like Thai food — do you cook or is that purely a restaurant thing?\"\n\n"
            "This works because it creates momentum. You're not just asking questions into a void — "
            "you're building a picture of yourself while showing genuine interest in her.\n\n"
            "Save this and try it. The difference is immediate."
        ),
        "author_display_name": "convo_coach",
        "is_featured": False,
        "days_ago": 20,
    },
    {
        "category": "dating_advice",
        "title": "Red flags vs green flags in early texting",
        "body": (
            "Things I've learned to look out for:\n\n"
            "🚩 Always responds but never asks questions back\n"
            "🚩 Great energy for 3 days then silence, repeat cycle\n"
            "🚩 Cancels plans with no offer to reschedule\n"
            "🚩 Future plans always vague ('we should hang out sometime')\n"
            "🚩 You feel anxious after every conversation\n\n"
            "✅ Replies even when she's clearly busy\n"
            "✅ Remembers things you've mentioned\n"
            "✅ Suggests the next thing before you do\n"
            "✅ You feel good after talking, not worse\n"
            "✅ Conversation feels easy, not like work\n\n"
            "You can't make someone interested. But you can stop wasting time on people who aren't."
        ),
        "author_display_name": "flag_checker",
        "is_featured": False,
        "days_ago": 25,
    },
    {
        "category": "dating_advice",
        "title": "The 24-hour rule: does waiting to reply actually work?",
        "body": (
            "Controversial opinion: strategic waiting is mostly a myth at this point and everyone knows it.\n\n"
            "The idea was that waiting creates desire. And in the 2010s maybe it did. "
            "Now people have 10 active conversations, 3 apps, and the attention span of a goldfish. "
            "If you wait 24 hours to reply, they've moved on to someone else.\n\n"
            "What actually works: replying when you have something good to say. "
            "Not immediately out of anxiety. Not after 24 hours to seem busy. "
            "When you're genuinely engaged and have something to add.\n\n"
            "Authenticity > game-playing. Every time."
        ),
        "author_display_name": "anti_games",
        "is_featured": False,
        "days_ago": 32,
    },
    {
        "category": "dating_advice",
        "title": "Stop trying to be funny in your opener — here's what works instead",
        "body": (
            "Everyone is trying to be funny. The result is that every opener sounds the same "
            "and none of them land because she's seen 40 of them.\n\n"
            "What cuts through: genuine curiosity. Look at her profile and find one specific thing "
            "that actually interests you, then ask about it like a normal person.\n\n"
            "Not: \"If you were a pizza topping what would you be 😏\"\n"
            "But: \"The photo at what looks like a night market — where was that? I've been trying to "
            "find good street food spots and now I'm on a mission.\"\n\n"
            "It's specific, it's real, and it tells her something about you without trying too hard. "
            "Funny can come later. First impression: genuine."
        ),
        "author_display_name": "no_more_pizza_jokes",
        "is_featured": False,
        "days_ago": 40,
    },

    # ── RATE MY PROFILE ──────────────────────────────────────────────────────
    {
        "category": "rate_my_profile",
        "title": "Roast my Hinge profile — I've had zero matches in 2 months",
        "body": (
            "I'm not going to pretend I don't need help. Zero matches in 2 months on Hinge and I'm "
            "genuinely stumped. I've updated photos twice, changed my prompts, and nothing.\n\n"
            "My current prompts:\n"
            "- \"I'm convinced that\" → good taste in coffee is a personality trait\n"
            "- \"The most spontaneous thing I've done\" → quit my job to travel for 3 months (that was 2 years ago)\n"
            "- \"We'll get along if\" → you have opinions about things\n\n"
            "Main photo is me at a rooftop bar looking fairly normal. No group shots.\n\n"
            "What am I doing wrong? Be brutal, I can take it."
        ),
        "author_display_name": "zero_matches",
        "is_featured": True,
        "days_ago": 4,
    },
    {
        "category": "rate_my_profile",
        "title": "First photo or second photo — which one would you swipe on?",
        "body": (
            "I've been going back and forth on this for weeks so I'm just going to ask the internet.\n\n"
            "Photo 1: Outdoors, natural light, candid, taken by a friend at a hiking trail. "
            "I'm smiling but not at the camera.\n\n"
            "Photo 2: Professional-ish, taken at a rooftop event, looking directly at camera, "
            "good lighting but clearly 'posed'.\n\n"
            "Every person I've asked has given me a different answer. Which would you swipe on first? "
            "Drop your vote and why in the comments — really trying to figure this out."
        ),
        "author_display_name": "photo_dilemma",
        "is_featured": False,
        "days_ago": 9,
    },
    {
        "category": "rate_my_profile",
        "title": "My Hinge prompt answers keep getting ignored — please help",
        "body": (
            "I get likes on my photos but nobody ever comments on my prompts, and when I send prompts "
            "to people I like I never hear back. So something is off.\n\n"
            "Current prompts:\n"
            "- \"Two truths and a lie\" → I've been to 14 countries / I speak basic Mandarin / "
            "I once accidentally ended up in a TV commercial\n"
            "- \"I want someone who\" → doesn't take themselves too seriously\n"
            "- \"My love language\" → acts of service apparently (according to a quiz I took at 1am)\n\n"
            "Are these too generic? Too safe? I feel like the two truths and a lie one should work "
            "but apparently it's not landing."
        ),
        "author_display_name": "prompt_problems",
        "is_featured": False,
        "days_ago": 13,
    },
    {
        "category": "rate_my_profile",
        "title": "Bio rewrite attempt #3 — is this better than the last one?",
        "body": (
            "Previous version (you helped me fix it 2 weeks ago):\n"
            "\"Product designer by day, amateur chef by night. Looking for someone to eat my experiments.\"\n\n"
            "New version:\n"
            "\"I design things for a living and cook things that may or may not be edible on weekends. "
            "If you're the kind of person who has a strong opinion about the right way to make a negroni, "
            "we're going to get along fine.\"\n\n"
            "Longer but more specific. Does it land? I feel like the negroni line either works or "
            "completely puts people off and I can't tell which."
        ),
        "author_display_name": "bio_writer_v3",
        "is_featured": False,
        "days_ago": 19,
    },
    {
        "category": "rate_my_profile",
        "title": "Is my profile too try-hard or just confident?",
        "body": (
            "I've been told my profile comes across as 'too much' but I also don't want to be boring. "
            "Looking for honest feedback.\n\n"
            "My main prompt:\n"
            "\"I'm looking for\" → Someone who's genuinely excited about their life. "
            "I have a lot going on — travel, building things, good food, being outside — "
            "and I want someone who matches that energy, not someone I have to convince to leave the house.\"\n\n"
            "Is this confident or does it sound like I'm setting a high bar to seem impressive? "
            "Real talk please."
        ),
        "author_display_name": "too_much_or_enough",
        "is_featured": False,
        "days_ago": 27,
    },
]


class Command(BaseCommand):
    help = "Seed the database with dummy community posts (idempotent)."

    def handle(self, *args, **options):
        now = timezone.now()
        created_posts = 0
        created_polls = 0

        for data in POSTS:
            published_at = now - timedelta(days=data["days_ago"])
            post, created = CommunityPost.objects.get_or_create(
                title=data["title"],
                category=data["category"],
                defaults={
                    "author": None,
                    "author_display_name": data["author_display_name"],
                    "body": data["body"],
                    "is_featured": data.get("is_featured", False),
                    "is_anonymous": False,
                    "published_at": published_at,
                },
            )
            if created:
                created_posts += 1

            if data.get("poll"):
                _, poll_created = PostPoll.objects.get_or_create(post=post)
                if poll_created:
                    created_polls += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_posts} posts, {created_polls} polls. "
                f"({len(POSTS) - created_posts} already existed, skipped)"
            )
        )

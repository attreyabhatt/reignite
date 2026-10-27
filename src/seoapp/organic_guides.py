"""Original, illustrative reply examples prepared for the October 2026 rollout.

Each guide has ten context-specific replies and two fictional follow-ups. These
are editorial examples, never testimonials or prefilled visitor conversations.
"""
from django.conf import settings

from seoapp.seed_data.search_refresh import example


PREPARED_ON = "2026-10-27"
AUTHOR = {"name": "TryAgainText", "url": "/about/"}
REDIRECTS = {"what-to-text-after-a-date": "what-to-text-after-first-date"}


def editorial_metadata(page):
    modified = page.get("date_modified")
    if not modified:
        return {}
    published = (settings.SEO_GUIDES_PUBLISHED_ON or None
                 if page.get("slug") in NEW_GUIDES else page.get("date_published"))
    return {"author": AUTHOR, "date_modified": max(modified, published or modified),
            "date_published": published}


def section(heading, advice, rows):
    return {"heading": heading, "paragraphs": [advice],
            "examples": [example(*row) for row in rows]}


NEW_GUIDES = {}


def add(slug, heading, description, cluster, answer, groups, conversations, mistakes,
        related, situation="stuck_after_reply"):
    NEW_GUIDES[slug] = {
        "slug": slug, "h1": heading, "title": heading + " | TryAgainText",
        "meta_description": description, "sidebar_label": heading.split(":")[0],
        "cluster": cluster, "date_modified": PREPARED_ON,
        "situation": "spark_deeper_conversation" if situation == "express_feelings" else situation,
        "quick_answer": answer,
        "sample_reply": groups[0][2][0][1], "prefill_text": "", "seo_sections": [],
        "upload_hint": "Paste the recent exchange or upload a chat screenshot with private details removed.",
        "force_show_upload": False,
        "screenshot_tip": "Only include context you are comfortable sharing.",
        "related_slugs": related,
        "guide_content": {"answer": answer,
            "sections": [section(*group) for group in groups] + [
                section("Two example conversations", "These conversations are fictional. Keep the details true to your life and use a follow-up only when the other person participates.", conversations),
                {"heading": "Common mistakes and when to stop", "paragraphs": mistakes, "examples": []},
            ]},
    }


add("how-to-respond-to-wyd", "How to Respond to WYD: Casual and Flirty Replies",
    "Reply to a WYD text with honest, casual or flirty examples. See how to turn 'what are you doing?' into a conversation or a clear invitation.",
    "everyday", "WYD means 'what are you doing?' Answer with one real detail, then leave a small opening: 'Making dinner and hoping the pasta cooperates. What are you up to?' You can also say you cannot chat.",
    [
        ("Give a casual, specific answer", "A normal detail is enough. You do not need to make a quiet evening sound impressive.", [
            ("Cooking", "Making a slightly ambitious dinner. What's happening in your kitchen?", "Use a real activity so there is something natural to discuss."),
            ("Relaxing", "Taking the evening slowly with a film. Have you watched anything good lately?", "A recommendation question connects to what you are doing."),
            ("Outdoors", "Just got back from a walk. The weather finally convinced me to leave the house.", "A statement can invite a response without another question."),
            ("Nothing much", "Nothing exciting, just winding down. How's your evening going?", "An ordinary answer is better than inventing a busy life."),
        ]),
        ("Be flirty when the interest is mutual", "Flirting should fit the relationship. A late message does not require accepting a last-minute invitation.", [
            ("You want to see them", "Deciding whether coffee with you should be part of my weekend.", "This makes your interest clear without assuming they agree."),
            ("You already have a date", "Looking forward to Saturday, honestly. How's your night?", "Mention the plan only if you have actually agreed to it."),
            ("You would prefer a plan", "I'm staying in tonight, but I'd enjoy seeing you another day. Are you free Sunday?", "Offer the kind of invitation you want rather than a reluctant yes."),
        ]),
        ("Say when you are unavailable", "Your reply can describe your availability without an apology or a detailed explanation.", [
            ("Working", "Finishing something for work. I can chat after seven.", "Give a time only if it is realistic."),
            ("With friends", "Out with friends, so I'm putting my phone away. Enjoy your evening!", "You can be present with other people."),
            ("Going to sleep", "Heading to bed. Hope the rest of your night is good.", "This closes the exchange without promising another message."),
        ]),
    ], [
        ("From a real detail to a shared interest", "Them: Wyd?\nYou: Trying a new soup recipe.\nThem: Any good?\nYou: Surprisingly, yes. I'll send you the recipe if you like ginger.", "Answer their follow-up before introducing another topic."),
        ("From checking in to making plans", "Them: Wyd?\nYou: Home for tonight. I'd like to see you this weekend, though.\nThem: Sunday works.\nYou: Great. Coffee at two?", "A clear invitation works better than hinting indefinitely."),
    ], ["Avoid pretending to be busy to provoke a reaction, or sending explicit replies to a casual question without mutual context.", "If the exchange stays one-sided, leave it there. You do not have to turn every WYD into a date."],
    ["how-to-respond-to-how-was-your-day", "how-to-respond-to-hey", "how-to-end-a-text-conversation"])

add("how-to-respond-to-how-was-your-day", "How to Respond to How Was Your Day: Reply Examples",
    "Answer 'how was your day?' with specific, warm replies for good days, hard days and quiet evenings, with two example follow-up conversations.",
    "everyday", "Give a brief, honest picture of the day: one event, how it felt, and an opening for them. 'Busy, but a long walk rescued the evening. How did your meeting go?' is more personal than 'fine, you?'",
    [
        ("Share a good or ordinary day", "Choose one moment instead of listing your entire schedule. Ask about something they have already mentioned when possible.", [
            ("A small win", "Pretty good! I finally finished the thing I'd been putting off. What was your highlight?", "A small accomplishment offers a real point of connection."),
            ("A quiet day", "A quiet one: work, groceries and an excellent sandwich. Sometimes that's enough.", "A peaceful day does not need embellishment."),
            ("Something funny", "Mostly normal, except I waved back at someone who was definitely waving at the person behind me.", "Use a harmless story that actually happened."),
            ("A shared interest", "Good! I started the book you recommended. You were right about the opening chapter.", "Acknowledging their recommendation makes this personal."),
        ]),
        ("Answer when the day was difficult", "You can be honest without sharing more than you want. It helps to say whether you want to talk or change the subject.", [
            ("You want to talk", "A bit rough. Could I tell you about it for a few minutes?", "Ask if they have space for the conversation."),
            ("You want a distraction", "Long day, honestly. I'd rather hear something good from yours.", "This names your preference without demanding entertainment."),
            ("You need rest", "Quite tiring. I'm going to have an early night, but I appreciate you checking in.", "Warmth and a clear boundary can coexist."),
        ]),
        ("Add warmth without forcing flirtation", "Match the familiarity you already have. Do not imply a relationship that has not developed.", [
            ("A warm check-in", "Better now that I have a moment to talk with you. How are you doing?", "Use this when you mean the warmth."),
            ("Looking ahead", "Productive, and now I'm looking forward to our coffee tomorrow.", "A real shared plan gives the message a natural ending."),
            ("Return to their news", "Mine was fairly calm. More importantly, how did your presentation go?", "Follow up only on something they actually told you."),
        ]),
    ], [
        ("Let one detail become a conversation", "Them: How was your day?\nYou: Good! I tried that little bakery you mentioned.\nThem: Did you get the cinnamon roll?\nYou: I did. I may need to go back for the lemon cake.", "A shared recommendation does the work of starting a topic."),
        ("Be honest about low energy", "Them: How was your day?\nYou: Draining. I don't have much conversation in me tonight.\nThem: Want to talk tomorrow?\nYou: That would be lovely. Thanks for understanding.", "You can accept support without continuing a chat when tired."),
    ], ["Avoid turning every check-in into a performance or a long complaint without checking the other person's availability.", "If they give a short response, do not assume you answered incorrectly. They may be occupied; let the conversation breathe."],
    ["how-to-respond-to-wyd", "what-to-say-next-over-text", "how-to-respond-to-im-busy-text"])

add("how-to-reply-to-haha-or-lol", "How to Reply to Haha or LOL Without Forcing the Chat",
    "Not sure what to say after haha or LOL? See natural follow-ups to a joke, ways to change topics, and examples of when to let the conversation end.",
    "everyday", "A laugh can be a complete response. Continue only if you have something relevant: add a small detail to the joke, return to a shared topic, or leave the conversation there. You do not need to send another joke to earn a longer reply.",
    [
        ("Add one detail to a joke", "Use these after your own funny story. They make sense because they continue the same moment, not because LOL has a secret meaning.", [
            ("A cooking mishap", "The recipe said 'easy.' I have a few follow-up questions for the author.", "This fits an actual cooking story."),
            ("Getting lost", "At least my accidental detour came with a very good coffee shop.", "A detail moves the story forward."),
            ("A pet story", "The cat has declined to comment on the damage.", "Use a pet joke only when it matches what you were discussing."),
            ("A harmless mistake", "I'd like to say I learned something, but let's not make promises.", "Keep the humor directed at your own situation."),
        ]),
        ("Return to something you both care about", "Once the joke is finished, a genuine topic is better than testing whether they will laugh again.", [
            ("An earlier plan", "Anyway, did you manage to book your trip?", "Return to something they had already brought up."),
            ("A recommendation", "On a more useful note, I finally listened to that album you mentioned.", "Offer your real reaction next rather than stopping at the announcement."),
            ("Mutual plans", "Now that my comedy career is settled, are we still good for Saturday?", "Use this only when you already have a tentative plan."),
        ]),
        ("Let a natural ending be an ending", "You can send a warm closer if you want, but a completed exchange does not require another message.", [
            ("You are heading out", "Glad that entertained you. I'm off to meet a friend. Have a good evening!", "A real closing avoids leaving a new question."),
            ("They need to work", "I'll let you get back to it. Hope the rest of the shift is calmer.", "Acknowledge their actual availability."),
            ("You will meet soon", "I'll save the rest of that story for coffee tomorrow.", "A shared plan can carry the conversation forward offline."),
        ]),
    ], [
        ("Carry on the same story", "Them: Lol.\nYou: The cake survived. The decorating is more abstract art.\nThem: I need to see this.\nYou: Prepare to lower your expectations.", "The follow-up works because they ask for more."),
        ("Allow the pause", "Them: Haha.\nYou: Glad you appreciated my terrible navigation. Enjoy your evening!\nThem: You too!", "A friendly close can be a successful conversation."),
    ], ["Do not interpret a single LOL as proof of attraction or rejection. Avoid 'that's all you have to say?' and repeated messages asking for attention.", "If replies repeatedly end the exchange, step back. When they have asked you to stop, do not use a new joke as a reason to contact them."],
    ["what-to-say-next-over-text", "how-to-respond-to-dry-texts", "how-to-end-a-text-conversation"])

add("how-to-respond-to-good-morning-text", "How to Respond to a Good Morning Text",
    "Find friendly and flirty good morning replies, including busy mornings and new dating connections. Use specific examples that match your relationship.",
    "everyday", "Return the greeting with the amount of warmth you actually feel. 'Good morning! Hope your first day goes well' is personal when you know their plans. A simple 'Morning! Have a good day' is also enough.",
    [
        ("Keep the greeting easy", "A morning message does not require an immediate conversation. Short and kind is a complete answer.", [
            ("A simple greeting", "Good morning! Hope your day's off to a good start.", "This works without implying romantic interest."),
            ("A slow start", "Morning! Still negotiating with my alarm clock.", "A small true detail gives the message personality."),
            ("A shared routine", "Good morning! I'm about to make my first coffee. How's your morning?", "Only ask if you have time for an answer."),
            ("Their plans", "Morning! Good luck with your first day today.", "Remembering a real detail is more personal than a borrowed line."),
        ]),
        ("Be warmer when you are dating", "Warmth should match the relationship and your actual feelings. Avoid pet names that would be unwelcome.", [
            ("After a good date", "Good morning! I'm still smiling about our conversation last night.", "Mention something you genuinely enjoyed."),
            ("Seeing them later", "Morning! Looking forward to seeing you this evening.", "This refers to an agreed plan rather than inventing one."),
            ("A mutual routine", "Good morning, you. Hope today is kind to you.", "Use a familiar tone only if it feels natural between you."),
        ]),
        ("Set expectations on a busy morning", "You can acknowledge the message while explaining that you will be away from your phone.", [
            ("An early meeting", "Morning! Heading into meetings, but thank you for the message.", "No lengthy excuse is necessary."),
            ("You reply later", "A slightly late good morning from me! How did your morning go?", "A delayed reply does not need a dramatic apology."),
            ("You prefer less frequent texting", "Morning! I enjoy hearing from you, though I'm usually offline before work.", "This explains your habits without criticizing theirs."),
        ]),
    ], [
        ("Remember their plans", "Them: Good morning!\nYou: Morning! Good luck with the presentation.\nThem: Thanks, I'm nervous.\nYou: That makes sense. Hope it goes smoothly; tell me about it when you're free.", "Support them without demanding live updates."),
        ("Leave space for the day", "Them: Morning :)\nYou: Good morning! I'm off for a walk before work. Have a good day.\nThem: Enjoy the walk!", "A greeting can remain brief and warm."),
    ], ["Avoid treating a morning greeting as a daily obligation or testing them by deliberately withholding a reply.", "If you do not want a romantic routine, keep your answer friendly and explain your preference when needed. You do not owe constant availability."],
    ["how-to-respond-to-how-was-your-day", "how-to-reply-to-good-night-text", "how-to-respond-to-im-busy-text"])

add("how-to-reply-to-good-night-text", "How to Reply to a Good Night Text: Warm and Simple Replies",
    "Reply to good night with friendly, affectionate or lightly flirty messages. See ways to close the chat without starting another long conversation.",
    "warm", "A good night text usually closes the conversation. Match the warmth and let them sleep: 'Good night! I enjoyed talking with you.' Save questions and complicated topics for when you are both available.",
    [
        ("Keep the closing simple", "A brief reply can communicate care without adding another topic.", [
            ("Friendly", "Good night! Hope you sleep well.", "This is warm without assuming a relationship."),
            ("After a long day", "Sleep well. Hope tomorrow feels a little easier.", "Acknowledge the day they described."),
            ("After a good chat", "Good night! I really enjoyed catching up.", "Name your enjoyment without needing a response."),
            ("An early start", "Night! Good luck with the early train tomorrow.", "Use the detail only if you know their plans."),
        ]),
        ("Add affection when it fits", "Affection should be welcome and mutual. You do not need to escalate a routine closing.", [
            ("New dating connection", "Good night. I'm glad we made time to talk.", "It is warm without overstating your closeness."),
            ("A shared joke", "Sleep well. I'll try not to dream about that disastrous board-game score.", "A genuine callback makes this specific."),
            ("An agreed date", "Night! Looking forward to Saturday.", "This keeps the next plan clear without reopening scheduling."),
        ]),
        ("Close or reply at a different time", "If you see the message in the morning, reply then. You do not have to wake someone for a closing text.", [
            ("You are also going to bed", "I'm calling it a night too. Sleep well!", "Both people can leave the conversation."),
            ("You missed the text", "I fell asleep before I saw this. Good morning! Hope you slept well.", "A simple explanation is enough."),
            ("You will be offline", "Good night. I'm putting my phone away now; talk another time.", "Set a clear ending rather than continuing with questions."),
        ]),
    ], [
        ("Close after a pleasant conversation", "Them: I should get some sleep. Good night!\nYou: Good night! I loved hearing about your trip. Sleep well.\nThem: Thanks, you too!", "The exchange ends without requiring another topic."),
        ("Pick it up in the morning", "Them: Night!\nYou, next morning: I was already asleep. Morning!\nThem: Morning, how are you?\nYou: Rested, for once. How about you?", "A delayed closing can become a normal greeting later."),
    ], ["Avoid sending repeated 'are you asleep?' texts, demanding a pet name back, or introducing a serious disagreement as they leave.", "One unanswered good night does not need a follow-up. Respect their rest and your own."],
    ["how-to-respond-to-good-morning-text", "how-to-end-a-text-conversation", "sincere-text-messages"])

add("how-to-respond-to-i-miss-you", "How to Respond to I Miss You: Honest Reply Examples",
    "Find honest replies to 'I miss you' when you feel the same, feel unsure, or do not want to reconnect. Includes warm responses and clear boundaries.",
    "warm", "Answer according to how you actually feel. Say 'I miss you too' when it is true, acknowledge the message without promising more when you are unsure, or clearly decline contact when you do not want it.",
    [
        ("When you feel the same", "You can return the feeling and suggest a realistic way to connect. Missing someone does not require making an immediate plan.", [
            ("Return the feeling", "I miss you too. I've been thinking about our last evening together.", "Use a real shared memory."),
            ("Make a plan", "I miss you too. Would you like to get coffee this weekend?", "A specific invitation leaves room for a yes or no."),
            ("Long distance", "I miss you. Could we make time for a call on Sunday?", "Suggest something you can both realistically do."),
            ("You cannot meet yet", "I miss you too. I can't visit this week, but I'd love to hear your voice later.", "Warmth does not require hiding a practical limit."),
        ]),
        ("When you are unsure", "You can acknowledge their vulnerability without mirroring feelings you do not have.", [
            ("You want to talk slowly", "It's good to hear from you. I'd like to catch up, but I want to take things slowly.", "State the pace you are comfortable with."),
            ("You need to think", "Thank you for telling me. I need some time to work out how I feel.", "Do not promise a romantic answer later."),
            ("You care as a friend", "I care about you and miss our chats. For me, that feeling is friendship.", "Name the kind of connection you are offering."),
        ]),
        ("When you do not want to reconnect", "A kind response can still be firm. You are not obliged to restart a relationship because someone misses you.", [
            ("An ex reaches out", "I appreciate you being honest. I don't want to restart our relationship.", "Avoid a vague 'maybe later' if your decision is no."),
            ("You need distance", "I understand, but staying in touch isn't right for me. Please respect the space I've asked for.", "Refer to the boundary without reopening a debate."),
            ("You want no further contact", "I don't want further contact. Please don't message me again.", "A direct boundary is appropriate when gentler wording would be unclear."),
        ]),
    ], [
        ("Turn mutual warmth into a plan", "Them: I miss you.\nYou: I miss you too. Want to take a walk on Sunday?\nThem: I'd like that.\nYou: Great. Shall we meet at the park entrance at three?", "Plans follow mutual interest, rather than replacing an honest answer."),
        ("Hold a clear boundary", "Them: I miss you. Can we try again?\nYou: I don't want to restart the relationship. I wish you well.\nThem: Are you sure?\nYou: Yes. Please respect my decision.", "You do not have to continue explaining after a clear refusal."),
    ], ["Do not say you miss someone just to avoid an uncomfortable moment. Avoid using jealousy, guilt or silence as a test.", "You can choose not to reply to unwanted contact, especially after an existing boundary. If you do reply, do not promise future contact you do not want."],
    ["how-to-respond-to-thinking-of-you", "how-to-confess-feelings-over-text", "how-to-end-a-text-conversation"], "express_feelings")

add("how-to-respond-to-thinking-of-you", "How to Respond to a Thinking of You Text",
    "See warm, friendly and flirty replies to 'thinking of you,' plus honest responses when you do not share the feeling or need space.",
    "warm", "Acknowledge the thought, then match the kind of connection you want: 'That's lovely to hear. I was thinking about our walk too.' You can appreciate the message without returning romantic interest.",
    [
        ("Return genuine warmth", "A real memory or detail makes the response feel personal without requiring a grand declaration.", [
            ("A shared memory", "That made me smile. I was remembering our very competitive game of cards.", "Use a memory you both actually share."),
            ("You feel the same", "I've been thinking of you too. How has your week been?", "Ask only if you have room to talk."),
            ("A new connection", "That's sweet. I really enjoyed getting to know you on Saturday.", "Ground the warmth in an actual meeting."),
            ("A mutual plan", "A lovely message to receive. I'm looking forward to seeing you tomorrow.", "Refer to an agreed plan."),
        ]),
        ("Keep it friendly or supportive", "Thinking of someone can be platonic. Respond to the context rather than assuming a hidden romantic message.", [
            ("A friend checks in", "Thank you. I appreciate you checking in. How are you doing?", "This is caring without implying romance."),
            ("During a difficult week", "Thank you. This week's been a lot, and your message means something.", "You can acknowledge support without sharing details."),
            ("You cannot talk", "That's kind of you. I'm low on energy tonight, but I appreciate it.", "A boundary does not cancel the gratitude."),
        ]),
        ("Respond when your feelings differ", "Clarity is kinder than returning affection you do not feel. You do not need to justify every boundary.", [
            ("You want friendship", "I value our friendship. I want to be clear that I don't feel a romantic connection.", "Use this when the romantic intent is clear, not as an assumption."),
            ("You need space", "Thank you, but I need some space and won't be keeping up a conversation.", "Say what the boundary means in practice."),
            ("You do not want to reconnect", "I understand you're reaching out, but I don't want to reconnect.", "Avoid a vague future possibility if it is not real."),
        ]),
    ], [
        ("A shared memory opens the conversation", "Them: Thinking of you.\nYou: That made me smile. I walked past the cafe from our date.\nThem: Did you go in?\nYou: Not today. I'd enjoy going back together sometime.", "The invitation follows a real shared detail."),
        ("Accept care without continuing tonight", "Them: Thinking of you. Hope you're okay.\nYou: Thank you. I'm tired and taking a quiet night.\nThem: No need to reply, just wanted you to know.\nYou: I appreciate that.", "A supportive exchange does not need to become a long conversation."),
    ], ["Avoid assuming every affectionate message asks for romance, or sending a stronger declaration than you mean.", "If a boundary has already been stated, you may leave unwanted contact unanswered. You do not owe reassurance at the expense of that boundary."],
    ["how-to-respond-to-i-miss-you", "sincere-text-messages", "how-to-respond-to-a-compliment-over-text"], "express_feelings")

add("what-to-say-after-thank-you-for-a-compliment", "What to Say After Someone Thanks You for a Compliment",
    "Wondering what to say after 'thank you' to a compliment? Find natural replies, ways to move the conversation forward, and when to leave it there.",
    "warm", "A thank-you can finish the exchange. Say 'You're welcome' or briefly reinforce what you meant, then continue only if there is a genuine topic. A compliment does not create an obligation to flirt back.",
    [
        ("Let the compliment stand", "A short acknowledgment gives the other person room to accept the compliment without having to reassure you.", [
            ("Simple", "You're welcome!", "A complete exchange does not need an extra question."),
            ("Sincere", "Of course. I meant it.", "Use this without demanding they agree with your assessment."),
            ("Their work", "You put a lot into it, and it shows.", "Keep the focus on their effort when that is what you praised."),
            ("A shared moment", "I'm glad I got to hear you play.", "A specific observation feels more natural than another broad compliment."),
        ]),
        ("Move to a connected topic", "Ask about the thing you actually noticed, rather than stacking compliments until you get a bigger reaction.", [
            ("A creative project", "How did you come up with the idea for that painting?", "This follows an actual compliment about their art."),
            ("A recommendation", "Where did you find that jacket? The shop sounds worth a visit.", "Ask only if you are interested in the answer."),
            ("An achievement", "Are you doing anything to celebrate?", "A relevant question works after congratulations."),
        ]),
        ("Use warmth without asking for a reward", "If mutual interest already exists, a gentle follow-up is enough. If it does not, do not treat politeness as a romantic signal.", [
            ("You are already dating", "You make it pretty easy to say nice things.", "This suits established, welcome flirtation."),
            ("You will see them soon", "Looking forward to hearing more about it when we meet.", "Use an agreed meeting rather than assuming an invitation."),
            ("The chat is ending", "You're welcome. Hope the rest of your evening is good!", "A kind closing lets the exchange end."),
        ]),
    ], [
        ("Turn a specific compliment into interest", "You: Your photos from the hike are lovely.\nThem: Thank you!\nYou: Was that the coast path you mentioned?\nThem: Yes, we finally went last weekend.", "The follow-up asks about the experience rather than fishing for a compliment back."),
        ("Leave the compliment alone", "You: You explained that really clearly.\nThem: Thanks, I was nervous.\nYou: You're welcome. You put the work in, and it showed.", "An acknowledgment can finish warmly without a new topic."),
    ], ["Avoid 'just thank you?' or asking why they did not compliment you back. A compliment is a gift, not a transaction.", "If their reply closes the conversation, accept that. Repeated compliments can feel pressuring when the interest is not mutual."],
    ["how-to-respond-to-a-compliment-over-text", "what-to-say-next-over-text", "how-to-end-a-text-conversation"])

add("what-to-text-before-first-date", "What to Text Before a First Date: Plans and Conversation",
    "Know what to text between agreeing to a first date and meeting. See examples for clear plans, light check-ins, practical changes and a calm confirmation.",
    "dating", "Once you have agreed to meet, make the day, time and place clear. Between then and the date, keep chatting if it feels mutual; there is no required texting schedule. Confirm near the date without repeatedly checking their interest.",
    [
        ("Turn an idea into a clear plan", "A date is easier to attend when both people know the practical details. Offer options without making every decision for them.", [
            ("Suggest a place", "Would the cafe by the station work for you on Saturday afternoon?", "A public, practical option is easy to accept or change."),
            ("Set a time", "Great. Does two o'clock suit you?", "One clear question resolves the missing detail."),
            ("Check preferences", "Would you prefer coffee or a walk somewhere busy?", "Give a small choice rather than a questionnaire."),
            ("Agree a meeting point", "Let's meet outside the main entrance so we're not searching for each other inside.", "Use a simple location you both understand."),
        ]),
        ("Keep the gap natural", "A check-in should be something you want to share, not a strategy to keep someone interested. Let them have a life between messages.", [
            ("A real callback", "I finally heard the song you recommended. The chorus has been in my head all day.", "Only use the detail if you followed the recommendation."),
            ("A light check-in", "Hope your week's going well. Did your interview happen yet?", "Remember a real event they mentioned."),
            ("You prefer meeting first", "I've enjoyed chatting. I'll save the rest of that story for Saturday.", "This can close the chat warmly without disappearing."),
        ]),
        ("Handle practical updates", "Be direct about changes. A confirmation clarifies a plan; it should not become a demand for reassurance.", [
            ("Confirm tomorrow", "Looking forward to tomorrow. Still good for two at the station cafe?", "Keep the details in one message."),
            ("A minor delay", "My train is running late. I expect to be about ten minutes behind; sorry for the wait.", "Give an honest estimate rather than leaving them guessing."),
            ("A venue problem", "The cafe's closed Saturday. Would the one across the square work instead?", "Offer a concrete alternative."),
        ]),
    ], [
        ("Agree the plan once", "You: Want to get coffee Saturday?\nThem: Yes, afternoon works.\nYou: Two at the cafe by the station?\nThem: Perfect.\nYou: Great, looking forward to meeting you.", "The details are settled without extending the planning indefinitely."),
        ("Leave room between messages", "You: Hope the exam went okay.\nThem: It did, thanks! I'm catching up on sleep now.\nYou: Well earned. Rest up; see you Saturday.", "A supportive closing respects their energy."),
    ], ["Avoid manufacturing daily check-ins, sending several confirmations, or treating a slower reply as proof the date is off.", "If the plan is still unconfirmed close to your leaving time, ask once and set your own practical cutoff. Do not travel to a vague plan or keep pursuing a refusal."],
    ["how-to-confirm-a-date-over-text", "how-to-reschedule-a-date-over-text", "what-to-text-after-first-date"], "ask_her_out")

add("how-to-reschedule-a-date-over-text", "How to Reschedule a Date Over Text Without Being Vague",
    "Need to move a date? Use clear rescheduling messages with an apology, realistic alternative plans and examples for when you cannot offer another time.",
    "dating", "Tell them promptly that you cannot make the agreed plan, acknowledge the inconvenience, and offer a realistic alternative if you want to meet. 'I'm sorry, I can't do Thursday now. Would Saturday afternoon work instead?' is clear.",
    [
        ("Offer an alternative you can keep", "You do not need to share private details. A brief truthful reason and a useful alternative are enough.", [
            ("Work changes", "I'm sorry, work has changed my Thursday plans. Could we move coffee to Saturday at two?", "Offer a specific time you can commit to."),
            ("You are unwell", "I'm not feeling well and need to cancel tonight. I'm sorry for the short notice. Could I check in about next weekend when I'm better?", "Avoid promising recovery by a particular day."),
            ("A family commitment", "A family commitment has come up, so I can't make Sunday. Would Wednesday evening suit you instead?", "Keep private details private."),
            ("Two possible times", "I'm sorry to move our plans. I can do Friday after six or Sunday afternoon if either works for you.", "A small number of real options makes planning easier."),
        ]),
        ("Handle short notice carefully", "Acknowledge their time, especially if they may already be travelling. Avoid turning the apology into a request that they comfort you.", [
            ("Same-day change", "I'm sorry for the late change. I can't make tonight, and I realise you set time aside. Could we try Saturday instead?", "Name the inconvenience without excessive self-criticism."),
            ("You are delayed rather than cancelling", "I'm running about twenty minutes late. Would you prefer to wait or move this to another day?", "Let them choose what works for their time."),
            ("A second change", "I'm sorry I've had to move this twice. I understand if you don't want to rearrange again.", "Repeated changes deserve acknowledgment and room for a no."),
        ]),
        ("Be honest when another date is uncertain", "Rescheduling is different from declining. Do not offer a future meeting simply to soften a decision you have already made.", [
            ("You cannot offer a day yet", "I can't commit to a new date this week. I don't want to keep you waiting; I'll reach out if my schedule clears.", "Only reach out later if contact remains welcome."),
            ("Their alternatives do not work", "Neither of those works for me, unfortunately. I could do next Tuesday, but I understand if that's too far away.", "State a practical limit without negotiating endlessly."),
            ("You do not want to meet", "I've thought about it and don't want to continue dating. I'm sorry to change the plan, and I wish you well.", "A clear decline is more respectful than a fake scheduling conflict."),
        ]),
    ], [
        ("Agree a replacement plan", "You: I'm sorry, I can't make Thursday. Could we do Saturday afternoon?\nThem: Saturday works.\nYou: Thank you. Two at the same cafe?\nThem: Yes.\nYou: Great, and thanks for being flexible.", "Confirm the new details instead of leaving the alternative vague."),
        ("Accept their decision", "You: I need to move our date again. I'm sorry.\nThem: I don't think this is working for me.\nYou: I understand. Thanks for being clear, and I wish you well.", "Do not argue someone into another arrangement."),
    ], ["Avoid waiting until the last moment when you already know you cannot attend. Do not invent emergencies or repeatedly say 'sometime soon.'", "If they decline to rearrange, accept it. A rescheduling request is an invitation, not a claim on their availability."],
    ["how-to-confirm-a-date-over-text", "what-to-text-when-she-cancels", "how-to-politely-decline-a-second-date"], "ask_her_out")

add("how-to-answer-what-are-you-looking-for", "How to Answer What Are You Looking For on Dating Apps",
    "Answer 'what are you looking for?' honestly on a dating app. Find examples for relationships, casual dating, uncertainty and different intentions.",
    "dating", "Describe your current intentions plainly and leave room for the other person to decide if they fit. 'I'm looking for a relationship, but I'd like to get to know someone gradually' is clearer than saying whatever you think they want to hear.",
    [
        ("When you want a relationship", "Talk about the kind of connection you want to build without promising a future with someone you have just met.", [
            ("Clear and simple", "I'm looking for a relationship with someone I enjoy spending time with. I like getting to know people at a steady pace.", "It states both your aim and your pace."),
            ("Intentional dating", "I'd like something lasting if the connection is right. I'm here to actually meet and see how we get on.", "An intention is not a guarantee of compatibility."),
            ("After a break", "I'm ready to date again and would like a relationship. I'm taking it slowly rather than rushing into one.", "Share only the history you want to share."),
            ("Return the question", "Ultimately a relationship, with room to see whether we fit. What are you hoping to find?", "Give your answer before asking theirs."),
        ]),
        ("When you want something casual or feel unsure", "People can make informed choices only when your message matches your actual intentions.", [
            ("Casual dating", "I'm looking for casual dating rather than a committed relationship. I understand if that's not what you want.", "Avoid implying you will change your mind to keep the chat going."),
            ("You are still figuring it out", "I'm open to dating, but I'm not sure what level of commitment I can offer yet. I want to be upfront about that.", "Uncertainty is useful information, not a reason to promise more."),
            ("You prefer a slower pace", "I'm interested in meeting people, though I need time before I know whether I want a relationship with someone.", "This describes your process without asking them to wait indefinitely."),
        ]),
        ("When your intentions differ", "A mismatch can be resolved respectfully. Do not argue that the other person's preference is unreasonable.", [
            ("They want casual, you do not", "Thanks for being clear. I'm looking for a relationship, so I don't think we're a match.", "Clarity lets both people move on."),
            ("They want commitment, you do not", "I can't offer the relationship you're looking for, and I don't want to give you the wrong impression.", "Do not keep a connection going through ambiguity."),
            ("Your intentions have changed", "I need to be honest that what I can offer has changed. I understand if that doesn't work for you.", "Communicate the change rather than relying on old assumptions."),
        ]),
    ], [
        ("Find compatible intentions", "Them: What are you looking for?\nYou: A relationship, if we connect. I like taking time to get to know someone.\nThem: Same here.\nYou: Good to know. Would you like to meet for coffee this weekend?", "A shared intention can lead to a normal invitation."),
        ("Accept a mismatch", "Them: I'm only looking for something casual.\nYou: Thanks for telling me. I'm looking for a relationship, so I don't think this fits.\nThem: Fair enough.\nYou: Wishing you well.", "A mismatch does not require persuading either person to change."),
    ], ["Avoid vague promises, copying a supposedly perfect answer, or hiding intentions because you fear losing the match.", "If your intentions differ, stop trying to negotiate away the difference. If someone pressures you to change a boundary, you can leave the conversation."],
    ["how-to-ask-her-out-over-text", "what-to-text-before-first-date", "how-to-end-a-text-conversation"], "express_feelings")

add("how-to-politely-decline-a-second-date", "How to Politely Decline a Second Date Over Text",
    "Decline a second date with clear, considerate messages. Find examples for different connections, a reply to an invitation and holding a boundary.",
    "dating", "Thank them for the time together and clearly say you do not want another date. 'Thanks for meeting me. I didn't feel the connection I'm looking for, so I don't want to plan another date. Wishing you well' is enough.",
    [
        ("Be kind and clear after one date", "You do not need to provide a list of faults. A brief statement about your decision is usually more considerate than a detailed review.", [
            ("A simple decline", "Thanks for meeting me. I didn't feel the connection I'm looking for, so I don't want to arrange another date.", "This states a decision without blaming them."),
            ("You enjoyed talking", "I enjoyed our conversation, but I don't feel a romantic connection. I wish you well.", "Enjoying a conversation does not require a second date."),
            ("They invite you again", "Thank you for asking. I don't want to go on another date, but I appreciate the time we spent together.", "Answer the invitation directly."),
            ("You had said maybe", "I've thought about it and don't want to plan a second date. I'm sorry I wasn't clearer earlier.", "Correct an ambiguous answer instead of disappearing."),
        ]),
        ("Explain only what you want to explain", "Be truthful about your decision. Do not promise friendship or a future date simply to soften the message.", [
            ("Different intentions", "I think we're looking for different things, so I don't want to continue dating.", "Name a genuine mismatch without debating it."),
            ("You are stepping back", "I've realised I don't want to continue dating right now. I won't be arranging another date.", "Use this only if it is true."),
            ("Friendship, if genuinely wanted", "I don't feel a romantic connection. I'd be open to friendship, but I understand if that isn't right for you.", "Friendship is an offer, not a consolation they must accept."),
        ]),
        ("Hold the boundary if they push", "You can repeat your decision once. You are not required to continue an unwanted exchange.", [
            ("They ask for another chance", "I understand you're disappointed, but my decision is no.", "Acknowledge the feeling without reopening the decision."),
            ("They ask for reasons", "I don't have more to add. I don't want to continue dating.", "You do not owe a detailed defence of your preference."),
            ("They keep messaging", "I've been clear that I don't want further contact. Please stop messaging me.", "Use a firm boundary when continued contact is unwanted."),
        ]),
    ], [
        ("Answer a second-date invitation", "Them: I had a good time. Dinner again Friday?\nYou: Thank you for meeting me. I didn't feel a romantic connection, so I don't want another date.\nThem: Thanks for letting me know.\nYou: Wishing you well.", "The response answers the invitation without creating a false scheduling problem."),
        ("Do not debate a refusal", "Them: Are you sure? We should try once more.\nYou: I'm sure. I don't want another date.\nThem: I think you're being unfair.\nYou: I'm ending this conversation now.", "Once the decision is clear, you may stop responding."),
    ], ["Avoid fake busy schedules, 'maybe later' when you mean no, or unnecessary criticism of their appearance or personality.", "If contact feels threatening or unsafe, you do not owe another explanation. Use the platform's blocking and reporting options and seek support from someone you trust."],
    ["what-to-text-after-first-date", "how-to-end-a-text-conversation", "how-to-answer-what-are-you-looking-for"], "express_feelings")


for _page, _label in zip(NEW_GUIDES.values(), (
    "Reply to WYD", "How Was Your Day", "Haha and LOL", "Good Morning Replies",
    "Good Night Replies", "I Miss You Replies", "Thinking of You Replies", "After a Compliment",
    "Before a First Date", "Reschedule a Date", "Your Dating Intentions", "Decline a Second Date",
)):
    _page["sidebar_label"] = _label

# Each new guide receives links from two established guides in the same release.
INCOMING_LINKS = {
    "what-to-say-next-over-text": list(NEW_GUIDES),
    "how-to-respond-to-hey": list(NEW_GUIDES)[:4],
    "sincere-text-messages": list(NEW_GUIDES)[4:8],
    "how-to-ask-her-out-over-text": list(NEW_GUIDES)[8:],
}

CLUSTERS = (
    ("everyday", "Everyday replies", "Find a natural next message, from a short greeting to a conversation that has gone quiet."),
    ("warm", "Warm and flirty replies", "Say what you mean, match the connection, and be clear about your boundaries."),
    ("dating", "Dating plans and intentions", "Make plans, explain what you want, and handle dates with consideration."),
)

EXISTING_CLUSTERS = {
    "everyday": {"what-to-say-next-over-text", "how-to-respond-to-hey", "how-to-respond-to-dry-texts",
                 "how-to-keep-a-conversation-going", "stop-boring-text-conversations", "how-to-change-the-subject-over-text",
                 "how-to-end-a-text-conversation", "how-to-respond-to-im-busy-text", "restart-dead-conversation",
                 "what-to-text-after-left-on-read", "how-to-double-text", "how-to-recover-awkward-text"},
    "warm": {"how-to-flirt-over-text", "how-to-be-witty-over-text", "how-to-reply-to-sassy-texts",
             "sincere-text-messages", "how-to-confess-feelings-over-text", "how-to-text-your-crush",
             "how-to-respond-to-a-compliment-over-text", "how-to-reply-to-a-pickup-line"},
}

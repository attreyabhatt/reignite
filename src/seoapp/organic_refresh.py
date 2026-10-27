"""Targeted October edits. No unrelated seeded records are overwritten."""
from copy import deepcopy

from seoapp.organic_guides import PREPARED_ON, section
from seoapp.situation_editorial import SITUATION_EDITORIAL
from seoapp.situation_expansion import NEW_SITUATION_PAGES
from seoapp.seed_data.search_refresh import PICKUP_REFRESH
from seoapp.seed_data.search_expansion import PICKUP_EXPANSION, _topic


def refresh(fields, answer, extra_sections, **overrides):
    fields = deepcopy(fields)
    guide = fields["guide_content"]
    guide["answer"] = answer
    # Editorial dates change only with this reviewed content, never per request.
    guide["date_modified"] = PREPARED_ON
    guide["sections"] = extra_sections + guide["sections"]
    fields.update(date_modified=PREPARED_ON, **overrides)
    return fields


SITUATION_REFRESH = {
    "what-to-say-next-over-text": refresh(
        SITUATION_EDITORIAL["what-to-say-next-over-text"],
        "Not sure what to say next? Respond to one detail in their last message, share something of your own, and add one easy opening. For 'I finally finished my exams,' try 'That must be a relief. What's the first thing you're doing with your free evening?' If they have not replied, give them time rather than stacking messages.",
        [section("Choose the next reply from the message they sent", "Start with the actual meaning of their message. An invitation, a short laugh and a difficult day call for different answers.", [
            ("They ask about you", "Them: How was your weekend?\nYou: Quiet in the best way: a walk and an attempt at homemade dumplings. How was yours?", "Answer their question before asking one back."),
            ("They mention a plan", "Them: I'm thinking of going to the market.\nYou: I went last month and found a great bread stall. Are you going for food or just a wander?", "Use the personal detail only if it is true."),
            ("They send a photo", "Them: Look at this view.\nYou: That looks peaceful. Did you have to walk far to get there?", "React to what they shared rather than redirecting immediately."),
            ("They say they are busy", "Them: I'm working late tonight.\nYou: Hope it goes smoothly. I'll let you get back to it.", "A useful next reply can close the conversation."),
        ])], title="What to Say Next Over Text: Examples & Reply Help | TryAgainText"),
    "how-to-confirm-a-date-over-text": refresh(
        {"guide_content": NEW_SITUATION_PAGES["how-to-confirm-a-date-over-text"]["guide_content"]},
        "Send one short message with the day, time and place: 'Looking forward to tomorrow. Still good for seven at the cafe on King Street?' Confirm close enough to resolve practical details, and leave room for an honest change of plan.",
        [section("Confirm tomorrow, today, or a vague plan", "The message should resolve what is missing. If you already agreed everything, a brief check-in is enough. If you never settled a time, propose one.", [
            ("Tomorrow's date", "Looking forward to tomorrow! Still good for seven at the cafe on King Street?", "Use the place and time you actually agreed."),
            ("Later today", "Hi! Looking forward to seeing you at two. I'll meet you outside the main entrance.", "A settled plan may only need a useful meeting detail."),
            ("The time is missing", "Would six on Thursday work for dinner? We haven't fixed a time yet.", "Ask directly rather than calling an incomplete plan confirmed."),
            ("No answer and you need to leave soon", "I haven't heard back, so I'll make other plans if we haven't confirmed by five. Let me know if another day works better.", "Choose a practical cutoff; do not send repeated demands for a response."),
        ])], title="How to Confirm a Date Over Text: Clear Message Examples | TryAgainText",
        h1="How to Confirm a Date Over Text: Clear Message Examples",
        meta_description="Confirm a date for tomorrow or today with clear text examples. Handle vague plans, meeting details and an unanswered confirmation without repeated follow-ups."),
    "how-to-end-a-text-conversation": refresh(
        {"guide_content": NEW_SITUATION_PAGES["how-to-end-a-text-conversation"]["guide_content"]},
        "End with a short, clear closing: 'I've enjoyed talking, but I'm heading to bed. Good night!' If you are only pausing, say so; if you do not want further contact, do not promise to talk later.",
        [section("Pick a closing that matches your intention", "You can leave a chat naturally without an invented excuse. Be clear about whether this is a pause or a decision to stop contact.", [
            ("The topic has finished", "Thanks for explaining that. Enjoy the rest of your evening!", "There is no need to manufacture another question."),
            ("You need to concentrate", "I'm putting my phone away to finish this. I'll check in tomorrow if you're around.", "Promise tomorrow only if you intend to follow through."),
            ("You are not interested", "I don't feel the connection I'm looking for, so I won't continue dating. Wishing you well.", "A clear refusal is kinder than a false pause."),
        ])], title="How to End a Text Conversation: Polite Closing Examples | TryAgainText",
        h1="How to End a Text Conversation: Polite Closing Examples",
        meta_description="End a text conversation naturally, pause when you are busy or decline further contact. Find polite closing messages and examples of clear boundaries."),
    "how-to-respond-to-a-compliment-over-text": refresh(
        {"guide_content": NEW_SITUATION_PAGES["how-to-respond-to-a-compliment-over-text"]["guide_content"]},
        "Start with thank you, then choose the warmth you actually feel. 'Thank you, that made me smile' accepts a compliment without requiring you to flirt. If the attention is unwanted, you can set a boundary instead.",
        [section("Friendly, flirty, or a boundary", "Choose according to your own interest. You do not have to return a compliment or turn praise into a romantic conversation.", [
            ("Friendly appreciation", "Thank you! That's kind of you to say.", "An uncomplicated response lets you accept the compliment."),
            ("Mutual flirtation", "Thank you. I was hoping I'd get to see you again.", "Use this only when you want to see them and flirtation is welcome."),
            ("Praise for something you made", "Thanks! I spent a lot of time on it, so that means something.", "Accept the effort rather than automatically dismissing the praise."),
            ("Unwelcome appearance comments", "I'd prefer that you didn't comment on my appearance.", "You can set a boundary without softening it with flirtation."),
        ])], title="How to Respond to a Compliment Over Text: Reply Examples | TryAgainText",
        h1="How to Respond to a Compliment Over Text: Reply Examples",
        meta_description="Accept a compliment with friendly or flirty text replies, or set a boundary when attention is unwanted. See examples that fit how you actually feel."),
    "what-to-text-after-first-date": {
        "title": "What to Text After a First Date: Honest Follow-Up Examples | TryAgainText",
        "h1": "What to Text After a First Date: Honest Follow-Up Examples",
        "meta_description": "Follow up after a first date with a specific thank-you, a second-date invitation or an honest decline. Includes warm messages and fictional conversations.",
        "date_modified": PREPARED_ON,
        "guide_content": {"date_modified": PREPARED_ON,
            "answer": "Say whether you enjoyed meeting and mention a real moment from the date. 'I had a lovely time tonight. Still laughing about our menu pronunciation. I'd like to see you again if you felt the same.' You do not need a strategic waiting period or a promise you do not mean.",
            "sections": [
                section("Say you enjoyed meeting", "Use a detail from the date rather than generic flattery. Send a message when you can be thoughtful; there is no universal deadline that determines the outcome.", [
                    ("A simple thank-you", "I enjoyed meeting you today. Thanks for making time.", "This is warm without making promises."),
                    ("A shared joke", "I had a lovely time tonight. Still laughing about our menu pronunciation.", "A real callback makes the message personal."),
                    ("A recommendation", "Your book recommendation is now at the top of my list. I enjoyed our conversation.", "Use the detail only if they recommended a book."),
                    ("After getting home", "Home now. I had a good evening with you; hope your journey was easy too.", "This works as a check-in when it fits your exchange."),
                ]),
                section("Suggest a second date when you want one", "Be clear about your interest and let them choose. A concrete invitation is easier to answer than a vague promise.", [
                    ("A simple invitation", "I'd like to see you again. Would you be free for coffee on Sunday?", "A clear proposal leaves room for a yes or no."),
                    ("An interest you discussed", "I'd enjoy trying that gallery we talked about. Would Saturday afternoon work?", "Build on something you both wanted to do."),
                    ("An open schedule", "I enjoyed today and would like another date. What does next week look like for you?", "Use one question rather than a series of schedule guesses."),
                ]),
                section("Be honest about uncertainty or no interest", "You do not owe a second date. Avoid suggesting friendship or a future meeting merely to soften a refusal.", [
                    ("You are interested but cautious", "I enjoyed meeting you and would like to get to know you a little more, if you feel the same.", "Say what you can honestly offer."),
                    ("No romantic connection", "Thanks for meeting me. I didn't feel a romantic connection, so I don't want to plan another date.", "A brief decline does not need criticism."),
                    ("They decline", "Thanks for being clear. I enjoyed meeting you and wish you well.", "Accept the answer rather than negotiating."),
                ]),
                section("Two fictional follow-up conversations", "These examples show different outcomes. A well-worded message cannot guarantee mutual interest.", [
                    ("Mutual interest", "You: I enjoyed tonight. Would you like to try that gallery Saturday?\nThem: I'd like that.\nYou: Great. Does two work?", "The practical plan follows a mutual yes."),
                    ("Different feelings", "You: I'd like to see you again if you felt the same.\nThem: Thank you, but I didn't feel a romantic connection.\nYou: Thanks for telling me. Wishing you well.", "A respectful ending is a valid outcome."),
                ]),
                {"heading": "When there is no reply", "paragraphs": ["Give them time. Avoid repeated check-ins or demands for an explanation. If you send one later follow-up, keep it low-pressure and stop if they do not respond. A clear refusal or request for space means stop."], "examples": []},
            ]},
    },
}


def pickup_refresh(fields, answer, extra):
    result = refresh(fields, answer, extra)
    # Only model fields may enter the database publisher.
    result.pop("date_modified")
    return result


PICKUP_ORGANIC_REFRESH = {
    ("professions", "lawyer"): pickup_refresh(
        PICKUP_REFRESH[("professions", "lawyer")],
        "A lawyer pickup line works best as one light joke followed by a real topic. Try 'I was going to make a legal argument for coffee, but a straightforward invitation seems stronger.' Use legal puns when the context fits; their job does not tell you whether they want to flirt.",
        [section("Start with a joke, then move beyond the job", "Choose a line that fits the profile. Avoid requests for free legal advice, assumptions about income or jokes about professional confidentiality.", [
            ("An invitation", "I was going to make a legal argument for coffee, but a straightforward invitation seems stronger.", "Use this when a direct invitation fits the stage of your chat."),
            ("A profile interest", "Your profile makes a strong case for trying that hiking route. What's the best part?", "The profile detail matters more than the pun."),
            ("They play along", "Them: Objection, leading question.\nYou: Fair. I'll rephrase: what's your ideal way to spend a free Saturday?", "Acknowledge the joke and offer a normal topic."),
        ])]),
    ("dating-apps", "instagram-dm-opener"): pickup_refresh(
        PICKUP_REFRESH[("dating-apps", "instagram-dm-opener")],
        "For a first Instagram DM, reference something they chose to share and ask one easy question. 'That little bookshop in your story looks dangerous for my budget. Did you find anything good?' is specific when their story actually shows a bookshop. A follow-back alone does not establish romantic interest.",
        [section("Choose a first DM, a story reply, or a follow-up", "Match the message to the actual connection. A stranger's story, a mutual friend's introduction and an ongoing conversation are different starting points.", [
            ("A real introduction", "Hey, I'm Sam. Maya mentioned we both went to the same gig on Friday. Did you catch the opening band?", "Name a mutual friend only if the introduction is real and welcome."),
            ("A story reply", "That coastal path in your story looks beautiful. Was it a long walk?", "A question about the shared experience is easy to answer."),
            ("A genuine update", "I tried the cafe you recommended. The iced coffee was excellent; thanks for the tip!", "Use this in an established conversation, not as a pretext to chase an unanswered first DM."),
        ])]),
    ("professions", "flight-attendant"): pickup_refresh(
        PICKUP_EXPANSION[("professions", "flight-attendant")],
        "Use one aviation pun if their profile invites that humor, then ask about something they enjoy away from work. 'Your travel photos have ruined my weekend plans: now I want mountains. Which trip would you repeat?' works only when those photos are actually there.",
        [section("Treat the profile as more than a job title", "Do not send romantic approaches while someone is working or required to be polite to you. In a dating-app conversation, reference the interests they chose to share.", [
            ("A travel interest", "Your mountain photo looks worth the early start. Was the sunrise as good as it looks?", "Use the visible trip detail instead of assuming all travel is a holiday."),
            ("Their time off", "When you get a free weekend, are you exploring somewhere new or enjoying being home?", "Leave room for an answer that has nothing to do with flying."),
            ("A natural follow-up", "Them: Honestly, I like being home.\nYou: Fair. My ideal reset is cooking and a long walk. What's yours?", "Respond to what they say rather than forcing another aviation joke."),
        ])]),
}


PICKUP_ORGANIC_REFRESH[("hobbies", "fishing")] = _topic(
    "Fishing", "Fishing Pickup Lines: Light Puns and Real Conversation Starters",
    "Find fishing pickup lines for a dating profile, with light angling puns, clear invitations and example follow-up conversations beyond the first joke.",
    "Use the fishing detail they actually shared. One small pun can open the chat; curiosity about their favourite place or kind of day keeps it personal.",
    "A fishing pickup line should connect to their interest without pretending you know more than you do. 'I had a reel-y clever opener, but I'd rather hear the story behind that lake photo' gives the joke a real topic.",
    [
        ("Light fishing puns", "Keep the joke short and grounded in a real profile detail.", [
            ("A lake photo", "I had a reel-y clever opener, but I'd rather hear the story behind that lake photo.", "Let their actual photo provide the next topic."),
            ("A patient hobby", "Your patience with fishing makes my five-minute coffee queue complaints look dramatic.", "A small joke about yourself avoids making assumptions about them."),
            ("A weekend plan", "I'm casting around for a good weekend idea. Does your favourite lakeside walk have a cafe?", "This works if you are genuinely interested in the place."),
            ("A beginner", "My fishing expertise is mostly knowing which end of the rod to hold. Where would you start a beginner?", "Be honest about your experience."),
            ("An impressive view", "The catch looks good, but that view is doing most of the convincing.", "Comment on the setting rather than treating the photo as a competition."),
        ]),
        ("Warm, direct openers", "A plain invitation or genuine question can work without a pun.", [
            ("A specific question", "Is your ideal fishing day about the catch, the quiet, or the company?", "Give them room to describe what they enjoy."),
            ("A real invitation", "I'd enjoy hearing those fishing stories over coffee. Interested?", "Use an invitation when mutual conversation has developed."),
            ("A shared interest", "I like quiet mornings by the water too. What's your favourite part of being out there?", "Keep the shared-interest claim true."),
            ("A profile story", "That photo looks like it comes with a story. What happened just before it?", "Curiosity is more personal than a stock compliment."),
            ("A relaxed plan", "A walk by the river and coffee sounds like a good afternoon to me. How about you?", "Suggest a public plan, not an isolated first meeting."),
        ]),
        ("Deliberately cheesy fishing lines", "Use these only if this kind of humor is welcome. One is plenty.", [
            ("A pun admission", "I promised myself no fishing puns. Clearly that plan has gone overboard.", "The joke admits its own cheesiness."),
            ("A coffee invitation", "No bait-and-switch: I really am asking you for coffee.", "Let the invitation stay clear."),
            ("A playful opener", "My opening line is tangled, but my interest in that hiking photo is straightforward.", "Replace the photo detail with something actually shown."),
            ("A small callback", "I'm hooked on the idea of hearing the rest of that story.", "Use this after they have started a story."),
            ("A gentle joke", "I brought one fishing pun and no backup plan. Fortunately your profile gave me a real question.", "Follow with a real, specific question."),
        ]),
    ], [
        ("Ask about their enjoyment", "You: Is it the catch or the quiet that makes fishing good for you?\nThem: Mostly the quiet.\nYou: I get that. Long walks do the same for me. Do you have a favourite spot?", "Share your own genuine point of connection."),
        ("Be an honest beginner", "You: Where would you start a beginner?\nThem: With a friend who knows what they're doing.\nYou: Sensible. My attempts at learning from videos have mixed results.", "You do not need to pretend expertise to keep talking."),
        ("Accept a short exchange", "You: That lake looks lovely.\nThem: Thanks.\nYou: Hope your next trip is a good one!", "A polite response does not obligate them to continue."),
    ], ["Use details from their profile rather than stereotypes about fishing. Do not invent experience or claim a shared trip you never took.", "If they reply, follow that detail into a conversation. If they do not, leave it there; repeated puns will not resolve silence."])


PICKUP_ORGANIC_REFRESH[("professions", "firefighter")] = _topic(
    "Firefighter", "Firefighter Pickup Lines: Light Puns and First Messages",
    "Try firefighter pickup lines that suit a dating-app profile, with light jokes, straightforward invitations and examples for moving beyond job-related banter.",
    "A uniform can be a profile detail without becoming the whole conversation. Use one light joke, then ask about an interest they chose to share.",
    "In a dating-app chat, a firefighter pickup line can be one small joke followed by a genuine question. Avoid jokes about emergencies, trauma or needing to be rescued. Never interrupt someone doing their job with a romantic approach.",
    [
        ("Light, respectful firefighter jokes", "Keep work-related humor low pressure and avoid pretending there is an emergency.", [
            ("A small admission", "I had a whole firefighter pun planned, but your dog has completely stolen the opening line.", "Use this only if the profile includes a dog."),
            ("A coffee plan", "No emergency here, just a fairly enthusiastic invitation for coffee.", "Keep a real invitation clear."),
            ("A profile interest", "Your cooking photo is doing more to spark my interest than any line I could borrow.", "Reference an actual photo and avoid sexualizing the uniform."),
            ("A quiet weekend", "Is your ideal day off an adventure, or the heroic achievement of doing absolutely nothing?", "Let them describe life outside work."),
            ("A pun with a topic", "I was going to mention sparks, but I'd rather ask about that excellent book recommendation.", "Follow with a real question about the book."),
        ]),
        ("Direct first messages", "A genuine question often offers more than a job pun. Ask about details the person chose to make public.", [
            ("A hobby", "Your profile says you climb. What got you into it?", "Use the actual hobby, not an invented shared interest."),
            ("A mutual interest", "I like early hikes too, though I need coffee first. What's your favourite route?", "Tell the truth about your own routine."),
            ("Their time off", "What do you look forward to when you have a completely free afternoon?", "This does not ask them to recount difficult calls."),
            ("An invitation", "I've enjoyed talking with you. Would you like to get coffee on Sunday?", "Use this after a mutual conversation has developed."),
            ("A practical choice", "Would a walk or a coffee suit you better for a first meeting?", "Offer a public, low-pressure option."),
        ]),
        ("Cheesy lines for welcome banter", "Choose one if the conversation already enjoys puns. Do not make their work a fantasy they have to perform.", [
            ("A gentle spark", "I'd make a spark joke, but I think a normal hello deserves a chance.", "The greeting can be enough."),
            ("A pun warning", "This message contains one questionable pun and a genuine interest in your weekend plans.", "Follow with a relevant, ordinary topic."),
            ("A cooking callback", "My cooking produces more toast than sparks. What's your reliable dinner recipe?", "Keep the humor on yourself."),
            ("A warm invitation", "There may be chemistry here. Coffee seems like a sensible way to investigate.", "Use this only with mutual flirtation."),
            ("A simple alternative", "I retired the fire puns. How has your week been outside work?", "Make space for the person beyond the role."),
        ]),
    ], [
        ("Follow the hobby", "You: What got you into climbing?\nThem: A friend talked me into it.\nYou: A good introduction, then. Do you prefer the gym or getting outdoors?", "Continue with the interest they shared."),
        ("Respect their availability", "Them: I'm on shift, so replies will be slow.\nYou: No problem. Hope it goes smoothly; we can talk another time.", "Do not require attention while they are working."),
        ("Move to a clear plan", "You: Would you like coffee Sunday?\nThem: Yes, afternoon works.\nYou: Great. How about two at the cafe near the station?", "An agreed time and place are more useful than another pun."),
    ], ["Do not ask for details about traumatic calls, assume relationship preferences from a uniform, or send flirty messages during an emergency interaction.", "Treat a refusal or repeated silence as a reason to stop. Adapt the opener to their actual interests and your real voice."])

for _fields in PICKUP_ORGANIC_REFRESH.values():
    _fields["guide_content"]["date_modified"] = PREPARED_ON

# Editorial model metadata is kept in the existing JSON, not added as columns.
PICKUP_REFRESH_KEYS = tuple(PICKUP_ORGANIC_REFRESH)

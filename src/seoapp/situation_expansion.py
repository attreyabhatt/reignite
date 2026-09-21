"""Specific texting guides; all sample messages are fictional examples."""

from seoapp.seed_data.search_refresh import example


def _section(heading, paragraph, *examples):
    return {"heading": heading, "paragraphs": [paragraph], "examples": [example(*row) for row in examples]}


def _guide(slug, heading, description, label, answer, sections, related, situation="stuck_after_reply"):
    return {
        "slug": slug, "situation": situation, "h1": heading,
        "title": f"{heading} | TryAgainText", "meta_description": description,
        "sidebar_label": label, "quick_answer": answer,
        "guide_content": {"answer": answer, "sections": sections},
        "sample_reply": sections[0]["examples"][0]["text"],
        "prefill_text": "", "seo_sections": [],
        "upload_hint": "Add the recent exchange so reply ideas can match what was actually said.",
        "screenshot_tip": "Include enough of the conversation to show the context, and remove details you do not want to share.",
        "force_show_upload": situation == "just_matched",
        "related_slugs": related,
    }


NEW_SITUATION_PAGES = {}


def _add(*args, **kwargs):
    page = _guide(*args, **kwargs)
    NEW_SITUATION_PAGES[page["slug"]] = page


_add(
    "how-to-respond-to-hey", "How to Respond to Hey: Replies That Start a Conversation",
    "Not sure how to reply to hey, hi or what's up? Try warm greetings, profile-based follow-ups and examples for new matches or people you already know.",
    "Reply to Hey",
    "Reply with a greeting, then add one small detail or easy question. 'Hey! I'm winding down after a long walk. How's your evening going?' gives them more to answer than another 'hey' alone.",
    [
        _section("When a new match says hey", "A short greeting is an opening, not enough evidence to judge interest or effort. Return it warmly and offer one topic. You do not need to carry the whole conversation by yourself.",
            ("A normal evening", "Hey! I'm deciding what to cook tonight. Has your day been busy or fairly relaxed?", "A small detail about you makes the question feel less like an interview."),
            ("A visible profile detail", "Hi! I noticed the pottery in your profile. Did you make that blue bowl?", "Ask only about something they actually chose to show.")),
        _section("When they say hi or what's up", "Answer the greeting in the same spirit. If they ask what you are doing, actually answer before asking something back; there is no need for a rehearsed comeback.",
            ("What's up?", "Not much tonight: leftovers and a film I've been meaning to watch. What are you up to?", "An ordinary truthful answer gives the conversation an accessible start."),
            ("A playful hello", "Hi! You've caught me debating whether a second coffee counts as a plan. How's your morning?", "Keep the joke small enough that they can reply normally.")),
        _section("When you already know each other", "Use shared context where it exists. A greeting from a friend or someone you have dated can lead back to an earlier conversation without demanding an explanation for the message.",
            ("Something they mentioned", "Hey! How did your presentation go? I remembered it was today.", "Remembering a real detail is more personal than an unrelated stock question."),
            ("After a good meeting", "Hi, good to hear from you. I tried that bakery you recommended, and you were right about the cinnamon rolls.", "Use this only if you actually followed the recommendation.")),
        _section("When the exchange stays one-sided", "Try an easy opening, then notice whether they contribute. You can pause or leave the conversation without scolding them for a short reply. You also do not owe a stranger an ongoing chat.",
            ("They seem occupied", "Sounds like you've got a lot on today. I'll let you get back to it; we can chat another time.", "You can end the exchange without making them justify their availability."),
            ("You cannot talk now", "Hey! I'm heading into something, but I can chat later this evening.", "Give a later time only if you intend to follow through.")),
    ],
    ["what-to-say-next-over-text", "how-to-respond-to-dry-texts", "how-to-end-a-text-conversation"],
)

_add(
    "how-to-respond-to-a-compliment-over-text", "How to Respond to a Compliment Over Text",
    "See replies to compliments that feel warm, flirty or friendly, plus ways to accept praise without deflecting it or returning interest you don't feel.",
    "Reply to Compliments",
    "Start with a simple thank-you. Add warmth, a truthful compliment back, or a boundary depending on how you feel. You do not have to flirt back just because someone complimented you.",
    [
        _section("Accept a compliment without arguing with it", "A short acknowledgment is enough. You do not need to list why the compliment is undeserved, explain every flaw, or find an equally impressive reply.",
            ("They like your photo", "Thank you! I was having a really good day when that was taken.", "Accept the kind remark and add a detail only if it is true."),
            ("They praise your work", "Thanks, that means a lot. I spent quite a while getting that part right.", "Acknowledge the effort without turning the response into self-criticism.")),
        _section("Flirt back when you want to", "Match the degree of familiarity. A new match might get a warm thank-you; someone you are already flirting with can get a more direct expression of interest.",
            ("You enjoy their attention", "Thank you. I was rather hoping you'd notice.", "This works when the shared context makes the flirtation clear."),
            ("You want to reciprocate", "That's lovely to hear. I really liked your smile when we met, too.", "Return a specific, sincere compliment rather than a reflexive claim.")),
        _section("Keep the reply friendly", "You can appreciate a kind comment without implying romantic interest. Be warm if that feels comfortable, and avoid adding a date invitation just to soften the reply.",
            ("A friendly acknowledgment", "That's kind of you, thank you!", "A complete answer can be brief and need no question afterward."),
            ("Clarifying your intentions", "Thank you. I enjoy talking with you, but I see this as a friendship.", "Use clear words when ongoing flirting needs clarification.")),
        _section("When a comment makes you uncomfortable", "A compliment does not create an obligation. If the wording is too personal, repeated or unwelcome, you can state a boundary or stop responding. You do not need to debate their intention.",
            ("Too personal, too soon", "I'd prefer to keep the conversation less personal while we're getting to know each other.", "Describe what you want rather than guessing why they wrote it."),
            ("You want it to stop", "I'm not comfortable with those comments. Please stop.", "A direct boundary does not require an apology or a substitute compliment.")),
    ],
    ["how-to-flirt-over-text", "sincere-text-messages", "how-to-end-a-text-conversation"],
)

_add(
    "how-to-reply-to-instagram-story", "How to Reply to an Instagram Story and Start a Chat",
    "Find Instagram story reply examples for food, travel, music and everyday posts, with advice for a first conversation and what to do after a reply.",
    "Instagram Story Replies",
    "Mention one detail from the story and ask something small about it. For a photo of homemade pasta, try 'That looks good. Was it a new recipe or a reliable favorite?' A public story does not mean someone owes you a conversation.",
    [
        _section("Reply to an activity or recommendation", "A visible activity gives you a natural subject. Be specific without pretending you know the location, the people pictured or the backstory. Avoid several questions in a single reply.",
            ("Food they made", "That cake looks excellent. Is it something you bake often or a first attempt?", "Use this when the story says they baked it, not just when a cake appears."),
            ("A book or film", "I've been considering that one. What did you enjoy about it? No spoilers needed.", "A recommendation invites their opinion rather than a yes-or-no answer.")),
        _section("Use travel, music and everyday details", "Choose something you can honestly respond to. Shared taste can open a conversation, but there is no need to invent having visited the same place or loving an artist you do not know.",
            ("A landscape", "That view looks peaceful. Was the walk as good as the photo makes it seem?", "Ask about the experience without requesting an exact live location."),
            ("A song recommendation", "I hadn't heard that track before. The opening caught my attention; is the rest of the album similar?", "Listen before saying this, and let unfamiliarity be part of the conversation.")),
        _section("Make a first reply or a familiar one", "How well you know each other matters more than finding a universally clever line. A first message can be friendly. A warmer reference fits someone with whom you already share a conversation.",
            ("First conversation", "Your post about the community art show caught my eye. Was there a piece you'd recommend looking out for?", "A public event supplies context without an overly personal approach."),
            ("You already talk", "You finally tried the noodle place! Did it live up to the very serious expectations we set?", "A real shared discussion makes the message personal.")),
        _section("Follow their response instead of sending another opener", "If they answer, respond to what they say. A brief acknowledgment might be all the conversation needs. If there is no reply, avoid using each new story as another attempt to get their attention.",
            ("They offer a detail", "Them: 'The walk was great, but so muddy.'\nYou: 'That sounds familiar. My last hike ended with a very undignified shoe-cleaning session.'", "Share a related experience without immediately demanding another answer."),
            ("They only acknowledge it", "Them: 'Thanks!'\nYou: 'You're welcome. Hope the rest of your day is good.'", "You can let a brief exchange end without forcing a longer chat.")),
    ],
    ["best-dating-app-openers", "what-to-say-next-over-text", "how-to-respond-to-hey"],
)

_add(
    "dating-app-openers-with-no-bio", "Dating App Openers When There Is No Bio",
    "What should you say to a match with no bio? See openers using visible photo details, simple preferences and honest introductions without assumptions.",
    "No Bio Openers",
    "If there is no bio, use a clear, non-sensitive photo detail or a small preference question. Do not infer someone's job, nationality or personality from their appearance. A plain 'Hi, what has been the best part of your week?' is a reasonable start.",
    [
        _section("Use a detail the photo actually provides", "An activity, a pet or a recognizable object may give you enough context. Phrase uncertainty as a question. A photo alone does not prove ownership, skill or a long-term interest.",
            ("A dog in a photo", "The dog in your photo looks very happy. Yours, or a particularly good guest appearance?", "Ask rather than assuming the dog belongs to them."),
            ("A visible activity", "That climbing photo caught my eye. Is it a regular hobby or something you were trying out?", "Give room for both possibilities instead of assigning an identity.")),
        _section("Ask a small preference question", "When the pictures offer little context, choose a question someone can answer without an essay. Add your own answer when it helps the message feel like a conversation.",
            ("A free afternoon", "Hi! If you unexpectedly got a free afternoon, would you go somewhere or happily stay in?", "An everyday choice is more approachable than asking for a life story."),
            ("A food preference", "My weekend usually includes finding something good to eat. Are you more likely to revisit a favorite or try somewhere new?", "Share a truthful preference before asking about theirs.")),
        _section("Keep a plain introduction available", "You do not need a clever angle for every match. If you have no useful context, a warm hello and one open subject can be enough to see whether conversation develops.",
            ("An ordinary introduction", "Hi, nice to meet you. What's something you've been enjoying lately?", "The other person can choose a hobby, show, meal or anything else."),
            ("A little of your day", "Hey! I just got back from a walk and am deciding what to watch tonight. Have you seen anything good recently?", "Use your actual day so follow-up questions are easy to answer honestly.")),
        _section("When they reply, build on what you learn", "Their answer now supplies the context the profile lacked. Stop treating the empty bio as a problem to solve. If they do not participate, you can leave the exchange there.",
            ("They mention a hobby", "Them: 'I've been learning to bake bread.'\nYou: 'What got you into it? My first attempt was more doorstop than loaf.'", "Use the second sentence only if it reflects your own experience."),
            ("They are vague", "Them: 'Not much really.'\nYou: 'Fair enough. Mine has been a quiet week too, apart from discovering a very good lunch spot.'", "Offer one detail without criticizing their profile or piling on questions.")),
    ],
    ["best-dating-app-openers", "how-to-respond-to-hey", "what-to-say-next-over-text"],
    situation="just_matched",
)

_add(
    "how-to-confirm-a-date-over-text", "How to Confirm a Date Over Text",
    "See simple texts to confirm a date's time and place, clarify vague plans, handle changes and decide what to do when you haven't heard back.",
    "Confirm a Date",
    "Send a short message naming the day, time and place you agreed on: 'Looking forward to tomorrow. Still good for coffee at Birch at 3?' If the details are not settled, suggest them clearly rather than treating a vague idea as a confirmed date.",
    [
        _section("Confirm plans you have already agreed on", "A confirmation is a practical check, not a test of enthusiasm. Send it early enough to make any travel or booking decisions you need to make. There is no universal hour that guarantees a reply.",
            ("The day before", "Looking forward to tomorrow. Are we still good for 6:30 at the little Italian place on King Street?", "Repeat the actual agreed details so there is no ambiguity."),
            ("Later today", "Hi! Just checking we're still on for coffee at Birch at 3 today.", "A short confirmation does not need an apology or a second invitation.")),
        _section("Turn a vague idea into a plan", "'We should go sometime' is not a confirmed date. Offer a concrete option and wait for agreement before making arrangements that assume they will attend.",
            ("You agreed on a day only", "Would Saturday at 2 at the park cafe work for you?", "One complete suggestion is easy to accept or adjust."),
            ("You discussed an activity", "I'd still enjoy visiting that exhibition together. Are you free Sunday afternoon?", "Make clear that you are proposing, not confirming, a plan.")),
        _section("Respond to changes or a cancellation", "Separate a practical conflict from assumptions about interest. Someone may offer another time, need to cancel, or be unable to commit. You can be understanding while also keeping your own plans clear.",
            ("A small time change", "Seven works for me instead. Same place?", "Accept only if the new time actually suits you."),
            ("They cancel", "Thanks for letting me know. If you'd like to rearrange, send me a day that works for you.", "Leave the next scheduling step with the person who canceled.")),
        _section("When you do not get confirmation", "Make decisions based on the time and travel involved. One practical follow-up can clarify the situation; repeated 'Are you there?' messages usually add no useful information. State your own cutoff if you need one.",
            ("You need to leave soon", "I need to head out by 5:30 to get there. Please let me know before then if we're still meeting.", "Explain a real logistical deadline without making it a threat."),
            ("The deadline has passed", "I haven't heard back, so I'm making other plans for tonight. We can discuss another day if you'd like.", "Close the uncertainty calmly instead of assuming a meeting is happening.")),
    ],
    ["how-to-ask-her-out-over-text", "what-to-text-when-she-cancels", "how-to-respond-to-im-busy-text"],
    situation="ask_her_out",
)

_add(
    "how-to-respond-to-im-busy-text", "How to Respond to an I'm Busy Text",
    "Find replies to an I'm busy text, whether they suggest another time, need space or stay unavailable, with examples that keep your own plans clear.",
    "I'm Busy Replies",
    "Acknowledge that they are busy and respond to any practical information they give. If they offer another time, discuss it. If they do not, you can leave an opening without repeatedly asking. One message cannot tell you why they are unavailable.",
    [
        _section("They are busy now but want to talk later", "If they name a later time, take it at face value. You do not need a clever reply to keep their attention while they work, study or spend time with other people.",
            ("They will message later", "No problem. Hope the rest of your afternoon goes smoothly; talk later.", "Acknowledge their message without adding another task."),
            ("They suggest a time", "After dinner works for me too. I'll be free around eight.", "Share your actual availability rather than promising to wait all evening.")),
        _section("They cannot make the date you suggested", "Notice whether they propose an alternative, but do not turn one scheduling conflict into a diagnosis of interest. Offer or accept a concrete option if you still want to meet.",
            ("They offer another day", "Thursday works for me. Would 6:30 at the same place suit you?", "Respond to the alternative instead of asking them to defend the cancellation."),
            ("No alternative yet", "Understood. If you'd like to meet another time, let me know a day that suits you.", "Give them a clear way to take the next step.")),
        _section("They are repeatedly unavailable", "You can notice that plans are not progressing without deciding whether they are dishonest or uninterested. A relationship needs workable availability as well as good intentions. You do not have to keep proposing dates indefinitely.",
            ("You want to stop chasing a plan", "It seems tricky to find a time right now. I'll leave it with you to suggest a day if you'd like to meet.", "State the practical situation without accusing them."),
            ("You want to step away", "I don't think our availability is lining up, so I'm going to step back. Wishing you well.", "A clear decision can be kind and does not require an argument.")),
        _section("They need space, or you also have limits", "If someone explicitly asks for space, respect the request rather than negotiating a faster reply. Your own time matters too: being understanding does not require staying available for an unspecified last-minute plan.",
            ("They ask for quiet time", "I understand. I'll give you space and let you reach out if you'd like to talk.", "Only say this if you intend to respect it."),
            ("A late invitation does not work", "I can't make tonight at short notice. If we plan a little ahead, I can usually do weekends.", "Describe your needs without punishing them for having been busy.")),
    ],
    ["how-to-confirm-a-date-over-text", "what-to-text-when-she-cancels", "how-to-end-a-text-conversation"],
)

_add(
    "how-to-end-a-text-conversation", "How to End a Text Conversation Politely",
    "See ways to end a text conversation for the night, pause when you're busy or clearly decline more contact, without promising a chat you don't want.",
    "End a Conversation",
    "State that you are leaving the conversation and add warmth if you want to continue another time. 'I've enjoyed talking, but I'm heading to bed. Good night!' is enough. Promise a later message only when you mean it.",
    [
        _section("End a good conversation for the night", "You can leave while a conversation is going well. A brief acknowledgment lets the other person understand the pause without needing a dramatic explanation or an invented excuse.",
            ("Going to sleep", "This has been fun, but I need to get some sleep. Good night!", "Name the actual reason and let the exchange close."),
            ("A warm ending", "I've really enjoyed hearing about your trip. I'm calling it a night, but I'm glad we talked.", "Mentioning the topic makes the closing feel attentive.")),
        _section("Pause because something else needs your attention", "State your availability simply. A later time is helpful if it is realistic, but you do not need to schedule every future message. Avoid continuing to ask questions after announcing you are leaving.",
            ("You have plans", "I'm heading out to meet a friend, so I'll put my phone away for a while. Talk another time.", "You can be present elsewhere without asking permission."),
            ("You can return later", "I need to focus on work now. I can pick this up after six if you're around.", "Offer a real option rather than an open-ended promise.")),
        _section("Close a chat that has naturally run its course", "Not every exchange needs a fresh topic. A kind closing can be better than squeezing another question out of a conversation neither person is actively continuing.",
            ("The topic is finished", "Thanks for the recommendation. Hope the rest of your weekend is good!", "This acknowledges the exchange without creating an obligation to reply."),
            ("You have made plans", "Great, Saturday at two it is. Looking forward to seeing you then.", "Once the details are agreed, you can leave the conversation there.")),
        _section("End contact when you do not want to continue", "Be clear about whether you are pausing or ending the connection. Do not promise a future conversation to soften a refusal. If a boundary is ignored, you do not have to keep explaining it.",
            ("A dating connection is not right", "Thanks for taking the time to chat. I don't feel this is the connection I'm looking for, so I won't continue dating. Wishing you well.", "A respectful refusal does not need a list of the other person's faults."),
            ("You want contact to stop", "I don't want to continue this conversation. Please don't message me again.", "A firm ending is appropriate when a softer message would leave ambiguity.")),
    ],
    ["how-to-keep-a-conversation-going", "how-to-respond-to-im-busy-text", "sincere-text-messages"],
)

_add(
    "how-to-reply-to-a-pickup-line", "How to Reply to a Pickup Line: Flirty or Friendly",
    "Find replies to funny, cheesy and awkward pickup lines, with examples for flirting back, starting a real conversation or politely declining.",
    "Pickup Line Replies",
    "Respond to your actual interest, not to a rule that you must produce a better joke. If you like the approach, acknowledge it and give them a real topic. If you do not, a brief, clear refusal is enough.",
    [
        _section("Play along when you like the joke", "You can return the energy without escalating further than you want. A smile in the wording and one playful response is enough; the chat does not have to become a contest of pickup lines.",
            ("An obvious pun", "That was impressively cheesy. I'm choosing to appreciate the commitment.", "It acknowledges the attempt without making a serious romantic promise."),
            ("A shared hobby joke", "A respectable opening move. Now I need to know whether you actually play chess.", "Use the hobby from their message, and ask with curiosity rather than as a test.")),
        _section("Be direct when you are interested", "If the line made you want to talk, say so. You do not need to hide a warm response behind sarcasm or make the other person work through a series of challenges.",
            ("You like the approach", "That made me smile. Hi, I'm Sam. How's your evening going?", "Move from the performance into a normal introduction using your own name."),
            ("You already have a connection", "You could have just said you wanted to get coffee. I'd have been interested.", "This is an invitation; use it only if meeting is something you want.")),
        _section("Move beyond the line", "Acknowledge the joke, then pick a detail from their profile or answer something they mentioned. If the line misses but the conversation still interests you, you can offer a fresh subject without insulting them.",
            ("A food pun", "I'll give the pasta pun a pass. What's your actual favorite thing to cook?", "The topic follows naturally from the joke."),
            ("An awkward attempt", "I think a normal hello might suit us better. Your profile mentions photography; what do you like taking pictures of?", "Use a real profile detail to start again on a subject you care about.")),
        _section("Decline or set a boundary", "Someone's effort at being funny does not obligate you to continue. A clear refusal can be brief. If the line is unwanted or explicit, you do not need a witty comeback before ending the exchange.",
            ("Not interested", "Thanks, but I'm not interested in flirting. Take care.", "This communicates your choice without debating how good the line was."),
            ("The message crossed a line", "I'm not comfortable with that message, and I don't want to continue this conversation.", "State your boundary plainly; another reply is not required.")),
    ],
    ["how-to-flirt-over-text", "what-to-say-next-over-text", "how-to-end-a-text-conversation"],
)


# Add relevant incoming links without replacing the existing guides' content.
SITUATION_INCOMING_LINKS = {
    "what-to-say-next-over-text": ["how-to-respond-to-hey", "how-to-reply-to-a-pickup-line"],
    "best-dating-app-openers": ["dating-app-openers-with-no-bio", "how-to-reply-to-instagram-story"],
    "how-to-respond-to-dry-texts": ["how-to-respond-to-im-busy-text", "how-to-respond-to-hey"],
    "how-to-ask-her-out-over-text": ["how-to-confirm-a-date-over-text"],
    "how-to-ask-for-a-second-date": ["how-to-confirm-a-date-over-text"],
    "what-to-text-when-she-cancels": ["how-to-respond-to-im-busy-text", "how-to-confirm-a-date-over-text"],
    "how-to-flirt-over-text": ["how-to-respond-to-a-compliment-over-text", "how-to-reply-to-a-pickup-line"],
    "sincere-text-messages": ["how-to-respond-to-a-compliment-over-text"],
    "how-to-keep-a-conversation-going": ["how-to-respond-to-hey", "how-to-end-a-text-conversation"],
    "how-to-change-the-subject-over-text": ["how-to-end-a-text-conversation"],
}

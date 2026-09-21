"""Original, illustrative pickup guides for the second September content batch.

The line lists and the visible editorial examples share one source of truth.
"""

from seoapp.seed_data.search_refresh import example


def _topic(keyword, heading, description, intro, answer, groups, conversations, advice):
    fields = {
        "keyword": keyword,
        "h1": heading,
        "title": f"{heading} | TryAgainText",
        "meta_description": description,
        "seo_intro": intro,
        "prefill_text": f"Write an opener using the {keyword.lower()} detail in this profile.",
        "upload_hint": "Add the profile or chat so the opener can use details they actually shared.",
        "her_info_prefill": "",
    }
    sections = []
    for field, group in zip(("witty_lines", "flirty_lines", "cheesy_lines"), groups):
        label, paragraph, rows = group
        examples = [example(*row) for row in rows]
        fields[field] = [item["text"] for item in examples]
        sections.append({"heading": label, "paragraphs": [paragraph], "examples": examples})
    sections.extend([
        {"heading": "After the opener: example conversations", "paragraphs": [
            "These fictional exchanges show possible directions, not predicted responses. Follow the detail they actually give you."
        ], "examples": [example(*row) for row in conversations]},
        {"heading": "Make the message your own", "paragraphs": advice, "examples": []},
    ])
    fields["guide_content"] = {"answer": answer, "sections": sections}
    return fields


NEW_PICKUP_TOPICS = {
    ("hobbies", "tennis"): _topic(
        "Tennis", "Tennis Pickup Lines: From First Serve to First Date",
        "Try 15 tennis pickup lines, from witty rally jokes to cheesy love puns, with follow-up conversations and tips for making the opener personal.",
        "A tennis photo gives you a starting point: a favorite court, a doubles partner or an enthusiasm for watching matches. Choose a line that fits what the profile actually shows.",
        "Use one tennis reference and leave room for a real answer. A question about their favorite court is easier to build on than several love-score jokes in a row.",
        [
            ("Five witty tennis openers", "Keep the competition friendly. You can be interested in their hobby without pretending to play at their level.", [
                ("A small confession", "My backhand needs work, but my post-match cafe recommendations are ready for the tour.", "Use it if you play and genuinely have a cafe recommendation to exchange."),
                ("Court preferences", "Important compatibility question: clay courts, hard courts, or whichever one is closest to brunch?", "A court photo provides context, and the choices make answering easy."),
                ("Doubles diplomacy", "Before we become doubles partners, how forgiving are you of someone saying 'yours' a little too late?", "This suits someone whose profile mentions doubles and a relaxed approach to sport."),
                ("An honest warm-up", "I can offer a decent rally and an unnecessarily detailed snack break.", "Offer something plausible rather than implying you are an expert."),
                ("Match-day plans", "Your tennis photo has me considering a very ambitious plan: exercise followed by sitting down together.", "A light invitation fits better after a little mutual interest."),
            ]),
            ("Five flirty tennis lines", "These are clearer about interest. Pick one that sounds like you and let their response set the pace.", [
                ("An invitation", "I'd like to hear your best tennis story over something colder than a courtside water bottle.", "It turns the hobby into a chance to get to know them."),
                ("A shared afternoon", "A rally with you and a walk afterward sounds like an afternoon I'd look forward to.", "Use this when meeting for a casual activity already feels welcome."),
                ("Off-court interest", "The tennis photo caught my eye. Now I'm curious about you when the racket's in its bag.", "Acknowledge the profile detail without reducing the person to it."),
                ("A friendly challenge", "You choose the court; I'll choose a place where we can keep talking afterward.", "This works as a proposed plan once both people want to meet."),
                ("Choosing a partner", "I'd happily be your doubles partner, but I'm more interested in a date than a trophy.", "The point is clear interest, not a promise of compatibility."),
            ]),
            ("Five deliberately cheesy tennis lines", "Love, advantage and match point are wordplay here. Save these for someone who seems to enjoy an obvious pun.", [
                ("Love score", "Tennis starts at love. My opening message appears to be taking that very literally.", "The self-aware ending makes the exaggeration part of the joke."),
                ("A match", "I came looking for a tennis match and accidentally started hoping for a dinner one.", "A dating profile with tennis in it supplies the setup."),
                ("Advantage", "Advantage: you. I've already used my best line just saying hello.", "Keep this as one playful message rather than a whole scoring routine."),
                ("At the net", "Are we at the net? Because I'd like to meet you halfway.", "This is intentionally corny and does not require a detailed tennis discussion."),
                ("Tie-break", "If choosing a coffee spot goes to a tie-break, I'll happily play another date.", "Better once you are already discussing places to meet."),
            ]),
        ],
        [
            ("They mention a court", "Them: 'I usually play at Riverside.'\nYou: 'I've walked past those courts. Do you go for casual hits or league matches?'", "Ask about how they enjoy the activity rather than assuming their standard."),
            ("They only watch tennis", "Them: 'I'm strictly a spectator.'\nYou: 'That works too. What's a match you still talk about?'", "Adapt to what they say instead of pressing for a playing date."),
            ("They accept an invitation", "Them: 'A casual hit sounds fun.'\nYou: 'Great. Would Saturday morning suit you? We can pick a court that's convenient for both of us.'", "Move from a joke to one practical question."),
        ],
        ["Mention a court or tournament only if it is visible in the profile or came up in conversation. If you only watch tennis, say so; you do not need to invent a playing history.", "Do not coach their technique from a photo. If the tennis topic gets a short answer, share something about yourself or let the conversation pause."],
    ),
    ("hobbies", "badminton"): _topic(
        "Badminton", "Badminton Pickup Lines: Playful Rallies and Replies",
        "Find 15 badminton pickup lines with shuttle, drop-shot and doubles jokes, plus example replies and ways to turn a shared hobby into conversation.",
        "Badminton gives you more to talk about than a smash pun. Use a club photo, a doubles story or their favorite way to play as the start of a conversation.",
        "Start with one detail about how they play badminton. A playful question about doubles or a casual rally gives them something specific to answer.",
        [
            ("Five witty badminton openers", "Talk about the shared activity without turning your first message into a challenge to prove their skill.", [
                ("Doubles honesty", "My doubles strategy is clear communication, followed by an occasional apology to my partner.", "Useful if you actually play and can laugh about a harmless mistake."),
                ("A favorite shot", "Which is more satisfying: a clean smash or a drop shot that makes everyone reconsider their footwork?", "This invites a player to talk about a preference."),
                ("After the rally", "I respect a long badminton rally. I respect whoever remembered the snacks even more.", "A relaxed club or social-game photo is a suitable opening."),
                ("Choosing a court", "Are you a book-the-court-ahead person or a somehow-find-four-rackets person?", "Ask about their routine rather than assuming they compete."),
                ("Beginner admission", "I'm still learning badminton. My most consistent skill is retrieving the shuttle with enthusiasm.", "Only use the beginner angle if it is true."),
            ]),
            ("Five flirty badminton lines", "Interest can be direct while the proposed activity stays low-pressure.", [
                ("A shared session", "I'd like to be the person you invite for a badminton session that turns into a long conversation.", "It suggests getting to know them beyond the game."),
                ("A doubles invitation", "If you need a doubles partner sometime, I'd enjoy a reason to spend an afternoon with you.", "Let them decide whether an activity together appeals."),
                ("After practice", "Your badminton stories sound worth staying after practice for.", "Use this after they have actually shared a story."),
                ("Two-part plan", "A casual rally, then a drink somewhere we don't have to shout across a court?", "This is a possible date once interest is mutual."),
                ("Getting acquainted", "I want to know your favorite shot, but also your favorite thing to do when the racket stays home.", "Broaden the chat so the hobby is not the only subject."),
            ]),
            ("Five deliberately cheesy badminton lines", "These make the pun obvious. One is plenty for an opening message.", [
                ("Drop shot", "I had a smooth opening planned, but apparently I've gone with a drop shot straight into your DMs.", "Works when badminton is already part of the visible context."),
                ("A rally", "Could we turn this little back-and-forth into the start of a very good rally?", "Use after a couple of messages rather than before they have replied."),
                ("Shuttle service", "My heart has started offering a shuttle service between your profile and the message button.", "An intentionally exaggerated line for someone who likes silly humor."),
                ("Court time", "I'm trying to court you, and for once the booking system might actually help.", "The double meaning lands best if you are discussing playing together."),
                ("Doubles", "Singles is a badminton format. I'm hoping it doesn't have to be our long-term plan.", "This is flirtation, not a serious commitment claim; keep the tone light."),
            ]),
        ],
        [
            ("They play socially", "Them: 'Mostly games with friends.'\nYou: 'That sounds like my pace. Is it friendly competition or does someone keep a very serious score?'", "Reflect their social context instead of asking about rankings."),
            ("They play competitively", "Them: 'I play league doubles.'\nYou: 'What do you enjoy most about having a regular partner?'", "Show curiosity without pretending to understand their league."),
            ("They suggest a game", "Them: 'We should play sometime.'\nYou: 'I'd like that. Want to find a casual session next weekend?'", "Agree clearly and offer one next step."),
        ],
        ["Use badminton details such as a shuttle, a clear or a drop shot where they make sense. Do not recycle a tennis scoring joke and just swap the sport's name.", "If you are new to the game, be honest. An invitation should be about a shared afternoon, not trapping them into giving a stranger a lesson."],
    ),
    ("hobbies", "pickleball"): _topic(
        "Pickleball", "Pickleball Pickup Lines: Dinks, Doubles and Dates",
        "Try 15 pickleball pickup lines with playful dink, paddle and kitchen references, plus follow-up chats and ideas for a casual pickleball date.",
        "A paddle in a dating photo can open a conversation about a regular game, a new hobby or a doubles group. Start there, then give the other person room to talk about more than pickleball.",
        "Use a pickleball detail they shared, add one light joke, and ask an easy question. Keep kitchen and dink references playful rather than turning the message into a rules quiz.",
        [
            ("Five witty pickleball openers", "Specific pickleball references help when they fit the profile. You do not need to claim a rating or competitive experience.", [
                ("Kitchen duties", "I can stay out of the pickleball kitchen. The actual kitchen is where my snack responsibilities begin.", "The joke uses the court term without making a misleading rules claim."),
                ("Paddle shopping", "Did you choose your paddle through careful research or because the color made a convincing argument?", "Ask when a paddle photo or equipment comment makes it relevant."),
                ("Doubles negotiations", "Before we partner up: are we discussing strategy or blaming the wind with dignity?", "Good for a casual outdoor-game context."),
                ("A small victory", "My pickleball highlight reel is currently one patient dink and a surprisingly good post-game sandwich.", "Keep the modest playing claim truthful."),
                ("Social games", "Does your pickleball group finish on time, or does 'one more game' have its own time zone?", "It invites a story about the group rather than demanding personal details."),
            ]),
            ("Five flirty pickleball lines", "A concrete invitation is easier to respond to than a vague promise of chemistry.", [
                ("Off-court conversation", "I'd enjoy being your partner for a game and your company for the coffee afterward.", "Use after you have established some mutual interest."),
                ("An easy plan", "You bring your paddle; I'll bring a genuinely good suggestion for lunch nearby.", "Suggest a real place if they are interested."),
                ("Curiosity", "The pickleball photo got my attention. What's the rest of a good weekend with you like?", "It opens a broader conversation beyond their sport."),
                ("A shared court", "A casual game with you sounds like a much better Saturday than my current plan of considering exercise.", "A little self-deprecation can keep the invitation relaxed."),
                ("Clear interest", "I'd say this is just about finding a doubles partner, but I'd also like to take you on a date.", "Use where a direct expression of interest fits the conversation."),
            ]),
            ("Five deliberately cheesy pickleball lines", "If their profile welcomes puns, these are knowingly silly ways to say hello.", [
                ("Dink about it", "Would you dink about getting coffee with me? I've clearly committed to the pun already.", "The second sentence acknowledges the joke rather than pretending it is smooth."),
                ("In a pickle", "I'm in a pickle: start with a paddle joke or admit I wanted an excuse to talk to you?", "An opener for someone who mentions pickleball explicitly."),
                ("A doubles match", "I thought doubles meant two people on a court. Now I'm hoping it also means dinner for two.", "Save the invitation for a conversation with reciprocal interest."),
                ("Paddle included", "My dating strategy now includes a paddle and a very hopeful hello.", "Works best alongside an honest interest in playing."),
                ("Kitchen plans", "Let's keep the flirting out of the kitchen until we've finished the game and chosen a restaurant.", "This is wordplay about the court area, not advice about how to play."),
            ]),
        ],
        [
            ("They are a beginner", "Them: 'I only started last month.'\nYou: 'What made you give it a try? I'm always curious how people find a new hobby.'", "Their experience is more interesting than testing their knowledge."),
            ("They have a regular group", "Them: 'We play every Sunday.'\nYou: 'That sounds like a good ritual. Do you usually grab food afterward?'", "Ask about the social side without inviting yourself into the group."),
            ("They like the date idea", "Them: 'Coffee after a game sounds good.'\nYou: 'Want to try Saturday afternoon? We can pick a public court and a cafe nearby.'", "Move to practical plans once they agree."),
        ],
        ["Use only profile details you can see. A paddle photo does not tell you their rating, availability or interest in teaching you.", "A beginner can say they are a beginner. If the other person does not respond, skip the sequence of increasingly elaborate dink jokes."],
    ),
    ("professions", "data-scientist"): _topic(
        "Data Scientist", "Data Scientist Pickup Lines: Clever, Flirty and Nerdy",
        "Explore 15 data scientist pickup lines about models, charts and messy data, with follow-up examples and tips for keeping the conversation human.",
        "A data-science reference can be a shared joke, not a test of someone's technical knowledge. Match the level of detail in their profile, then ask about the person behind the job title.",
        "Choose one data-science joke you understand and connect it to a real profile detail. Follow with an ordinary question rather than treating a date like an interview or an experiment.",
        [
            ("Five witty data-science openers", "These are light references to working with data. Use a technical term only if you would be comfortable talking about it.", [
                ("Chart preferences", "Your profile mentions data science. What chart type do you defend with unreasonable enthusiasm?", "It invites a harmless opinion without asking for confidential work."),
                ("Messy inputs", "My weekend plans are unstructured data, but a coffee invitation could give them a useful schema.", "Best when both people enjoy a little technical wordplay."),
                ("An honest baseline", "I considered optimizing this opener, then decided a sincere hello was a respectable baseline.", "You can follow with a specific detail from their profile."),
                ("A human review", "My recommendation system suggested saying something normal, so naturally I'm asking about your favorite bakery.", "Use if their profile gives a food or neighborhood connection."),
                ("Notebook habits", "Do your personal notes have sensible names, or is there a final_final_v3 situation we should discuss?", "A relatable file-name joke does not presume how good they are at their job."),
            ]),
            ("Five flirty data-science lines", "Express interest without making someone sound like a dataset to be studied.", [
                ("An actual date", "I'd like to trade one evening of looking at dashboards for one evening getting to know you.", "Use only if dashboards really are part of your own routine."),
                ("Beyond the bio", "Your work sounds interesting. I'm even more curious about what makes you forget to check your phone.", "It gives them permission to choose a non-work subject."),
                ("A clear invitation", "No elaborate model: I like talking with you, and I'd like to get coffee.", "A direct next step is useful once conversation is flowing both ways."),
                ("Shared curiosity", "I like the way you explain things. I'd enjoy continuing this conversation somewhere with dessert.", "Base the compliment on an explanation they actually gave."),
                ("A weekend question", "When your laptop closes for the weekend, I'd like to be part of a plan you're excited about.", "This is warmer than an opening message; use it after a connection develops."),
            ]),
            ("Five deliberately cheesy data-science lines", "The statistics are metaphors, not claims that a line can predict romantic success.", [
                ("Missing values", "My calendar has a missing value where a date with you could go.", "A simple joke with a clear invitation behind it."),
                ("A useful feature", "Your smile wasn't in my feature set, and now the whole model needs revisiting.", "A deliberately nerdy compliment suited to reciprocal flirting."),
                ("Confidence interval", "My confidence interval for this opening line is wide, but the interest is quite specific.", "The uncertainty is part of the joke, not a request for reassurance."),
                ("Training data", "None of my training data prepared me for wanting to send such a cheesy message.", "Keep it light and move to a real topic if they reply."),
                ("A scatter plot", "If this chat were a scatter plot, I'd be hoping the next point was a coffee shop.", "This is playful imagery rather than a technical explanation."),
            ]),
        ],
        [
            ("They enjoy the reference", "Them: 'A sensible baseline is underrated.'\nYou: 'Agreed. My other dependable baseline is a long walk on Sunday. What's yours?'", "Use the shared joke to reveal a real preference."),
            ("They do not want work chat", "Them: 'Please, no more models today.'\nYou: 'Fair. What's been the best non-work part of your week?'", "Respect the change of subject immediately."),
            ("They mention a hobby", "Them: 'I spend weekends making pottery.'\nYou: 'What have you made recently that you're pleased with?'", "Stay with their chosen topic instead of forcing another data pun."),
        ],
        ["A job title does not establish personality, intelligence relative to others or preferred humor. Mention the detail they shared, then let their reply guide you.", "Keep these for dating or social conversations where interest is welcome. Do not request private datasets, employer information or a technical demonstration to keep chatting."],
    ),
    ("professions", "journalist"): _topic(
        "Journalist", "Journalist Pickup Lines: Headlines, Humor and Dates",
        "Read 15 journalist pickup lines with headline and deadline wordplay, plus natural follow-up conversations that go beyond asking about work.",
        "Journalism can provide a playful opening, but someone on a dating app is not there to interview you. Use a writing or reporting reference, then make room for their interests outside work.",
        "Try one headline or editing joke and a question they can answer without discussing a current assignment. If they want a break from work, change the subject.",
        [
            ("Five witty journalist openers", "Let the joke be about wording or everyday habits, not pressure to share a scoop.", [
                ("A first draft", "This hello has survived two drafts and one unnecessary adjective. I hope the editor approves.", "Use if writing is a visible part of their profile."),
                ("Weekend headline", "What's the headline for your ideal Sunday: ambitious outing or local person stays in pajamas?", "The options open a conversation about leisure."),
                ("An editorial decision", "Would you edit 'coffee sometime' into a stronger sentence with a day and a place?", "Useful once you are both discussing meeting."),
                ("A harmless debate", "Which gets the stronger editorial: a terrible movie or a disappointing sandwich?", "It asks for a light preference rather than a professional judgment."),
                ("Word economy", "I was aiming for a concise opener, but your book recommendations may require a follow-up edition.", "Only use if the profile actually mentions books."),
            ]),
            ("Five flirty journalist lines", "Be interested in the person. Their job is a conversation detail, not the entire attraction.", [
                ("An invitation", "I'd like to hear the story behind that travel photo over coffee, if you're interested.", "Refer to an actual photo and leave room to decline."),
                ("A personal detail", "The article link was interesting. The small joke in your bio is what made me want to say hello.", "Use only after reading both; do not pretend familiarity with their work."),
                ("A conversation", "You make ordinary details interesting. I'd like another hour of this conversation in person.", "This compliment belongs after a real exchange."),
                ("A date, clearly", "No interview questions from me tonight. I'd just like to take you somewhere nice and get to know you.", "An appropriate invitation when the interest is mutual."),
                ("After the deadline", "When you have an evening free, I'd enjoy being part of your plans away from the deadline.", "Let them choose their availability rather than assuming their schedule."),
            ]),
            ("Five deliberately cheesy journalist lines", "These use newsroom language as obvious wordplay. They are not requests for access to someone's work.", [
                ("Breaking news", "Breaking news: local person opens dating app and immediately forgets their prepared greeting.", "The joke is on the sender, not on their profession."),
                ("A headline", "I had a headline ready, but 'I'd like to meet you' seems to cover the story.", "A straightforward invitation wrapped in a small pun."),
                ("The next edition", "Could the next edition of my weekend include dinner with you?", "Use once proposing a date feels welcome."),
                ("A correction", "Correction: when I said 'nice profile,' I meant 'I'd really like to talk to you.'", "A silly clarification that communicates interest plainly."),
                ("Human interest", "This is becoming a human-interest story, and the human is me.", "It works as a knowingly corny response during friendly banter."),
            ]),
        ],
        [
            ("They mention their beat", "Them: 'I mostly cover local arts.'\nYou: 'That sounds interesting. Is there a public exhibition you'd recommend to someone new to the area?'", "Ask for public recommendations, not inside information."),
            ("They want a break", "Them: 'I'm trying not to think about deadlines.'\nYou: 'Understood. Tell me about something you're looking forward to outside work.'", "Acknowledge the boundary and give them another subject."),
            ("They suggest coffee", "Them: 'Coffee sounds good.'\nYou: 'Would Saturday at two work? There's a quiet place near the library, if that area suits you.'", "Offer a specific plan without turning the chat into an interview."),
        ],
        ["Read anything you mention. A sincere question about a public article is better than pretending to know their work.", "Do not ask about confidential sources or treat professional curiosity as romantic interest. Keep flirting in an appropriate social setting, separate from interviews and assignments."],
    ),
    ("professions", "optometrist"): _topic(
        "Optometrist", "Optometrist Pickup Lines: Eye Puns and Real Conversation",
        "Find 15 optometrist pickup lines, from eye-chart jokes to direct invitations, with follow-up examples for dating and social conversations.",
        "An eye-care reference can be a light way to acknowledge a dating-profile detail. Keep the joke brief, then ask about the person rather than turning the conversation into an appointment.",
        "Use one eye or lens pun in a dating context, then follow with an ordinary question. An optometrist's friendliness during an appointment is professional care, not an invitation to flirt.",
        [
            ("Five witty optometrist openers", "These are social jokes, not medical questions or claims about vision.", [
                ("Two options", "Which is better: coffee on Saturday, or coffee on Sunday? I promise those are the only options in this test.", "A familiar phrase becomes a clear invitation once interest is mutual."),
                ("Frame choices", "Your profile has excellent glasses. Were they a quick choice or a forty-frame negotiation?", "Use only when glasses are actually visible; ask about style rather than eyesight."),
                ("A small adjustment", "I adjusted this opener several times and somehow 'hello' still looks like the clearest option.", "A simple self-aware way to begin."),
                ("An evening off", "When you're off duty, do you prefer a detailed plan or seeing where the afternoon goes?", "The answer can lead to a conversation about free time."),
                ("The reading test", "I can read the small print on the menu. Choosing what to order is where I need assistance.", "A light food topic gives the other person an easy way into the chat."),
            ]),
            ("Five flirty optometrist lines", "Make the interest about a possible date, not about receiving professional attention.", [
                ("Clear interest", "I don't have a clever eye joke left. I do have a genuine interest in getting to know you.", "Use it when a simple statement fits your voice."),
                ("Beyond the job", "Your work caught my attention; your weekend photos made me want to hear more.", "Mention a real photo next so the compliment stays specific."),
                ("A shared evening", "I'd like to see you across a dinner table, if that sounds good to you too.", "A direct invitation makes mutual choice explicit."),
                ("A smile", "That smile in your hiking photo is a good reason to ask how the trip went.", "Use only if that photo exists; do not invent a shared context."),
                ("An easy plan", "An evening walk and a coffee with you sounds like a plan worth making.", "Offer this after the conversation has shown reciprocal interest."),
            ]),
            ("Five deliberately cheesy optometrist lines", "Eye puns are the whole point here. Choose one, then give the conversation somewhere else to go.", [
                ("In focus", "My weekend was a little blurry until the idea of a date with you came into focus.", "This is a metaphor, not a statement about an actual vision problem."),
                ("An eye chart", "If this were an eye chart, the big letter at the top would stand for Hello.", "An intentionally goofy first message for someone who welcomes puns."),
                ("A lens", "I may need a wider lens to fit all the date ideas your travel photos just gave me.", "Use real travel details and follow with one plausible idea."),
                ("A frame", "I've been trying to frame this smoothly, but would you like to get coffee?", "The pun leads directly to a question they can answer."),
                ("Seeing potential", "I'm seeing potential here, and for once that isn't a request for a prescription.", "Keep this in a dating conversation, never a clinical appointment."),
            ]),
        ],
        [
            ("They laugh at the pun", "Them: 'I've heard a lot of eye jokes, but that was new.'\nYou: 'I'll retire while I'm ahead. What do you like doing on a free afternoon?'", "Let one joke lead into a normal conversation."),
            ("They mention an interest", "Them: 'I spend most weekends hiking.'\nYou: 'Do you have a favorite local trail? I'm looking for a new weekend walk.'", "Stay with the hobby they volunteered."),
            ("They do not like work jokes", "Them: 'No eye puns, please.'\nYou: 'Fair request. Your bio also mentions baking; what have you made lately?'", "Drop the joke immediately and reference another real detail, if available."),
        ],
        ["Use these with someone you meet through a dating app or an appropriate social setting. Do not turn an appointment into a dating approach or ask for health advice as an excuse to keep messaging.", "You do not need to know technical eye-care terms. A profile detail, a clear invitation and an honest reply can carry the conversation without another pun."],
    ),
}


PICKUP_EXPANSION = {
    ("dating-apps", "tinder-opener"): _topic(
        "Tinder Opener", "Tinder Openers: First Messages and Follow-Up Examples",
        "Find Tinder openers based on hobbies, photos and a short bio, with direct alternatives to jokes and examples of what to say after a match replies.",
        "A first message needs a starting point, not a performance. Use a detail your match chose to share, offer a little of your own personality, and give them an easy way to answer.",
        "For a Tinder opener, reference one visible profile detail and ask a small, specific question. If the bio is sparse, use an ordinary preference question instead of guessing who they are.",
        [
            ("Openers with a little humor", "Use the actual hobby or photo in front of you. Replace fictional details with something true.", [
                ("A cooking photo", "That homemade pizza looks serious. Are you a follow-the-recipe person or a cheese-is-a-measurement person?", "It gives a cooking enthusiast an easy choice to respond to."),
                ("A dog photo", "Your dog looks very pleased with that walk. Who usually decides when it's time to go home?", "A light question about the photo avoids assuming the dog's breed or name."),
                ("A book mention", "I noticed your book recommendation. Should I clear a whole weekend or expect to keep a normal sleep schedule?", "Use only if the book really appears in their profile."),
            ]),
            ("Direct openers without a punchline", "Warm curiosity is enough. You do not have to make every first message flirty.", [
                ("A shared interest", "You mentioned weekend markets. I like finding one good thing to cook afterward. What's your usual first stop?", "Include your own detail so it does not feel like a questionnaire."),
                ("A travel photo", "That coast looks beautiful. What did you enjoy most about the trip?", "Ask about their experience without guessing an exact location."),
                ("Limited profile information", "Hi, nice to meet you. What's a small thing you're looking forward to this week?", "A sparse profile does not justify inventing a personal detail."),
            ]),
            ("Cheesy openers for a profile that welcomes them", "If their bio explicitly asks for a bad joke, a knowingly silly opener can fit. Otherwise, start with the person.", [
                ("The bad-joke invitation", "Your bio requested a terrible opener. I'd hate to disappoint you by suddenly becoming smooth.", "The request in the bio supplies the context; do not use it if absent."),
                ("A small confession", "I had a pickup line ready, but your playlist distracted me into wanting an actual conversation.", "Follow with a real song or artist from their profile."),
                ("A coffee connection", "Your coffee photo and my cafe loyalty card appear to have arranged this introduction.", "It is an obvious joke about a shared interest, not a claim about matching algorithms."),
            ]),
        ],
        [
            ("They answer enthusiastically", "Them: 'I always buy too many tomatoes at the market.'\nYou: 'Same. I end up making enough sauce for a small restaurant. Do you have a favorite recipe?'", "Respond to the detail and add something of your own."),
            ("They give a short answer", "Them: 'Mostly beach trips.'\nYou: 'I'm usually a long-walk-and-find-lunch traveler. Do you prefer exploring or a day with no plans?'", "Try one easy follow-up without treating brevity as a challenge to overcome."),
            ("They ask about you", "Them: 'What are you looking forward to?'\nYou: 'Dinner with an old friend on Friday. We're attempting a recipe neither of us has read properly.'", "Answer their question; do not immediately replace it with another one."),
        ],
        ["Keep your opener short enough to read easily and specific enough to answer. Never claim to recognize a location, pet or book if you do not.", "No response does not prove the opener was wrong. Avoid sending a string of alternatives; leave room for the other person to choose whether to engage."],
    ),
    ("professions", "barista"): _topic(
        "Barista", "Barista Pickup Lines: Coffee Puns and Conversation",
        "Explore barista pickup lines, coffee-themed invitations and natural alternatives, with follow-up chats for dating profiles and social settings.",
        "Coffee can be the opening subject without making someone's whole identity their job. These examples are for dating and social conversations where flirting is welcome.",
        "A coffee pun can say hello, but a question about their tastes gives the conversation somewhere to go. In a cafe, service and politeness are part of the job; use these in a mutual social or dating context.",
        [
            ("Witty coffee openers", "Aim for a shared coffee habit rather than a claim about what all baristas are like.", [
                ("Home coffee", "Do you make elaborate coffee at home, or does the kettle get a well-earned promotion on days off?", "It leaves room for them to prefer something other than coffee."),
                ("Taste preferences", "What's your most defensible coffee opinion? Mine is that the pastry is part of the order.", "Offer an opinion of your own to make the exchange mutual."),
                ("Learning honestly", "I can make breakfast, but my latte art still looks like a weather map. Do I get points for interpretation?", "Use this if making coffee is something you actually enjoy."),
            ]),
            ("Flirty alternatives to another coffee pun", "A direct invitation can be warmer than another joke about caffeine.", [
                ("A day off", "I'd like to take you somewhere you can sit down and let someone else bring the drinks.", "Use when you are already discussing a date, not while they are serving you."),
                ("Their interests", "Your cafe stories are fun, but I'd also like to hear about that ceramics class you mentioned.", "Refer to something they actually shared beyond work."),
                ("Choosing a place", "Want to pick a place for a long conversation? I'm happy with coffee, tea or your favorite alternative.", "Do not assume a barista wants a coffee date."),
            ]),
            ("Deliberately cheesy coffee lines", "These are best for someone who enjoys puns and has already made room for flirting.", [
                ("An espresso joke", "I'm trying to espresso an interest in dinner, and apparently this is how I've chosen to do it.", "The joke ends in a clear invitation rather than a vague compliment."),
                ("A filter", "I put this message through a filter and somehow the coffee pun still got through.", "A self-aware opener that can lead into a normal question."),
                ("A latte", "There's a latte I'd like to know about you, starting with your ideal day off.", "A silly pun followed by a real subject gives them something to answer."),
            ]),
        ],
        [
            ("They prefer tea", "Them: 'Honestly, I drink tea at home.'\nYou: 'Then tea gets my vote. What's your favorite kind?'", "Follow their preference instead of defending the coffee theme."),
            ("They mention a hobby", "Them: 'I spend days off cycling.'\nYou: 'Is that a long ride with a destination or a wander until you find somewhere good to stop?'", "Let the conversation move beyond work."),
            ("They accept a date", "Them: 'A place where I can sit down sounds great.'\nYou: 'Would the little tea room near the park suit you on Sunday afternoon?'", "Offer one concrete option after they express interest."),
        ],
        ["Use profile details or a conversation you are both choosing to have. Someone remembering your regular order is not evidence of romantic interest.", "Avoid approaches that interrupt a shift or make a worker feel obliged to respond. If a date sounds welcome, choose a setting where neither person has to provide a service to the other."],
    ),
    ("professions", "flight-attendant"): _topic(
        "Flight Attendant", "Flight Attendant Pickup Lines: Aviation Puns and Replies",
        "Read flight-attendant pickup lines, aviation jokes and direct date invitations, with follow-up examples that move beyond talking about work.",
        "Aviation wordplay can be fun when a dating profile invites it. A flight attendant is also a person with interests and plans unrelated to routes, airports or uniforms.",
        "Use an aviation reference lightly, then ask about a real interest from the profile. Keep flirting to appropriate social or dating settings; friendliness while working a flight is professional service.",
        [
            ("Witty aviation openers", "Ask about public preferences, not private schedules or travel access.", [
                ("Packing habits", "I pack for a weekend as though weather might develop new categories. Do you have a calmer approach?", "An everyday travel habit is easier to discuss than an employer or roster."),
                ("An ordinary day", "After all the travel, is your ideal day off an adventure or a very loyal relationship with your sofa?", "Let them choose how much they want to talk about travel."),
                ("A travel opinion", "My controversial airport opinion is that a good book counts as a complete itinerary. What's yours?", "Use if reading and travel are genuine interests of yours."),
            ]),
            ("Direct invitations and conversation starters", "The job title can start a chat; it should not supply every question.", [
                ("A flexible invitation", "When you have a free afternoon, I'd like to take you for coffee somewhere you can stay as long as you like.", "Do not guess their working hours or press for their schedule."),
                ("Beyond the travel photo", "The city photo caught my eye, but the hobby in your bio is what I'd like to hear more about.", "Name the actual hobby in your message."),
                ("Clear interest", "I'm enjoying this conversation. Would you like to continue it over dinner when our calendars line up?", "Make mutual availability part of the invitation."),
            ]),
            ("Deliberately cheesy flight-attendant lines", "One aviation pun is enough. Avoid comments that reduce someone to their uniform or appearance at work.", [
                ("An itinerary", "My next itinerary is remarkably simple: meet you, find coffee, forget to check the time.", "A fictional plan can express interest without assuming agreement."),
                ("An arrival", "This opening line has landed with all the elegance of my overpacked suitcase.", "The humor is directed at the sender."),
                ("A destination", "I've stopped researching destinations and started hoping the next one is dinner with you.", "A playful date invitation belongs after some reciprocal conversation."),
            ]),
        ],
        [
            ("They prefer staying home", "Them: 'Days off are mostly cooking and doing nothing.'\nYou: 'That sounds good to me. What's your favorite thing to cook when you have time?'", "Respect the answer instead of pushing another travel question."),
            ("They have an uncertain schedule", "Them: 'I don't know next week's plans yet.'\nYou: 'No problem. If you'd like to meet when you know, send me a day that suits you.'", "Leave the choice with them rather than repeatedly checking."),
            ("They suggest a time", "Them: 'I'm free Sunday afternoon.'\nYou: 'Would three work? We could meet at the cafe by the park if that's convenient.'", "One practical proposal is enough to move toward a date."),
        ],
        ["Do not ask for staff benefits, private rosters, hotel details or an introduction as a pretext for flirting. Use interests the person voluntarily shares.", "Professional hospitality is not a romantic signal. These examples belong in a dating conversation or a social setting where either person can comfortably decline."],
    ),
    ("fandoms", "lord-of-the-rings"): _topic(
        "Lord of the Rings", "Lord of the Rings Pickup Lines: Puns and Follow-Ups",
        "Find original Lord of the Rings pickup lines, gentle Middle-earth jokes and follow-up conversations for fellow fans, from second breakfast to a date.",
        "A Middle-earth reference can be a shared smile, not a lore exam. Start with the part of the story they mention and find out how they enjoy it: books, films, artwork or a comfort rewatch.",
        "Choose a reference your match is likely to recognize and pair it with a real question. A second-breakfast joke can lead to favorite food; a walking joke can become a casual date idea.",
        [
            ("Witty Middle-earth openers", "These are original jokes about familiar story elements, not quotations from the books or films.", [
                ("Second breakfast", "Before we plan anything, I need to know whether your ideal weekend makes room for second breakfast.", "An accessible food reference gives even a casual fan an easy answer."),
                ("Travel planning", "Would your Middle-earth holiday be a peaceful stay in the Shire or an itinerary your friends would question?", "Let them choose an atmosphere without testing obscure lore."),
                ("A small adventure", "My weekend adventures involve less Mount Doom and more finding a bakery before it sells out.", "Share a real preference and invite them to offer theirs."),
            ]),
            ("Flirty lines for a fellow fan", "Keep the interest human even when the setting is fictional.", [
                ("A walking date", "I'd enjoy a long walk with you, preferably with more cafe stops than an epic quest usually allows.", "A shared love of the story can lead to an ordinary, practical date."),
                ("An evening together", "You choose the film; I'll bring enough snacks to make a hobbit comfortable.", "Best after you know each other; an initial date can be somewhere public."),
                ("An honest invitation", "We seem to agree about good stories. I'd like to find out whether we also agree about good coffee.", "Move from fandom to a clear invitation once interest is mutual."),
            ]),
            ("Deliberately cheesy Lord of the Rings lines", "Use the silliness knowingly. A borrowed fantasy setting does not need an exaggerated romantic promise.", [
                ("A fellowship", "I'm assembling a fellowship of two for a very manageable quest to get lunch.", "A deliberately small adventure makes the invitation light."),
                ("A precious plan", "My most precious possession right now is a cafe recommendation I'd like to share with you.", "The joke is about a recommendation, not treating the person as a possession."),
                ("An unexpected message", "An unexpected journey has begun, and so far it consists of me trying to write a decent hello.", "An approachable nod that does not require detailed plot knowledge."),
            ]),
        ],
        [
            ("They love the films", "Them: 'The films are my rainy-day comfort watch.'\nYou: 'That sounds like a good ritual. Do you settle in for one, or does it become a whole weekend?'", "Ask how they enjoy the story rather than whether they qualify as a fan."),
            ("They mention the books", "Them: 'I reread the books every few years.'\nYou: 'Is there a place in the story you always look forward to returning to?'", "Invite their perspective without pretending you share the same reading history."),
            ("They pick breakfast", "Them: 'Second breakfast is essential.'\nYou: 'Then we agree on the important part. Would you like to try the bakery near the station on Saturday?'", "Turn a shared joke into one concrete suggestion."),
        ],
        ["Use familiar references accurately, and be honest if you have only seen the films or are new to the books. Curiosity is a better conversation starter than gatekeeping.", "If they answer with another interest, follow it. You do not need to keep every message in Middle-earth or quote long passages to show you like the story."],
    ),
}

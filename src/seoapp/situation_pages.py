SITUATION_PAGE_FIELDS = (
    "slug",
    "situation",
    "h1",
    "title",
    "meta_description",
    "prefill_text",
    "seo_sections",
    "screenshot_tip",
    "sidebar_label",
    "upload_hint",
    "force_show_upload",
    "related_slugs",
)


def _to_sentence(text, fallback):
    value = str(text or "").strip()
    if not value:
        return fallback
    if value.endswith((".", "!", "?")):
        return value
    return f"{value}."


def _normalize_rule(rule_text):
    normalized = str(rule_text or "").strip()
    if not normalized:
        return ""
    normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
    if not normalized.endswith((".", "!", "?")):
        normalized = f"{normalized}."
    return normalized


def _build_rule_bullets(framework, mistakes):
    mistakes_raw = (
        str(mistakes or "")
        .replace(" and ", ", ")
        .replace(";", ",")
        .replace("  ", " ")
        .strip()
    )
    parts = [item.strip() for item in mistakes_raw.split(",") if item.strip()]
    normalized_parts = [_normalize_rule(part) for part in parts if _normalize_rule(part)]
    while len(normalized_parts) < 2:
        normalized_parts.append("Avoid overcomplicating the next message.")

    return [
        _to_sentence(
            f"Lead with structure and context: {framework}",
            "Lead with structure and context before sending the next message.",
        ),
        normalized_parts[0],
        normalized_parts[1],
    ]


def _build_screenshot_tip(topic, upload_hint):
    return (
        f"Upload a screenshot into the tool above before sending your next text. "
        f"{_to_sentence(upload_hint, 'Context from your real chat helps the AI match tone and timing more accurately.')}"
    )


def _build_seo_sections(topic, pain_point, framework, mistakes, tool_hook, close, claim_html=""):
    claim_line = f" {claim_html}" if claim_html else ""
    sections = [
        {
            "heading": f"Why {topic} Gets Stuck",
            "paragraphs": [
                (
                    f"{topic} is usually a momentum problem, not a value problem. {pain_point} "
                    "Most chats do not collapse because people are incompatible, they collapse because the next message "
                    "has no direction. When the thread slows down, overthinking starts, timing gets worse, and every reply "
                    "feels riskier than it really is."
                ),
                (
                    f"A practical way to handle this moment is to use a repeatable framework. {_to_sentence(framework, 'Use a repeatable framework.')}"
                    "The strongest texts usually do three things at once: they acknowledge current context, add emotional "
                    "texture, and create a clear next beat. That structure keeps your message from sounding random or needy."
                    f"{claim_line}"
                ),
            ],
        },
        {
            "heading": "The 3 Rules for Better Replies",
            "paragraphs": [
                (
                    "Most people lose ground by making predictable errors, especially when they react emotionally to a slow or awkward thread. "
                    "Instead of improvising under pressure, follow a compact set of rules you can execute every time. "
                    "These rules keep your message clear, socially calibrated, and easier to answer."
                ),
            ],
            "bullets": _build_rule_bullets(framework, mistakes),
        },
        {
            "heading": "How TryAgainText Finds the Right Reply",
            "paragraphs": [
                (
                    f"This is exactly where the scenario tool helps. {_to_sentence(tool_hook, 'Use the tool to generate response options tailored to your chat.')}"
                    "Instead of writing from emotion, you can compare multiple response angles and choose the one that "
                    "matches both your style and her vibe. That turns a stressful texting moment into a clear decision with "
                    "better odds of a positive reply."
                ),
                (
                    "Because the response options are generated from your real context, they are faster to evaluate and easier to send without second-guessing. "
                    "You still make the final choice, but you avoid the blank-page hesitation that usually kills timing in key moments."
                ),
            ],
        },
        {
            "heading": "What to Do Next",
            "paragraphs": [
                (
                    f"If this pattern keeps showing up in your chats, practice it deliberately. {_to_sentence(close, 'Keep refining your approach with consistent practice.')}"
                    "The objective is not to sound scripted. The objective is to build a reliable texting process that "
                    "creates better momentum, stronger connection, and cleaner paths toward real dates."
                ),
                (
                    "A useful way to improve quickly is to treat every conversation like a feedback loop. Keep the parts "
                    "that get warm responses, discard low-performing patterns, and refine your phrasing based on real outcomes. "
                    "With enough repetition, you stop freezing in key moments because you already know what kind of message "
                    "creates traction. That is how this scenario approach compounds: clearer decisions, better timing, and "
                    "more consistent results without losing your own voice. Over time this becomes a practical texting system "
                    "you can rely on under pressure, not just a one-off answer for one conversation."
                ),
            ],
        },
    ]
    return sections


def _page(
    slug,
    situation,
    h1,
    title,
    meta_description,
    prefill_text,
    upload_hint,
    force_show_upload,
    related_slugs,
    topic,
    pain_point,
    framework,
    mistakes,
    tool_hook,
    close,
    claim_html="",
):
    return {
        "slug": slug,
        "situation": situation,
        "h1": h1,
        "title": title,
        "meta_description": meta_description,
        "prefill_text": prefill_text,
        "seo_sections": _build_seo_sections(
            topic=topic,
            pain_point=pain_point,
            framework=framework,
            mistakes=mistakes,
            tool_hook=tool_hook,
            close=close,
            claim_html=claim_html,
        ),
        "screenshot_tip": _build_screenshot_tip(topic, upload_hint),
        "sidebar_label": h1,
        "upload_hint": upload_hint,
        "force_show_upload": force_show_upload,
        "related_slugs": related_slugs,
    }


SITUATION_PAGES = {
    "what-to-say-next-over-text": _page(
        slug="what-to-say-next-over-text",
        situation="stuck_after_reply",
        h1="Not Sure What to Say? Generate the Perfect Reply.",
        title="What To Say Next Over Text | TryAgainText",
        meta_description="Learn how to keep a text conversation going when you feel stuck after a reply. Get send-ready responses with context-aware AI.",
        prefill_text="You: We should compare coffee spots sometime.\nHer: Haha yeah maybe.",
        upload_hint="Drop in a screenshot when the chat feels vague and you need a clean next line.",
        force_show_upload=False,
        related_slugs=[
            "how-to-respond-to-dry-texts",
            "how-to-change-the-subject-over-text",
            "what-to-text-after-left-on-read",
        ],
        topic="Feeling stuck after she replies",
        pain_point="You get a neutral response and suddenly every idea feels wrong.",
        framework="Use conversation threading: pull one detail from her text, add one playful or sincere angle, then guide the chat into a fresh mini-topic.",
        mistakes="Do not mirror low energy, do not panic-text a paragraph, and do not stack generic questions.",
        tool_hook="Paste the exact exchange and generate three send-ready replies with different tones so you can pick quickly and keep timing on your side.",
        close="As you repeat this workflow, you will recognize branch points faster and keep more conversations alive without sounding forced.",
    ),
    "best-dating-app-openers": _page(
        slug="best-dating-app-openers",
        situation="just_matched",
        h1="The Perfect First Message to Send Your Match.",
        title="Best Dating App Openers | TryAgainText",
        meta_description="Generate strong Tinder and Hinge openers based on profile context. Skip boring first messages and start with momentum.",
        prefill_text="Her profile: Golden retriever, weekend hikes, and matcha addiction.\nWrite a playful first message that feels specific.",
        upload_hint="Upload her profile screenshot to get an opener based on her photos and prompts.",
        force_show_upload=True,
        related_slugs=[
            "how-to-flirt-over-text",
            "how-to-be-witty-over-text",
            "how-to-ask-her-out-over-text",
        ],
        topic="First-message openers on dating apps",
        pain_point="Most matches receive the same boring opener patterns, so generic messages are invisible by default.",
        framework="Use contextual openers: reference one profile detail, add a playful angle, and end with an easy response hook.",
        mistakes="Avoid \"hey\" openers, avoid copy-paste pickup lines, and avoid long intros that feel like performance.",
        tool_hook="Upload her profile screenshot and generate opener options that are witty, direct, and tailored to her visible context.",
        close="This gives you a repeatable launch sequence for every match and improves the odds that the conversation starts with real energy.",
        claim_html="Contextual first messages often produce a <strong>300% higher reply rate</strong> than generic openers because they feel specific and intentional.",
    ),
    "how-to-respond-to-dry-texts": _page(
        slug="how-to-respond-to-dry-texts",
        situation="dry_reply",
        h1="How to Respond to a Dry Text (And Spark Interest).",
        title="How To Respond To Dry Texts | TryAgainText",
        meta_description="Get better replies when she sends short or low-effort texts. Learn how to handle dry texting without sounding needy.",
        prefill_text="You: That rooftop spot looked fun, you go often?\nHer: Lol",
        upload_hint="Upload the thread when replies turn into 'lol' or 'yeah' so the AI can reset the vibe.",
        force_show_upload=False,
        related_slugs=[
            "what-to-say-next-over-text",
            "stop-boring-text-conversations",
            "how-to-flirt-over-text",
        ],
        topic="Responding to dry texts",
        pain_point="One-word replies create ambiguity and make it hard to tell whether the issue is interest, timing, or conversation quality.",
        framework="Shift emotional texture: acknowledge the vibe, add playful tension, and move into a clearer hook she can actually engage with.",
        mistakes="Do not chase with multiple messages, do not punish her tone, and do not keep pushing the same dead topic.",
        tool_hook="Paste the dry exchange and generate options for playful re-engagement, clean pivots, and stronger conversation hooks.",
        close="Once you stop reacting emotionally to dry messages, you can recover more threads and protect your own composure.",
    ),
    "what-to-text-after-left-on-read": _page(
        slug="what-to-text-after-left-on-read",
        situation="left_on_read",
        h1="Left on Read? Here is Exactly What to Text Next.",
        title="What To Text After Left On Read | TryAgainText",
        meta_description="Learn when and how to follow up after being left on read. Generate casual re-engagement texts that avoid neediness.",
        prefill_text="You: Mini golf rematch this weekend?\n[No response for 48 hours] AI, write a casual follow-up.",
        upload_hint="If she has not replied in 24-72 hours, upload the thread and get a calm follow-up option.",
        force_show_upload=False,
        related_slugs=[
            "restart-dead-conversation",
            "what-to-say-next-over-text",
            "how-to-recover-awkward-text",
        ],
        topic="Following up after being left on read",
        pain_point="Silence creates pressure, and that pressure pushes people into reactive texts that usually make things worse.",
        framework="Use calm re-entry: low-pressure wording, fresh context, and a message that does not demand emotional explanation.",
        mistakes="Skip guilt texts, skip passive-aggressive comments, and skip long explanations about why she did not respond.",
        tool_hook="Paste your last exchange and generate follow-ups that reopen momentum while keeping your tone confident and clean.",
        close="Handled well, a single calm follow-up can recover a thread without compromising your standards.",
    ),
    "how-to-ask-her-out-over-text": _page(
        slug="how-to-ask-her-out-over-text",
        situation="ask_her_out",
        h1="How to Smoothly Ask Her Out Over Text (Without Being Awkward).",
        title="How To Ask Her Out Over Text | TryAgainText",
        meta_description="Ask for a date confidently over text with clear, specific plans. Generate low-pressure asks that get better responses.",
        prefill_text="We've been talking for a few days. How do I ask her out for coffee?",
        upload_hint="Upload your current thread to generate a smooth soft-pitch or hard-pitch date invite.",
        force_show_upload=False,
        related_slugs=[
            "how-to-ask-for-number-tinder",
            "what-to-say-next-over-text",
            "best-dating-app-openers",
        ],
        topic="Asking her out over text",
        pain_point="Good conversations often stall at the transition point from chat chemistry to real plans.",
        framework="Use a soft pitch to test interest, then a hard pitch with specific time and activity when momentum is strong.",
        mistakes="Avoid vague invites, avoid over-selling the date, and avoid negotiating against yourself before she responds.",
        tool_hook="Paste your recent thread and generate date asks from low-pressure to direct so you can choose the right level of intent.",
        close="Clear invites create decisive outcomes and help you convert chats into real-life meetings more consistently.",
    ),
    "how-to-flirt-over-text": _page(
        slug="how-to-flirt-over-text",
        situation="spark_interest",
        h1="Turn Boring Texts into Flirty Messages.",
        title="How To Flirt Over Text | TryAgainText",
        meta_description="Learn how to make texts playful and flirty without trying too hard. Build attraction with better message structure.",
        prefill_text="You: How's your week going?\nHer: Busy but good.\nYou: Help me make this less boring and more flirty.",
        upload_hint="Share a screenshot when the chat feels friendly but not flirty so we can raise attraction cleanly.",
        force_show_upload=False,
        related_slugs=[
            "how-to-be-witty-over-text",
            "sincere-text-messages",
            "how-to-respond-to-dry-texts",
        ],
        topic="Making texts more flirty",
        pain_point="Many conversations stay polite and friendly for too long, which keeps attraction flat even when interest exists.",
        framework="Blend warm intent with playful assumptions, teasing, or light challenges that invite banter instead of small talk.",
        mistakes="Do not jump from safe to extreme, do not force edgy humor, and do not copy lines that do not match your voice.",
        tool_hook="Paste the current chat and generate flirty options with different intensity so you can stay calibrated and authentic.",
        close="Practiced consistently, this helps you create chemistry without losing social awareness or sounding scripted.",
    ),
    "how-to-be-witty-over-text": _page(
        slug="how-to-be-witty-over-text",
        situation="she_asked_question",
        h1="Turn Boring Answers into Witty, Engaging Replies.",
        title="How To Be Witty Over Text | TryAgainText",
        meta_description="Transform basic Q&A texting into witty responses that build attraction and keep conversations engaging.",
        prefill_text="Her: What do you do for work?\nYou: Help me answer this in a witty way.",
        upload_hint="Paste her question and get witty responses that still sound authentic to you.",
        force_show_upload=False,
        related_slugs=[
            "how-to-flirt-over-text",
            "stop-boring-text-conversations",
            "what-to-say-next-over-text",
        ],
        topic="Being witty when she asks a question",
        pain_point="Literal answers can make your personality invisible, even when your intent is good.",
        framework="Use hook-detail-return: open with playful framing, provide one true detail, then bounce back with an engaging thread.",
        mistakes="Avoid over-joking, avoid long factual dumps, and avoid dodging direct questions completely.",
        tool_hook="Paste her question and generate witty response options that stay clear, confident, and easy to reply to.",
        close="Wit is a learnable pattern, and better answers usually lead to better conversation loops.",
    ),
    "stop-boring-text-conversations": _page(
        slug="stop-boring-text-conversations",
        situation="feels_like_interview",
        h1="Stop the \"Interview\" Chat: How to Make Texting Fun Again.",
        title="Stop Boring Text Conversations | TryAgainText",
        meta_description="Break out of interview-style texting and create better chemistry with statement-led conversation tactics.",
        prefill_text="You: Where are you from?\nHer: Delhi.\nYou: What do you do?\nHer: Marketing.\nYou: This feels like an interview. Rewrite it.",
        upload_hint="Upload your chat when it turns into nonstop questions so we can reframe it with personality.",
        force_show_upload=False,
        related_slugs=[
            "how-to-be-witty-over-text",
            "how-to-respond-to-dry-texts",
            "how-to-change-the-subject-over-text",
        ],
        topic="Fixing interview-style conversation",
        pain_point="Rapid-fire Q&A creates social pressure and makes both sides feel like they are filling a form.",
        framework="Switch to statement-led flow: add observations, opinions, and playful assumptions before asking the next question.",
        mistakes="Do not chain generic questions, do not ignore emotional tone, and do not keep pacing flat.",
        tool_hook="Paste the thread and generate rewrites that turn robotic Q&A into messages with personality and momentum.",
        close="Once you control rhythm, conversations feel lighter and attraction has more room to grow.",
    ),
    "how-to-reply-to-sassy-texts": _page(
        slug="how-to-reply-to-sassy-texts",
        situation="sassy_challenge",
        h1="How to Handle Sassy Texts and Win the Banter.",
        title="How To Reply To Sassy Texts | TryAgainText",
        meta_description="Reply to teasing or challenging texts with confident banter. Keep attraction high without overreacting.",
        prefill_text="Her: Oh, so you think you're pretty smart, huh?",
        upload_hint="Share the full banter screenshot so your reply stays playful instead of reactive.",
        force_show_upload=False,
        related_slugs=[
            "how-to-flirt-over-text",
            "how-to-be-witty-over-text",
            "sincere-text-messages",
        ],
        topic="Responding to sassy or challenging texts",
        pain_point="Teasing often tests composure, and defensive replies usually kill the playful energy instantly.",
        framework="Keep frame with light pushback, agree-and-amplify, or humorous roleplay while staying warm and concise.",
        mistakes="Do not justify yourself, do not escalate with bitterness, and do not mistake playful tension for rejection.",
        tool_hook="Paste her exact line and generate banter options from subtle to bold so you can answer without overreacting.",
        close="Confident banter is a major differentiator and often turns challenges into stronger attraction.",
    ),
    "sincere-text-messages": _page(
        slug="sincere-text-messages",
        situation="spark_deeper_conversation",
        h1="Ditch the Small Talk: How to Send a Sincere Text.",
        title="Sincere Text Messages | TryAgainText",
        meta_description="Send genuine texts that create deeper connection without sounding overly intense or awkward.",
        prefill_text="You: I usually joke a lot, but I want to send something sincere without sounding weird.",
        upload_hint="Paste your thread to craft a sincere message that feels real, not overly intense.",
        force_show_upload=False,
        related_slugs=[
            "how-to-flirt-over-text",
            "how-to-recover-awkward-text",
            "how-to-ask-her-out-over-text",
        ],
        topic="Sending sincere messages",
        pain_point="Many chats stay in surface banter too long, then feel awkward when someone tries to become genuine.",
        framework="Use specific sincerity: acknowledge one quality you respect, share one honest reaction, and leave room for response.",
        mistakes="Avoid emotional over-dumping, avoid generic praise, and avoid turning sincerity into pressure.",
        tool_hook="Paste your chat and generate sincere options calibrated for early-stage rapport or deeper established connection.",
        close="Used at the right moment, sincerity builds trust and gives the conversation more substance.",
    ),
    "how-to-change-the-subject-over-text": _page(
        slug="how-to-change-the-subject-over-text",
        situation="pivot_conversation",
        h1="How to Smoothly Change the Topic (Before the Chat Dies).",
        title="How To Change The Subject Over Text | TryAgainText",
        meta_description="Learn smooth topic pivots that revive stale chats and keep text conversations engaging.",
        prefill_text="We already talked this topic to death. Give me a smooth topic change that feels natural.",
        upload_hint="Share the full thread when the topic is stale and you need a natural pivot.",
        force_show_upload=False,
        related_slugs=[
            "what-to-say-next-over-text",
            "stop-boring-text-conversations",
            "how-to-respond-to-dry-texts",
        ],
        topic="Changing the topic smoothly",
        pain_point="Threads die when one subject gets overused and no one introduces a better direction.",
        framework="Use bridge-shift-hook: connect to existing context, pivot to a fresher angle, and add a response trigger.",
        mistakes="Do not hard-switch with random topics, do not repeat dead threads, and do not pivot into boring logistics too soon.",
        tool_hook="Paste the stale exchange and generate topic pivots that sound natural instead of abrupt.",
        close="Good pivots keep momentum alive and help you lead conversation flow with confidence.",
    ),
    "restart-dead-conversation": _page(
        slug="restart-dead-conversation",
        situation="reviving_old_chat",
        h1="How to Restart a Chat After Weeks of Silence.",
        title="Restart Dead Conversation | TryAgainText",
        meta_description="Revive old dating chats with context-aware re-engagement texts that feel natural instead of random.",
        prefill_text="It's been 3 weeks since we last talked. Help me restart this chat naturally.",
        upload_hint="Upload your old chat screenshot so the restart message feels connected, not random.",
        force_show_upload=False,
        related_slugs=[
            "what-to-text-after-left-on-read",
            "how-to-recover-awkward-text",
            "what-to-say-next-over-text",
        ],
        topic="Restarting an old conversation",
        pain_point="After a long gap, random re-entry messages feel disconnected and often get ignored.",
        framework="Reference one shared thread, introduce a fresh present-moment hook, and keep tone light with low pressure.",
        mistakes="Do not over-apologize, do not guilt-trip, and do not pretend the gap did not exist if context clearly matters.",
        tool_hook="Upload the previous chat and generate re-openers that match prior tone while feeling timely now.",
        close="Many dead threads are recoverable when re-entry feels contextual, calm, and easy to answer.",
    ),
    "how-to-recover-awkward-text": _page(
        slug="how-to-recover-awkward-text",
        situation="recovering_after_cringe",
        h1="Said Something Awkward? How to Save the Conversation.",
        title="How To Recover From Awkward Text | TryAgainText",
        meta_description="Recover from awkward or cringe texts using humor and composure instead of over-apologizing.",
        prefill_text="I think that last joke came off weird. Give me a recovery text that doesn't sound needy.",
        upload_hint="Upload the last few messages so your recovery line fits the exact awkward moment.",
        force_show_upload=False,
        related_slugs=[
            "what-to-text-after-left-on-read",
            "restart-dead-conversation",
            "sincere-text-messages",
        ],
        topic="Recovering after an awkward text",
        pain_point="The awkward line is rarely fatal; panic follow-ups are usually what create real damage.",
        framework="Use brief self-aware reset or a clean forward pivot based on how severe the miss actually was.",
        mistakes="Avoid over-apologizing, avoid multiple correction texts, and avoid defensive explanations.",
        tool_hook="Paste the awkward sequence and generate recovery lines that reset tone without losing confidence.",
        close="Resilience in texting matters more than perfection, and one good recovery message often fixes the moment.",
    ),
    "how-to-ask-for-number-tinder": _page(
        slug="how-to-ask-for-number-tinder",
        situation="switching_platforms",
        h1="How to Smoothly Ask for Her Number (or Instagram).",
        title="How To Ask For Number On Tinder | TryAgainText",
        meta_description="Move from dating app chat to phone number or Instagram smoothly with better timing and wording.",
        prefill_text="The vibe is good. Help me ask for her number without making it awkward.",
        upload_hint="Paste your current chat so the move-off-app ask matches the exact vibe and timing.",
        force_show_upload=False,
        related_slugs=[
            "how-to-ask-her-out-over-text",
            "best-dating-app-openers",
            "how-to-flirt-over-text",
        ],
        topic="Switching from app chat to number or Instagram",
        pain_point="Asked too early, it feels rushed; asked too late, the conversation loses momentum.",
        framework="Make the ask at peak engagement with clear, low-pressure wording and a practical reason for the switch.",
        mistakes="Avoid needy framing, avoid heavy persuasion, and avoid treating a soft no as a personal rejection.",
        tool_hook="Paste your live thread and generate direct and soft transfer asks so you can match the moment correctly.",
        close="Clean platform transitions speed up logistics and improve the path from messaging to real dates.",
    ),
    "what-to-text-after-getting-her-number": _page(
        slug="what-to-text-after-getting-her-number",
        situation="just_matched",
        h1="The First Text After Getting Her Number (No Awkward Pause).",
        title="What To Text After Getting Her Number | TryAgainText",
        meta_description="Text her smoothly after she gives you her number. Skip the creepy timing and build confidence for the next step.",
        prefill_text="We've been chatting on the app and just exchanged numbers. What should my first text be?",
        upload_hint="Upload the moment she shared her number so your first text acknowledges it naturally.",
        force_show_upload=False,
        related_slugs=[
            "best-dating-app-openers",
            "how-to-ask-her-out-over-text",
            "how-to-flirt-over-text",
        ],
        topic="Texting after getting her number",
        pain_point="The transition from app to text feels loaded; wait too long and it feels like you didn't care, text too fast and it feels pushy.",
        framework="Use warm confirmation: reference the exchange, add one personal detail, then set light expectations for next contact.",
        mistakes="Avoid waiting more than a few hours, avoid using a corny 'just making sure you saved my number' line, and avoid acting like it's a big deal.",
        tool_hook="Paste the exchange and generate first-text options that feel natural, confident, and ready to move forward.",
        close="The first text after exchange is your chance to reset momentum and show you are genuinely interested without being needy.",
    ),
    "what-to-text-after-a-date": _page(
        slug="what-to-text-after-a-date",
        situation="stuck_after_reply",
        h1="What to Text After a Date (To Keep Her Interested).",
        title="What To Text After A Date | TryAgainText",
        meta_description="Send the right follow-up text after your date so momentum builds instead of fizzling.",
        prefill_text="We had a great date tonight. How do I follow up without sounding desperate?",
        upload_hint="Describe the date vibe so the AI can craft a follow-up that matches what you actually shared.",
        force_show_upload=False,
        related_slugs=[
            "how-to-ask-her-out-over-text",
            "how-to-flirt-over-text",
            "what-to-say-next-over-text",
        ],
        topic="Following up after a date",
        pain_point="You had chemistry in person but now the text after feels either too eager or too distant.",
        framework="Use specific callbacks: mention one moment from the date, add genuine feeling, then suggest next plans or indicate you will reach out.",
        mistakes="Avoid generic 'thanks for tonight' messages, avoid waiting more than 24 hours, and avoid making it transactional.",
        tool_hook="Paste details about the date and generate follow-up texts that extend the chemistry into real momentum.",
        close="The right text after a date compounds interest and moves you from first date to serious dating.",
    ),
    "how-to-ask-for-a-second-date": _page(
        slug="how-to-ask-for-a-second-date",
        situation="ask_her_out",
        h1="How to Ask for a Second Date (The Right Way).",
        title="How To Ask For A Second Date | TryAgainText",
        meta_description="Ask for a second date confidently with specificity and clear intent instead of vague 'we should do this again' language.",
        prefill_text="The first date went well. How do I ask her out again without seeming desperate?",
        upload_hint="Paste your recent conversation to generate a second-date ask that matches your energy.",
        force_show_upload=False,
        related_slugs=[
            "how-to-ask-her-out-over-text",
            "what-to-text-after-a-date",
            "how-to-flirt-over-text",
        ],
        topic="Asking for a second date",
        pain_point="First dates often end with mutual interest but the second ask often stalls because it feels like asking again is too forward.",
        framework="Use clear specificity: suggest a specific activity, pick a realistic time, and frame it as wanting to continue something real rather than just hanging out.",
        mistakes="Avoid vague 'let's do this again' suggestions, avoid negotiating your confidence before she responds, and avoid suggesting something too formal.",
        tool_hook="Paste your first-date summary and generate second-date asks with specific plans and clear intent.",
        close="Confident second-date asks convert more first dates into actual relationships.",
    ),
    "what-to-text-a-girl-you-ghosted": _page(
        slug="what-to-text-a-girl-you-ghosted",
        situation="stuck_after_reply",
        h1="How to Text a Girl You Ghosted (And Actually Get a Response).",
        title="What To Text A Girl You Ghosted | TryAgainText",
        meta_description="Re-engage someone you ghosted with honesty and authenticity instead of pretending it didn't happen.",
        prefill_text="I ghosted her a few months ago and want to reach out. How do I do this without seeming creepy?",
        upload_hint="Describe your history with her so the AI can craft something genuine.",
        force_show_upload=False,
        related_slugs=[
            "how-to-recover-awkward-text",
            "restart-dead-conversation",
            "what-to-text-after-left-on-read",
        ],
        topic="Re-engaging after ghosting",
        pain_point="You ghosted but now realize you actually miss her; the guilt makes it hard to reach out authentically.",
        framework="Use honest acknowledgment: own the ghost without over-apologizing, explain what changed, and leave space for her to decide if she is interested.",
        mistakes="Avoid pretending nothing happened, avoid heavy apologies that make it about you, and avoid asking for instant forgiveness.",
        tool_hook="Paste your situation and generate re-engagement texts that are honest, take accountability, and give her agency.",
        close="Sometimes ghosting teaches you something real, and reaching out authentically can revive conversations that mattered.",
    ),
    "how-to-keep-a-conversation-going": _page(
        slug="how-to-keep-a-conversation-going",
        situation="stuck_after_reply",
        h1="How to Keep a Text Conversation Going (Never Run Out of Things to Say).",
        title="How To Keep A Conversation Going | TryAgainText",
        meta_description="Stop letting conversations fizzle with better questions, deeper engagement, and genuine follow-up.",
        prefill_text="The chat started great but now it feels like we are just trading basic messages. How do I deepen it?",
        upload_hint="Upload the current thread so the AI can identify where engagement is dropping and suggest resets.",
        force_show_upload=False,
        related_slugs=[
            "stop-boring-text-conversations",
            "what-to-say-next-over-text",
            "how-to-flirt-over-text",
        ],
        topic="Maintaining conversation momentum",
        pain_point="Most conversations stall not because of bad attraction but because messages become generic and predictable.",
        framework="Use statement-led responses with follow-up hooks: share something real, ask something that invites deeper answers, repeat.",
        mistakes="Avoid interview-style questions, avoid mirroring her low energy, and avoid filling silence with filler text.",
        tool_hook="Paste your thread and generate conversation resets that add texture and create natural follow-up hooks.",
        close="The ability to keep conversations alive is a core skill that directly improves your dating outcomes.",
    ),
    "what-to-text-when-she-cancels": _page(
        slug="what-to-text-when-she-cancels",
        situation="stuck_after_reply",
        h1="What to Text When She Cancels Plans (Without Looking Weak).",
        title="What To Text When She Cancels Plans | TryAgainText",
        meta_description="Respond to cancelled plans with confidence that builds respect instead of resentment.",
        prefill_text="She just cancelled our date. How do I respond so I don't look bitter or desperate?",
        upload_hint="Paste her cancellation message so your response matches her tone and reason.",
        force_show_upload=False,
        related_slugs=[
            "what-to-text-after-left-on-read",
            "restart-dead-conversation",
            "how-to-recover-awkward-text",
        ],
        topic="Responding to cancelled plans",
        pain_point="Cancelled plans create anxiety; most men respond either too nice (desperate) or too hostile (angry).",
        framework="Use casual reset: acknowledge without drama, leave the door open, and stay emotionally steady.",
        mistakes="Avoid guilt-tripping her, avoid pretending it does not matter, and avoid passive-aggressive humor.",
        tool_hook="Paste her cancellation and generate responses that are confident, mature, and keep options open.",
        close="How you handle cancellations shows her whether you are secure or needy, and secure always wins.",
    ),
    "how-to-confess-feelings-over-text": _page(
        slug="how-to-confess-feelings-over-text",
        situation="sincere",
        h1="How to Confess Feelings Over Text (And Actually Get a Real Response).",
        title="How To Confess Feelings Over Text | TryAgainText",
        meta_description="Express genuine feelings over text without being creepy, needy, or over the top.",
        prefill_text="I want to tell her I have real feelings for her. How do I say it without messing things up?",
        upload_hint="Describe your situation so the AI can calibrate honesty with timing.",
        force_show_upload=False,
        related_slugs=[
            "sincere-text-messages",
            "how-to-flirt-over-text",
            "how-to-ask-her-out-over-text",
        ],
        topic="Confessing feelings over text",
        pain_point="Vulnerability feels risky, so most men either hide feelings completely or dump everything at once.",
        framework="Use clear, specific honesty: state what you feel without expectations, reference specific moments, and give space for her response.",
        mistakes="Avoid soul-bearing novels, avoid confessing via late-night text, and avoid making it her job to manage your emotions.",
        tool_hook="Paste your situation and generate confessions that are genuine, grounded, and leave room for her choice.",
        close="The right confession of feelings, timed well, often deepens connections instead of ruining them.",
    ),
    "how-to-text-your-crush": _page(
        slug="how-to-text-your-crush",
        situation="just_matched",
        h1="How to Text Your Crush (When You are Nervous).",
        title="How To Text Your Crush | TryAgainText",
        meta_description="Reach out to your crush with confidence and authenticity instead of overthinking every word.",
        prefill_text="I've been wanting to text my crush but I'm nervous. What should I say?",
        upload_hint="Describe who she is so the AI can craft something that feels personal.",
        force_show_upload=False,
        related_slugs=[
            "best-dating-app-openers",
            "how-to-flirt-over-text",
            "how-to-ask-her-out-over-text",
        ],
        topic="Texting your crush",
        pain_point="Crushing creates overthinking; you either text too much trying to impress or wait forever trying to seem cool.",
        framework="Use genuine interest: reference something real about her, suggest something specific, and show up as yourself without trying.",
        mistakes="Avoid huge gaps between texts, avoid overly formal language, and avoid pretending to be someone you are not.",
        tool_hook="Paste your situation and generate opener texts that feel natural, interested, and actually like you.",
        close="Most crushes respond better to genuine interest than to perfect game, so just show up as yourself.",
    ),
    "what-to-text-after-first-date": _page(
        slug="what-to-text-after-first-date",
        situation="stuck_after_reply",
        h1="What to Say After a First Date (So She Wants a Second One).",
        title="What To Text After First Date | TryAgainText",
        meta_description="Follow up after your first date with a message that extends the chemistry and moves toward a second date.",
        prefill_text="First date was great. How do I keep the momentum going without seeming thirsty?",
        upload_hint="Describe how the date went so the AI can match the right energy.",
        force_show_upload=False,
        related_slugs=[
            "what-to-text-after-a-date",
            "how-to-ask-for-a-second-date",
            "how-to-flirt-over-text",
        ],
        topic="Following up after a first date",
        pain_point="The first date felt good but follow-up text often kills momentum because timing, tone, or specificity is off.",
        framework="Use warm reference: remind her of a specific moment, express genuine interest in her, and suggest something concrete for next time.",
        mistakes="Avoid waiting more than 24 hours, avoid generic flattery, and avoid acting like second dates are guaranteed.",
        tool_hook="Paste date details and generate follow-ups that lock in genuine interest and move toward second date.",
        close="The right text after a first date builds real momentum instead of letting chemistry fade.",
    ),
    "how-to-double-text": _page(
        slug="how-to-double-text",
        situation="stuck_after_reply",
        h1="Is It Okay to Double Text? (Yes, But Here's How).",
        title="How To Double Text | TryAgainText",
        meta_description="Send a second text after no response with confidence instead of shame, using timing and substance that justify it.",
        prefill_text="I texted her yesterday and she hasn't responded. Should I send another message?",
        upload_hint="Paste your original text so the AI knows what she is responding to.",
        force_show_upload=False,
        related_slugs=[
            "what-to-text-after-left-on-read",
            "restart-dead-conversation",
            "how-to-keep-a-conversation-going",
        ],
        topic="Double texting",
        pain_point="Single texting creates anxiety; double texting feels desperate unless it is done right.",
        framework="Use the double text as a reset, not a chase: new topic, different energy, or valuable context that reframes.",
        mistakes="Avoid sending the same type of message twice, avoid guilt-filled follow-ups, and avoid explaining why you are texting again.",
        tool_hook="Paste your original message and generate double texts that feel fresh and justified instead of needy.",
        close="Strategic double texting often revives conversations that simple waiting would have lost.",
    ),
}

SIDEBAR_LABELS = {
    "what-to-say-next-over-text": "What To Say Next",
    "best-dating-app-openers": "Best Openers",
    "how-to-respond-to-dry-texts": "Dry Text Replies",
    "what-to-text-after-left-on-read": "Left on Read",
    "how-to-ask-her-out-over-text": "Asking Her Out",
    "how-to-flirt-over-text": "Flirty Texting",
    "how-to-be-witty-over-text": "Witty Replies",
    "stop-boring-text-conversations": "Stop Interview Chat",
    "how-to-reply-to-sassy-texts": "Sassy Banter",
    "sincere-text-messages": "Sincere Texts",
    "how-to-change-the-subject-over-text": "Change Topic",
    "restart-dead-conversation": "Restart Dead Chat",
    "how-to-recover-awkward-text": "Recover Awkward Text",
    "how-to-ask-for-number-tinder": "Ask for Number",
    "what-to-text-after-getting-her-number": "After She Gives Number",
    "what-to-text-after-a-date": "After The Date",
    "how-to-ask-for-a-second-date": "Ask For Second Date",
    "what-to-text-a-girl-you-ghosted": "Re-engage After Ghost",
    "how-to-keep-a-conversation-going": "Keep Chat Alive",
    "what-to-text-when-she-cancels": "When She Cancels",
    "how-to-confess-feelings-over-text": "Confess Feelings",
    "how-to-text-your-crush": "Text Your Crush",
    "what-to-text-after-first-date": "After First Date",
    "how-to-double-text": "Double Texting",
}


SCREENSHOT_TIPS = {
    "what-to-say-next-over-text": "Upload a screenshot of the last few messages to anchor the AI in the exact thread before you send your next line.",
    "best-dating-app-openers": "Upload her profile screenshot so the opener references real details instead of generic lines.",
    "how-to-respond-to-dry-texts": "Upload the dry-text moment so the AI can calibrate a playful re-engagement without sounding needy.",
    "what-to-text-after-left-on-read": "Upload the last exchange and timing gap so your follow-up feels casual, not reactive.",
    "how-to-ask-her-out-over-text": "Upload your current chat to choose a date invite that matches the momentum and tone already built.",
    "how-to-flirt-over-text": "Upload your chat so the AI can raise flirt energy while keeping your style consistent.",
    "how-to-be-witty-over-text": "Upload the exact question thread so your witty answer still sounds natural and relevant.",
    "stop-boring-text-conversations": "Upload the interview-style exchange so the AI can rewrite it into statement-led, engaging flow.",
    "how-to-reply-to-sassy-texts": "Upload the banter context so your response stays playful and confident instead of defensive.",
    "sincere-text-messages": "Upload your recent messages to craft a sincere line that feels grounded and well-timed.",
    "how-to-change-the-subject-over-text": "Upload the stale thread so the AI can generate a smooth topic pivot that feels natural.",
    "restart-dead-conversation": "Upload your old chat screenshot above so the AI can revive the thread with context-aware re-openers.",
    "how-to-recover-awkward-text": "Upload the awkward moment so the recovery text resets tone without over-apologizing.",
    "how-to-ask-for-number-tinder": "Upload your live thread so the number/Instagram ask lands at the right moment.",
    "what-to-text-after-getting-her-number": "Upload the message exchange where she gave you her number so the follow-up feels natural.",
    "what-to-text-after-a-date": "Upload details about the date so the follow-up text hits the right tone and specificity.",
    "how-to-ask-for-a-second-date": "Upload your current chat so the second-date ask matches the momentum you have built.",
    "what-to-text-a-girl-you-ghosted": "Upload your old thread so the re-engagement feels contextual and genuine.",
    "how-to-keep-a-conversation-going": "Upload your current exchange so the AI can identify where it is dropping and suggest resets.",
    "what-to-text-when-she-cancels": "Upload her cancellation message so your response matches her tone and situation.",
    "how-to-confess-feelings-over-text": "Upload your recent messages so the confession feels grounded and perfectly timed.",
    "how-to-text-your-crush": "Upload any previous conversations so the opener feels personal to your actual dynamic.",
    "what-to-text-after-first-date": "Upload details about the first date so your follow-up extends the chemistry.",
    "how-to-double-text": "Upload your original message so the double text feels like a reset, not a chase.",
}


for _slug, _page_data in SITUATION_PAGES.items():
    if _slug in SIDEBAR_LABELS:
        _page_data["sidebar_label"] = SIDEBAR_LABELS[_slug]
    if _slug in SCREENSHOT_TIPS:
        _page_data["screenshot_tip"] = SCREENSHOT_TIPS[_slug]


SITUATION_PAGE_ORDER = [
    "what-to-say-next-over-text",
    "best-dating-app-openers",
    "how-to-respond-to-dry-texts",
    "what-to-text-after-left-on-read",
    "how-to-ask-her-out-over-text",
    "how-to-flirt-over-text",
    "how-to-be-witty-over-text",
    "stop-boring-text-conversations",
    "how-to-reply-to-sassy-texts",
    "sincere-text-messages",
    "how-to-change-the-subject-over-text",
    "restart-dead-conversation",
    "how-to-recover-awkward-text",
    "how-to-ask-for-number-tinder",
    "what-to-text-after-getting-her-number",
    "what-to-text-after-a-date",
    "how-to-ask-for-a-second-date",
    "what-to-text-a-girl-you-ghosted",
    "how-to-keep-a-conversation-going",
    "what-to-text-when-she-cancels",
    "how-to-confess-feelings-over-text",
    "how-to-text-your-crush",
    "what-to-text-after-first-date",
    "how-to-double-text",
]


def get_situation_page(slug):
    if not slug:
        return None
    return SITUATION_PAGES.get(str(slug).strip())


def list_situation_pages():
    return [SITUATION_PAGES[slug] for slug in SITUATION_PAGE_ORDER if slug in SITUATION_PAGES]


def list_related_pages(page):
    if not page:
        return []

    related = []
    for slug in page.get("related_slugs", []):
        match = SITUATION_PAGES.get(slug)
        if not match:
            continue
        related.append(match)
    return related

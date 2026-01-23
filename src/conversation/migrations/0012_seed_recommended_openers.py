from django.db import migrations


def seed_recommended_openers(apps, schema_editor):
    RecommendedOpener = apps.get_model("conversation", "RecommendedOpener")

    openers = [
        (
            "How does this work? are we getting married now?",
            "Its a fun, silly opener that works because people find it adorable.",
        ),
        (
            "Can I be honest?",
            "It makes people curious about what you want to be honest about. "
            "You can follow it with: You're exactly my type.",
        ),
        (
            "Hey <name>, you know whats interesting about your pictures?",
            "Everyone wants to know what makes them interesting.",
        ),
        (
            "I like you",
            "Its so simple and direct that it catches people off guard in a noisy dating world.",
        ),
        (
            "Hahah oh shit! Not sure if you remember",
            "This is straight up clickbait. After she replies, you can say: "
            "Never mind. I thought you were the girl who had a crush on me in high school.",
        ),
        (
            "Im the one, you can delete the app now.",
            "This one is way too cocky and confident.",
        ),
        (
            "Um, hi. I feel you appear attractive and consequently I would like to explore the possibility "
            "of enhancing your life by means of exposure to my awesomeness. K, thanks bye.",
            "This uses a mix of being unique, casual, awkward, and smart with vocabulary.",
        ),
        (
            "Hey, [name]. So is this the part where we fall for each other instantly, tie the knot too soon, "
            "get divorced and then argue over who gets custody of the dog?",
            "This is a roleplay opener where you create and shatter a world together.",
        ),
        (
            "youre adorable...fingers crossed you are not crazy",
            "This is a push-pull opener and implies you get a lot of dates.",
        ),
        (
            "Should I be jealous?",
            "Makes people curious about what they have that can make others jealous.",
        ),
        (
            "Love that print on your top! Reminds me of the bedsheets I had as a child <3",
            "A push-pull opener: complimenting her top while teasing that it looks like a bedsheet. "
            "High risk, high reward. Use when your match is very attractive.",
        ),
        (
            "This is what I notice when I see your pictures. You have this kind of friendly vibe about you, "
            "you seem quite open. On the other hand, I think you can be quite introverted and be a bit shy as well. "
            "In one of your photos, I also noticed something funny",
            "This involves a bit of cold reading. The statement applies to almost anyone, "
            "so they might think you read their soul.",
        ),
        (
            "Hey, trouble.",
            "Calling someone trouble is always a little bit flirty.",
        ),
        (
            "You seem like my type :)",
            "Its so simple and direct that it catches people off guard in a noisy dating world.",
        ),
        (
            "Hey, future lover",
            "Its short and has a flirty undertone to it.",
        ),
        (
            "Im at the food section in a store. Want me to pick you up something?",
            "Funny and spontaneous, it feels casual and playful.",
        ),
        (
            "So sweet that you got me flowers for our matchiversary!",
            "Swap flowers with anything from her profile (champagne, books, tickets, etc.). "
            "It works because its tied to her actual profile and not a scripted opener.",
        ),
        (
            "I was so stoked to get to know you, but then my horoscope said that a girl in a blue dress would get me into trouble",
            "Change 'blue dress' to anything she is wearing or doing. It works because its tied to her actual profile.",
        ),
    ]

    for index, (text, why) in enumerate(openers, start=1):
        RecommendedOpener.objects.create(
            text=text,
            why_it_works=why,
            sort_order=index,
            is_active=True,
        )


def unseed_recommended_openers(apps, schema_editor):
    RecommendedOpener = apps.get_model("conversation", "RecommendedOpener")
    RecommendedOpener.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("conversation", "0011_recommended_opener"),
    ]

    operations = [
        migrations.RunPython(seed_recommended_openers, unseed_recommended_openers),
    ]

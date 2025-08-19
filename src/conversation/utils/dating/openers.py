import random

type1 = [
    "you're adorable...fingers crossed you are not crazy 🤞",
    "You look normal… which is suspicious ",
    "You look like someone who’d be fun… and slightly exhausting",
    "You look like fun… exhausting, but fun ;)"
    "You seem normal… but then again, so did my ex",
]

type2 = [
    "Um, hi. I feel you appear attractive and consequently I would like to explore the possibility of enhancing your life by means of exposure to my awesomeness. K, thanks bye.",
    "Adorable profile pic… but let’s be honest, how much of it is just filters and witchcraft?",
    "You seem normal… but that’s usually how the best Netflix true crime documentaries start 😏",
    "So we matched… the algorithm clearly has a twisted sense of humor",
    "Cute pic. Blink twice if you bribed the lighting to behave 👀"
]

type3 = [
    "Hey, [name], cool that we matched. So is this the part where we start a whirlwind romance and get married and divorced way too fast ;)",
    "Hey, [name], cool that we matched. Are we doing the whirlwind romance, the impulsive wedding, and the bitter divorce all in one season?",
    "Hey, [name], cool that we matched. So is this the part where we fall for each other instantly, tie the knot too soon, and then argue over who gets custody of the dog?"
    "Hey, [name], cool that we matched. We could be the couple everyone envies… until the divorce lawyers get all our money"
    "Hey, [name], cool that we matched. Instant chemistry, dreamy vows, catastrophic divorce… at least the wedding photos will slap."
]

def get_openers():
    opener1 = random.choice(type1)
    opener2 = random.choice(type2)
    opener3 = random.choice(type3)
    
    # Send the opener to the user
    return opener1, opener2, opener3

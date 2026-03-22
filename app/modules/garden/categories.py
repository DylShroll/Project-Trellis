# Interest categories for garden-entry details.
# Keys are category names; values are ordered lists of suggested detail labels.

INTEREST_CATEGORIES: dict[str, list[str]] = {
    "Music": [
        "Favourite artists",
        "Favourite songs",
        "Favourite genres",
        "Favourite albums",
        "Concerts attended",
        "Dream concerts",
        "Instruments they play",
        "Music they make",
    ],
    "Movies": [
        "Favourite films",
        "Favourite directors",
        "Favourite genres",
        "Favourite actors",
        "Themes they love",
        "All-time favourite film",
        "Films they quote",
    ],
    "TV & Streaming": [
        "Favourite shows",
        "Currently watching",
        "Favourite genres",
        "Content creators they follow",
        "Podcasts they love",
        "Guilty pleasures",
        "Rewatched shows",
    ],
    "Books": [
        "Favourite authors",
        "Favourite genres",
        "Currently reading",
        "Favourite titles",
        "Favourite series",
        "Book clubs",
        "Books that changed them",
    ],
    "Food & Drink": [
        "Favourite cuisines",
        "Favourite restaurants",
        "Coffee order",
        "Drink of choice",
        "Comfort food",
        "Dietary preferences",
        "Allergies or restrictions",
        "They love to cook",
    ],
    "Travel": [
        "Places visited",
        "Dream destinations",
        "Favourite city",
        "Travel style",
        "Languages spoken",
        "Places they lived",
        "Next trip planned",
    ],
    "Sports & Fitness": [
        "Favourite sports",
        "Favourite teams",
        "Activities they enjoy",
        "Fitness goals",
        "Outdoor pursuits",
        "Sports they played growing up",
    ],
    "Work & Career": [
        "Industry",
        "Current role",
        "Career goals",
        "Dream job",
        "Side projects",
        "Skills they are proud of",
        "Work style",
        "How they found their path",
    ],
    "Hobbies": [
        "Creative pursuits",
        "Collections",
        "Video games they play",
        "Board games they love",
        "Crafts",
        "DIY projects",
        "Other hobbies",
    ],
    "Personal": [
        "Values",
        "Life goals",
        "Love languages",
        "What energises them",
        "What drains them",
        "Myers-Briggs or personality type",
        "Quirks",
        "Pet peeves",
        "How they recharge",
    ],
    "General": [
        "Birthday",
        "Hometown",
        "Current city",
        "Pets",
        "Fun fact",
        "How we met",
        "Custom",
    ],
}

# Display order for category sections
CATEGORY_ORDER: list[str] = list(INTEREST_CATEGORIES.keys())

# Suggested milestone titles per relationship type.
# Each entry is (title, is_recurring).  Shown as one-click helpers in the milestone form.
MILESTONE_SUGGESTIONS: dict[str, list[tuple[str, bool]]] = {
    "partner": [
        ("Birthday", True),
        ("Anniversary", True),
        ("First date", False),
        ("Moved in together", False),
        ("Engagement", False),
        ("Wedding", False),
    ],
    "family": [
        ("Birthday", True),
        ("Wedding anniversary", True),
        ("Graduation", False),
        ("New baby", False),
        ("Holiday tradition", True),
    ],
    "close_friend": [
        ("Birthday", True),
        ("Friendiversary", True),
        ("Graduation", False),
        ("Promotion", False),
        ("Moving day", False),
    ],
    "friend": [
        ("Birthday", True),
        ("Meetup anniversary", True),
    ],
    "acquaintance": [
        ("Birthday", True),
        ("First proper conversation", False),
    ],
    "childhood_friend": [
        ("Birthday", True),
        ("Friendiversary", True),
        ("Reunion", False),
        ("School graduation", False),
    ],
    "online_friend": [
        ("Birthday", True),
        ("First message anniversary", True),
        ("First time meeting in person", False),
    ],
    "neighbour": [
        ("Birthday", True),
        ("Move-in date", False),
        ("Annual street event", True),
    ],
    "colleague": [
        ("Work anniversary", True),
        ("Birthday", True),
        ("Project launch", False),
        ("Promotion", False),
    ],
    "collaborator": [
        ("Project start", False),
        ("Project launch", False),
        ("Birthday", True),
        ("Collaboration anniversary", True),
    ],
    "mentor": [
        ("First meeting anniversary", True),
        ("Career milestone", False),
        ("Birthday", True),
    ],
    "mentee": [
        ("First meeting anniversary", True),
        ("Their career milestone", False),
        ("Birthday", True),
        ("Graduation", False),
    ],
    "community": [
        ("Annual event", True),
        ("First meetup", False),
        ("Birthday", True),
    ],
    "ex_partner": [
        ("Birthday", True),
        ("First met", False),
    ],
    "inspiration": [
        ("Birthday", True),
        ("Discovered their work", False),
        ("Saw them live / in person", False),
    ],
    "custom": [
        ("Birthday", True),
        ("Anniversary", True),
    ],
}


# Single-char icons per category (text-safe, no emoji dependency)
CATEGORY_ICONS: dict[str, str] = {
    "Music": "♪",
    "Movies": "◈",
    "TV & Streaming": "▷",
    "Books": "☷",
    "Food & Drink": "◉",
    "Travel": "◎",
    "Sports & Fitness": "▣",
    "Work & Career": "▤",
    "Hobbies": "✦",
    "Personal": "♡",
    "General": "·",
}

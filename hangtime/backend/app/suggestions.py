"""Curated activity ideas, lightly localized by the group's city.

This is a starter dataset; the roadmap swaps it for a places API (Google Places /
Yelp Fusion) keyed off the group's location.
"""
import random

GENERIC = [
    {"emoji": "🍜", "title": "Ramen night", "blurb": "Slurp-off at the best ramen spot nearby", "vibe": "food", "slot": "evening", "cost": "$$"},
    {"emoji": "🌮", "title": "Taco crawl", "blurb": "Hit 3 taco spots, rank them, crown a winner", "vibe": "food", "slot": "evening", "cost": "$"},
    {"emoji": "🎳", "title": "Bowling + arcade", "blurb": "Loser buys the next round of games", "vibe": "games", "slot": "evening", "cost": "$$"},
    {"emoji": "🥾", "title": "Sunrise-ish hike", "blurb": "Easy trail, big views, coffee after", "vibe": "outdoors", "slot": "morning", "cost": "free"},
    {"emoji": "🧺", "title": "Park picnic", "blurb": "Everyone brings one snack, no duplicates allowed", "vibe": "outdoors", "slot": "afternoon", "cost": "$"},
    {"emoji": "🎬", "title": "Movie night in", "blurb": "One veto per person, blankets mandatory", "vibe": "chill", "slot": "evening", "cost": "free"},
    {"emoji": "🃏", "title": "Game night", "blurb": "Board games, cards, and unearned trash talk", "vibe": "games", "slot": "evening", "cost": "free"},
    {"emoji": "☕", "title": "Coffee catch-up", "blurb": "New café, one hour, phones down", "vibe": "chill", "slot": "morning", "cost": "$"},
    {"emoji": "🍳", "title": "Brunch, obviously", "blurb": "The classic. Someone books, everyone shows", "vibe": "food", "slot": "morning", "cost": "$$"},
    {"emoji": "🎤", "title": "Karaoke", "blurb": "Private room, zero judgment, all bangers", "vibe": "party", "slot": "evening", "cost": "$$"},
    {"emoji": "🏓", "title": "Pickleball run", "blurb": "Round robin, winners stay on", "vibe": "active", "slot": "afternoon", "cost": "$"},
    {"emoji": "🍦", "title": "Dessert walk", "blurb": "Ice cream + a long walk with the group chat IRL", "vibe": "chill", "slot": "evening", "cost": "$"},
    {"emoji": "🧗", "title": "Climbing gym", "blurb": "Day passes + belay-certified bragging rights", "vibe": "active", "slot": "afternoon", "cost": "$$"},
    {"emoji": "🍷", "title": "Wine & paint", "blurb": "Everyone paints the same thing. Results vary", "vibe": "party", "slot": "evening", "cost": "$$"},
    {"emoji": "⚽", "title": "Pickup game", "blurb": "Soccer/basketball at the local courts", "vibe": "active", "slot": "afternoon", "cost": "free"},
    {"emoji": "🔥", "title": "Backyard hang", "blurb": "Fire pit, s'mores, unhinged storytelling", "vibe": "chill", "slot": "evening", "cost": "$"},
]

CITY_EXTRAS = {
    "los angeles": [
        {"emoji": "🌅", "title": "Sunset at El Matador", "blurb": "Malibu beach hour + In-N-Out on the way home", "vibe": "outdoors", "slot": "evening", "cost": "free"},
        {"emoji": "🌭", "title": "Smorgasburg Sunday", "blurb": "ROW DTLA food-stall roulette", "vibe": "food", "slot": "afternoon", "cost": "$$"},
        {"emoji": "🥙", "title": "K-town BBQ", "blurb": "AYCE Korean BBQ — bring your appetite", "vibe": "food", "slot": "evening", "cost": "$$"},
        {"emoji": "🎢", "title": "Santa Monica Pier", "blurb": "Rides, skee-ball, boardwalk snacks", "vibe": "party", "slot": "afternoon", "cost": "$$"},
    ],
    "san francisco": [
        {"emoji": "🌁", "title": "Lands End walk", "blurb": "Coastal trail + Sutro Baths photo op", "vibe": "outdoors", "slot": "morning", "cost": "free"},
        {"emoji": "🫓", "title": "Mission burrito battle", "blurb": "La Taqueria vs. El Farolito. Settle it", "vibe": "food", "slot": "evening", "cost": "$"},
        {"emoji": "⛵", "title": "Ferry to Sausalito", "blurb": "Boat, bikes, and a long lunch", "vibe": "outdoors", "slot": "afternoon", "cost": "$$"},
    ],
    "new york": [
        {"emoji": "🍕", "title": "Dollar-slice tour", "blurb": "Five slices, five boroughs* (*two boroughs)", "vibe": "food", "slot": "evening", "cost": "$"},
        {"emoji": "🌉", "title": "Brooklyn Bridge walk", "blurb": "Sunset crossing + DUMBO ice cream", "vibe": "outdoors", "slot": "evening", "cost": "free"},
        {"emoji": "🎭", "title": "Comedy cellar night", "blurb": "Late show + late-night diner debrief", "vibe": "party", "slot": "evening", "cost": "$$"},
    ],
}


def suggest(city: str, slot: str | None = None, count: int = 6, seed: int | None = None) -> list[dict]:
    pool = list(GENERIC)
    key = (city or "").strip().lower()
    for name, extras in CITY_EXTRAS.items():
        if name in key:
            pool = extras + pool
            break
    if slot:
        preferred = [p for p in pool if p["slot"] == slot]
        rest = [p for p in pool if p["slot"] != slot]
        pool = preferred + rest
    rng = random.Random(seed)
    head = pool[: max(count, 8)]
    rng.shuffle(head)
    return head[:count]

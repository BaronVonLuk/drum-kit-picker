from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class DrumKit:
    id: str
    name: str
    kit_type: str  # acoustic | electronic
    price_min: int
    price_max: int
    space: str     # apartment | house | studio
    genres: List[str]
    skill: str     # beginner | intermediate | advanced
    notes: str


KITS: List[DrumKit] = [
    DrumKit(
        id="roland-td-17kvx2",
        name="Roland TD-17KVX2",
        kit_type="electronic",
        price_min=1700,
        price_max=2300,
        space="apartment",
        genres=["rock", "metal", "pop", "funk", "jazz"],
        skill="intermediate",
        notes="Solid pads, good module, quiet enough for most apartments with a mat."
    ),
    DrumKit(
        id="alesis-nitro-max",
        name="Alesis Nitro Max",
        kit_type="electronic",
        price_min=300,
        price_max=450,
        space="apartment",
        genres=["rock", "pop", "hiphop", "edm"],
        skill="beginner",
        notes="Budget-friendly starter kit, expect compromises in feel/durability."
    ),
    DrumKit(
        id="yamaha-dtx6k2-x",
        name="Yamaha DTX6K2-X",
        kit_type="electronic",
        price_min=900,
        price_max=1300,
        space="apartment",
        genres=["rock", "pop", "funk", "jazz"],
        skill="intermediate",
        notes="Strong sounds and training features; pad feel is preference-dependent."
    ),
    DrumKit(
        id="yamaha-stage-custom-birch",
        name="Yamaha Stage Custom Birch",
        kit_type="acoustic",
        price_min=750,
        price_max=1100,
        space="house",
        genres=["rock", "pop", "funk", "jazz", "country"],
        skill="beginner",
        notes="Reliable entry acoustic kit; cymbals/hardware may be extra depending on bundle."
    ),
    DrumKit(
        id="tama-imperialstar",
        name="Tama Imperialstar",
        kit_type="acoustic",
        price_min=700,
        price_max=1100,
        space="house",
        genres=["rock", "metal", "pop"],
        skill="beginner",
        notes="Often sold as complete packages; good value, not subtle."
    ),
    DrumKit(
        id="gretsch-catalina-club",
        name="Gretsch Catalina Club",
        kit_type="acoustic",
        price_min=800,
        price_max=1200,
        space="house",
        genres=["jazz", "funk", "pop", "rock"],
        skill="intermediate",
        notes="Smaller shells, easier in tight spaces, still loud like any acoustic kit."
    ),
]


def score_kit(kit: DrumKit, prefs: Dict[str, Any]) -> int:
    score = 0

    # Type
    if prefs["kit_type"] == kit.kit_type:
        score += 30
    else:
        score -= 10

    # Budget overlap (hard-ish constraint)
    budget = prefs["budget"]
    if kit.price_min <= budget <= kit.price_max:
        score += 25
    elif budget < kit.price_min:
        score -= 20
    else:
        score -= 5

    # Space / noise reality
    if prefs["space"] == kit.space:
        score += 20
    elif prefs["space"] == "apartment" and kit.kit_type == "acoustic":
        score -= 40  # be honest: acoustic + apartment is a conflict
    else:
        score += 5

    # Skill match
    if prefs["skill"] == kit.skill:
        score += 10
    elif prefs["skill"] == "beginner" and kit.skill != "advanced":
        score += 6
    else:
        score += 0

    # Genre match
    genre = prefs["genre"]
    if genre in kit.genres:
        score += 15
    else:
        score += 2

    # Practice priority (quiet)
    if prefs["quiet_priority"] and kit.kit_type == "electronic":
        score += 10

    return score


def pick_top_kits(prefs: Dict[str, Any], k: int = 3) -> List[DrumKit]:
    ranked = sorted(KITS, key=lambda kit: score_kit(kit, prefs), reverse=True)
    return ranked[:k]

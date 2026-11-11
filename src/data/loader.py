"""Load and validate character/ability data. Stat values are prototype
starting points; tune them after the engine works."""
import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).with_name("characters.json")
VALID_TARGETS = {"enemy", "self"}


@dataclass(frozen=True)
class Ability:
    name: str
    damage: int
    chakra_cost: int
    cooldown: int
    effect: str | None
    target: str


@dataclass
class Character:
    name: str
    max_hp: int
    max_chakra: int
    attack: int
    defense: int
    speed: int
    abilities: list[Ability]
    hp: int = field(init=False)
    chakra: int = field(init=False)
    cooldowns: dict[str, int] = field(init=False)

    def __post_init__(self):
        self.hp = self.max_hp
        self.chakra = self.max_chakra
        self.cooldowns = {a.name: 0 for a in self.abilities}


def _validate_ability(name: str, d: dict) -> Ability:
    for key in ("damage", "chakra_cost", "cooldown"):
        if not isinstance(d.get(key), int) or d[key] < 0:
            raise ValueError(f"Ability '{name}': '{key}' must be a non-negative int")
    if d.get("target") not in VALID_TARGETS:
        raise ValueError(f"Ability '{name}': target must be one of {VALID_TARGETS}")
    return Ability(name, d["damage"], d["chakra_cost"], d["cooldown"],
                   d.get("effect"), d["target"])


def load_characters(path: Path = DATA_FILE) -> dict[str, Character]:
    """Return fresh Character objects keyed by name (new copy on every call,
    so battles never share mutable state)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    abilities = {n: _validate_ability(n, d) for n, d in raw["abilities"].items()}

    chars = {}
    for c in raw["characters"]:
        missing = [a for a in c["abilities"] if a not in abilities]
        if missing:
            raise ValueError(f"{c['name']}: unknown abilities {missing}")
        if c["max_hp"] <= 0 or c["max_chakra"] < 0:
            raise ValueError(f"{c['name']}: invalid max_hp/max_chakra")
        chars[c["name"]] = Character(
            name=c["name"], max_hp=c["max_hp"], max_chakra=c["max_chakra"],
            attack=c["attack"], defense=c["defense"], speed=c["speed"],
            abilities=[abilities[a] for a in c["abilities"]],
        )
    return chars


if __name__ == "__main__":
    for ch in load_characters().values():
        print(ch.name, ch.hp, ch.chakra, [a.name for a in ch.abilities])

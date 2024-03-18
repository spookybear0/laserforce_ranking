from dataclasses import dataclass
from typing import Optional
from enum import Enum, IntEnum


@dataclass
class _TeamDefinition:
    """Descriptor for a team.

    When converted to a string, it is shown as the lower-case color name so Tortoise can use it as an enum value for
    its schema."""
    color: str
    element: str

    def __eq__(self, color: str) -> bool:
        return self.color == color

    def __len__(self):
        # Tortoise uses the length of the enum value.
        return len(self.color)

    def __str__(self):
        return self.color

    def __hash__(self):
        return self.color.__hash__()


class Team(Enum):
    RED = _TeamDefinition(color="red", element="Fire")
    GREEN = _TeamDefinition(color="green", element="Earth")
    BLUE = _TeamDefinition(color="blue", element="Ice")

    def __call__(cls, value, *args, **kw):
        # Tortoise looks up values by the lower-case color name.
        if type(value) is str:
            for teams in cls:
                if teams.value.color == value:
                    return super().__call__(teams, *args, **kw)
        return super().__call__(value, *args, **kw)

    def standardize(self) -> str:
        return self.value.color.capitalize()

    @property
    def element(self) -> str:
        return self.value.element


# Mapping of opposing teams in SM5 games.
SM5_ENEMY_TEAM = {
    Team.GREEN: Team.RED,
    Team.RED: Team.GREEN,
}


class Role(Enum):
    SCOUT = "scout"
    HEAVY = "heavy"
    COMMANDER = "commander"
    MEDIC = "medic"
    AMMO = "ammo"
    
class GameType(Enum):
    SM5 = "sm5"
    LASERBALL = "laserball"

class EventType(Enum):
    # basic and sm5 events
    MISSION_START = "0100"  # Arguments: "* Mission Start *"
    MISSION_END = "0101"  # Arguments: "* Mission End *"
    SHOT_EMPTY = "0200"  # unused?
    MISS = "0201"  # Arguments: "(entity 1)", " misses"
    MISS_BASE = "0202"  # Arguments: "(entity 1)", " misses ", "(entity 2)". Entity 2 is a base
    HIT_BASE = "0203"  # Arguments: "(entity 1)", " zaps ", "(entity 2)". Entity 2 is a base
    DESTROY_BASE = "0204"  # Arguments: "(entity 1)", " destroys ", "(entity 2)". Entity 2 is a base
    DAMAGED_OPPONENT = "0205"  # Arguments: "(entity 1)", " zaps ", "(entity 2)"
    DOWNED_OPPONENT = "0206"  # Arguments: "(entity 1)", " zaps ", "(entity 2)"
    DAMANGED_TEAM = "0207"  # unused?
    DOWNED_TEAM = "0208"  # unused?
    LOCKING = "0300"  # (aka missile start) Arguments: "(entity 1)", " locking ", "(entity 2)"
    MISSILE_BASE_MISS = "0301"
    MISSILE_BASE_DAMAGE = "0302"
    MISISLE_BASE_DESTROY = "0303"  # Arguments: "(entity 1)", " destroys ", "(entity 2)"
    MISSILE_MISS = "0304"
    MISSILE_DAMAGE_OPPONENT = "0305"  # unused? theres no way for a missile to not down/destroy
    MISSILE_DOWN_OPPONENT = "0306"  # Arguments: "(entity 1)", " missiles ", "(entity 2)"
    MISSILE_DAMAGE_TEAM = "0307"  # unused?
    MISSILE_DOWN_TEAM = "0308"
    ACTIVATE_RAPID_FIRE = "0400"  # Arguments: "(entity 1)", " activates rapid fire"
    DEACTIVATE_RAPID_FIRE = "0401"  # unused?
    ACTIVATE_NUKE = "0404"  # Arguments: "(entity 1)", " activates nuke"
    DETONATE_NUKE = "0405"  # Arguments: "(entity 1)", " detonates nuke"
    RESUPPLY_AMMO = "0500"  # Arguments: "(entity 1)", " resupplies ", "(entity 2)"
    RESUPPLY_LIVES = "0502"  # Arguments: "(entity 1)", " resupplies ", "(entity 2)"
    AMMO_BOOST = "0510"  # Arguments: "(entity 1)", " resupplies team"
    LIFE_BOOST = "0512"  # Arguments: "(entity 1)", " resupplies team"
    PENALTY = "0600"
    ACHIEVEMENT = "0900"  # Arguments: "(entity 1)", " completes an achievement!"
    REWARD = "0902"  # Arguments: "(entity 1)", " earns a reward!"
    BASE_AWARDED = "0B03"  # (technically #0B03 in hex)

    # laserball events

    PASS = "1100"  # Arguments: "(entity 1)", " passes to ", "(entity 2)"
    GOAL = "1101"  # Arguments: "(entity 1)", " scores!"
    ASSIST = "1102"  # THIS IS NOT A REAL EVENT TYPE (as far as im aware, im generating it myself)
    STEAL = "1103"  # Arguments: "(entity 1)", " steals from ", "(entity 2)"
    BLOCK = "1104"  # Arguments: "(entity 1)", " blocks ", "(entity 2)"
    ROUND_START = "1105"  # Arguments: "★ Round Start ★"
    ROUND_END = "1106"  # Arguments: "★ Round End ★"
    GETS_BALL = "1107"  # at the start of the round. Arguments: "(entity 1)", " gets the ball"
    TIME_VIOLATION = "1108"
    CLEAR = "1109"  # Arguments: "(entity 1)", " clears to ", "(entity 2)"
    FAIL_CLEAR = "110A"  # Arguments: "(entity 1)", " fails to clear"
    

class IntRole(IntEnum):
    OTHER = 0 # or no role
    COMMANDER = 1
    HEAVY = 2
    SCOUT = 3
    AMMO = 4
    MEDIC = 5

    def __str__(self) -> str:
        names = {
            0: "Other",
            1: "Commander",
            2: "Heavy",
            3: "Scout",
            4: "Ammo",
            5: "Medic"
        }
        return names.get(self.value, "Base")
    
    @classmethod
    def from_role(cls, role: Role) -> int:
        return cls({
            Role.COMMANDER: 1,
            Role.HEAVY: 2,
            Role.SCOUT: 3,
            Role.AMMO: 4,
            Role.MEDIC: 5
        }.get(role, 0))
    
    def to_role(self) -> Role:
        return {
            1: Role.COMMANDER,
            2: Role.HEAVY,
            3: Role.SCOUT,
            4: Role.AMMO,
            5: Role.MEDIC
        }.get(self.value)
    

class PlayerStateType(IntEnum):
    ACTIVE = 0
    UNKNOWN = 1 # unused?
    RESETTABLE = 2
    DOWN = 3

class Permission(IntEnum):
    USER = 0
    ADMIN = 1

@dataclass
class BallPossessionEvent:
    """This denotes a time at which an entity gains possession of the ball in Laserball."""
    timestamp_millis: int
    entity_id: Optional[str]


class PlayerStateDetailType(IntEnum):
    ACTIVE = 0
    DOWN_ZAPPED = 1
    DOWN_MISSILED = 2
    DOWN_NUKED = 3
    DOWN_FOR_RESUP = 4
    DOWN_FOR_OTHER = 5  # Down for a reason not obvious from logs
    RESETTABLE = 6


@dataclass
class PlayerStateEvent:
    """This denotes a time at which the player state changed."""
    timestamp_millis: int
    state: Optional[PlayerStateDetailType]
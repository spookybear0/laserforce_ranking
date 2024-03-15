from dataclasses import dataclass
from typing import Optional
from enum import Enum, IntEnum

class Team(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

    def standardize(self) -> str:
        return self.value.capitalize()
    

class ElementTeam(Enum):
    FIRE = "Fire"
    EARTH = "Earth"
    ICE = "Ice"


TEAM_TO_ELEMENT_TEAM = {
    Team.RED: ElementTeam.FIRE,
    Team.GREEN: ElementTeam.EARTH,
    Team.BLUE: ElementTeam.ICE,
}

SM5_ENEMY_TEAM = {
    ElementTeam.EARTH: ElementTeam.FIRE,
    ElementTeam.FIRE: ElementTeam.EARTH,
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
    MISSION_START = "0100"
    MISSION_END = "0101"
    SHOT_EMPTY = "0200" # unused?
    MISS = "0201"
    MISS_BASE = "0202"
    HIT_BASE = "0203"
    DESTROY_BASE = "0204"
    DAMAGED_OPPONENT = "0205"
    DOWNED_OPPONENT = "0206"
    DAMANGED_TEAM = "0207" # unused?
    DOWNED_TEAM = "0208" # unused?
    LOCKING = "0300" # (aka missile start)
    MISSILE_BASE_MISS = "0301"
    MISSILE_BASE_DAMAGE = "0302"
    MISISLE_BASE_DESTROY = "0303"
    MISSILE_MISS = "0304"
    MISSILE_DAMAGE_OPPONENT = "0305" # unused? theres no way for a missile to not down/destroy
    MISSILE_DOWN_OPPONENT = "0306"
    MISSILE_DAMAGE_TEAM = "0307" # unused?
    MISSILE_DOWN_TEAM = "0308"
    ACTIVATE_RAPID_FIRE = "0400"
    DEACTIVATE_RAPID_FIRE = "0401" # unused?
    ACTIVATE_NUKE = "0404"
    DETONATE_NUKE = "0405"
    RESUPPLY_AMMO = "0500"
    RESUPPLY_LIVES = "0502"
    AMMO_BOOST = "0510"
    LIFE_BOOST = "0512"
    PENALTY = "0600"
    ACHIEVEMENT = "0900"
    REWARD = "0902"
    BASE_AWARDED = "0B03" # (technically #0B03 in hex)

    # laserball events

    PASS = "1100"
    GOAL = "1101"
    ASSIST = "1102" # THIS IS NOT A REAL EVENT TYPE (as far as im aware, im generating it myself)
    STEAL = "1103"
    BLOCK = "1104"
    ROUND_START = "1105"
    ROUND_END = "1106"
    GETS_BALL = "1107" # at the start of the round
    TIME_VIOLATION = "1108"
    CLEAR = "1109"
    FAIL_CLEAR = "110A"
    

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
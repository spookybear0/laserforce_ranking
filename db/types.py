from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Optional, List


@dataclass
class RgbColor:
    """An RGB value, with each component having a value between 0 and 255."""
    red: int
    green: int
    blue: int

    @property
    def rgb_value(self) -> str:
        """Returns the color as an RGB string to plug into HTML or CSS."""
        return "#%02x%02x%02x" % (self.red, self.green, self.blue)

    def add(self, other: "RgbColor") -> "RgbColor":
        """Returns a new RgbColor() that is the addition of this and the other one.

        Components are clamped at their max value."""
        return RgbColor(
            red=self._add_values(self.red, other.red),
            green=self._add_values(self.green, other.green),
            blue=self._add_values(self.blue, other.blue)
        )

    def multiply(self, multiplier: int) -> "RgbColor":
        """Returns a new RgbColor() that is each component multiplied by a value.

        Components are clamped at their max value."""
        return RgbColor(
            red=self._add_values(self.red, multiplier),
            green=self._add_values(self.green, multiplier),
            blue=self._add_values(self.blue, multiplier)
        )

    @staticmethod
    def _add_values(value1: int, value2: int) -> int:
        return min(value1 + value2, 255)

    @staticmethod
    def _multiply_value(value1: int, value2: int) -> int:
        return min(value1 * value2, 255)


@dataclass
class _TeamDefinition:
    """Descriptor for a team.

    When converted to a string, it is shown as the lower-case color name so Tortoise can use it as an enum value for
    its schema."""
    # Lower case name of the team, expressed as a color.
    color: str

    # Name of the team, expressed as an element (Fire, Earth).
    element: str

    # CSS class to use to show text in the color of the team.
    css_class: str

    # CSS name of the color.
    css_color_name: str

    # Color as an rgb() value for cases where CSS cannot be used, like Canvas (i.e. charts).
    plain_color: str

    # Color value of a dimmed version of the team color.
    dim_color: RgbColor

    def __eq__(self, color: str) -> bool:
        return self.color == color

    def __len__(self):
        # Tortoise uses the length of the enum value.
        return len(self.color)

    def __str__(self):
        return self.color

    def __repr__(self):
        return f'"{self.color}"'

    def __json__(self):
        return f'"{self.color}"'

    def __hash__(self):
        return self.color.__hash__()


class Team(Enum):
    # neutral team, sometimes None is used instead of this
    NEUTRAL = _TeamDefinition(color="neutral", element="Neutral", css_class="neutral-team", css_color_name="white",
                              dim_color=RgbColor(red=68, green=68, blue=68), plain_color="rgb(255, 255, 255)")
    NONE = _TeamDefinition(color="none", element="None", css_class="none-team", css_color_name="white",
                           dim_color=RgbColor(red=68, green=68, blue=68), plain_color="rgb(255, 255, 255)")

    RED = _TeamDefinition(color="red", element="Fire", css_class="fire-team", css_color_name="orangered",
                          dim_color=RgbColor(red=68, green=17, blue=0), plain_color="rgb(255, 69, 0)")
    GREEN = _TeamDefinition(color="green", element="Earth", css_class="earth-team", css_color_name="greenyellow",
                            dim_color=RgbColor(red=43, green=60, blue=12), plain_color="rgb(173, 255, 47)")
    BLUE = _TeamDefinition(color="blue", element="Ice", css_class="ice-team", css_color_name="#0096FF",
                           dim_color=RgbColor(red=0, green=37, blue=68), plain_color="rgb(0, 150, 255)")
    # new additions for laserball ramps mode
    YELLOW = _TeamDefinition(color="yellow", element="Yellow", css_class="yellow-team", css_color_name="gold",
                             dim_color=RgbColor(red=68, green=68, blue=0), plain_color="rgb(255, 215, 0)")
    PURPLE = _TeamDefinition(color="purple", element="Purple", css_class="purple-team", css_color_name="#A020F0",
                             dim_color=RgbColor(red=34, green=0, blue=68), plain_color="rgb(160, 32, 240)")

    def __call__(cls, value, *args, **kw):
        # Tortoise looks up values by the lower-case color name.
        if type(value) is str:
            for teams in cls:
                if teams.value.color == value:
                    return super().__call__(teams, *args, **kw)
        return super().__call__(value, *args, **kw)

    def standardize(self) -> str:
        """The color name starting in upper case, like "Red" or "Blue"."""
        return self.value.color.capitalize()

    @property
    def element(self) -> str:
        """The element, like "Fire" or "Ice"."""
        return self.value.element

    @property
    def css_class(self) -> str:
        """CSS class to use to show text using the color of this team."""
        return self.value.css_class

    @property
    def dim_css_class(self) -> str:
        """CSS class to use to show text using the color of this team but dimmed (used when a player is down)."""
        return f"{self.value.css_class}-dim"

    @property
    def down_css_class(self) -> str:
        """CSS class to use for a player on this team who is currently down - slightly dimmer."""
        return f"{self.value.css_class}-down"

    @property
    def css_color_name(self) -> str:
        """CSS color to use for this team, could be a RGB HEX value or a CSS color value."""
        return self.value.css_color_name

    @property
    def dim_color(self) -> RgbColor:
        """Color to use for this team at a darker brightness, good for line graphs showing peripheral data."""
        return self.value.dim_color

    @property
    def plain_color(self) -> str:
        """Color to use for this team, expressed as an Rgb() string."""
        return self.value.plain_color

    @property
    def name(self) -> str:
        """The display name, like "Earth Team"."""
        return f"{self.element} Team"

    @property
    def short_name(self):
        """Returns the name without 'Team' in it to keep it short."""
        return re.sub(r"\s*Team\s*", "", self.name)


# Mapping of opposing teams in SM5 games.
SM5_ENEMY_TEAM = {
    Team.GREEN: Team.RED,
    Team.RED: Team.GREEN,
}

# Name to team

NAME_TO_TEAM = {
    # neutral/none
    "Neutral": Team.NEUTRAL,
    None: Team.NONE,
    "None": Team.NONE,
    # real teams
    "Fire": Team.RED,
    "Earth": Team.GREEN,
    "Red": Team.RED,
    "Green": Team.GREEN,
    "Blue": Team.BLUE,
    "Ice": Team.BLUE,
    # laserball ramps
    "Yellow": Team.YELLOW,
    "Purple": Team.PURPLE,
}


class Role(Enum):
    COMMANDER = "commander"
    HEAVY = "heavy"
    SCOUT = "scout"
    AMMO = "ammo"
    MEDIC = "medic"


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
    PENALTY = "0600"  # Arguments: "(entity 1)", " is penalized"
    ACHIEVEMENT = "0900"  # Arguments: "(entity 1)", " completes an achievement!"
    REWARD = "0902"  # Arguments: "(entity 1)", " earns a reward!"
    BASE_AWARDED = "0B03"  # (technically #0B03 in hex) Arguments: "(entity 1)", " is awarded ", "(entity 2)"

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
    RESET_ON_BASE = "110B"  # Arguments: "(entity 1)", " resets on (base entity)"


class IntRole(IntEnum):
    OTHER = 0  # or no role
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
    UNKNOWN = 1  # unused?
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


@dataclass
class PieChartData:
    """Data sent to a frontend template to display a pie chart."""
    labels: List[str]
    colors: List[str]
    data: List[int]


@dataclass
class LineChartData:
    """Data sent to a frontend template to display a line chart dataset."""
    label: str
    color: str
    data: List[int]
    borderWidth: int = 3


ROLES = [
    str(role) for role in IntRole if role != IntRole.OTHER
]

ROLE_MAP = {
    str(role): role for role in IntRole if role != IntRole.OTHER
}

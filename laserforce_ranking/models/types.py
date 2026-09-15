from typing import Optional, Union
from dataclasses import dataclass
from enum import Enum, IntEnum
from django.db import models
import re

@dataclass(frozen=True)
class Site:
    """
    Represents a Laserforce site with its associated information.

    Attributes:
        id (str): The unique identifier for the site (e.g., "4-19").
        name (str): The short name of the site (e.g., "Loveland").
        ipl_name (str): The long name of the site that IPL shows (e.g., "Loveland Laser Tag Fun Center").
        timezone_offset (str): The timezone offset for the site in the format "+HH:MM" or "-HH:MM".
        timezone_name (str): The name of the timezone for the site (e.g., "America/Denver").
        competitive (bool): Indicates whether the site is considered competitive, this means we store tdfs for it. Defaults to True.
            the point of storing non-competitve sites is if a player's home site is not competitive, we can still show it on their profile.
    """
    id: str
    name: str
    ipl_name: str
    timezone_offset: Optional[str] = None
    timezone_name: Optional[str] = None
    competitive: bool = True

    def __str__(self):
        return f"{self.name} ({self.id})"
    
    def __repr__(self):
        return f"Site(id={self.id}, name={self.name}, ipl_name={self.ipl_name}, timezone_offset={self.timezone_offset}, timezone_name={self.timezone_name}, competitive={self.competitive})"

SITES = [
    Site(
        id="4-19",
        name="Loveland",
        ipl_name="Loveland Laser Tag Fun Center",
        timezone_offset="+07:00",
        timezone_name="America/Denver",
        competitive=True
    ),
    Site(
        id="1-1",
        name="Brisbane",
        ipl_name="Laserforce Brisbane, QLD, AU",
        timezone_offset="+10:00",
        timezone_name="Australia/Brisbane",
        competitive=True
    ),
    Site(
        id="4-23",
        name="Syracuse",
        ipl_name="The Fun Warehouse, Syracuse",
        timezone_offset="-05:00",
        timezone_name="America/New_York",
        competitive=True
    ),
    Site(
        id="4-43",
        name="Invasion",
        ipl_name="Invasion Laser Tag, San Marcos, CA, US",
        timezone_offset="-07:00",
        timezone_name="America/Denver",
        competitive=True
    ),
    Site(
        id="4-2",
        name="St George",
        ipl_name="Laser Mania, St George, UT, USA",
        timezone_offset="+07:00",
        timezone_name="America/Denver",
        competitive=True
    ),
    Site(
        id="3-3",
        name="Auckland Wairau",
        ipl_name="Laserforce Auckland",
        timezone_offset="+13:00",
        timezone_name="Pacific/Auckland",
        competitive=True
    ),
    Site(
        id="4-6",
        name="Detroit",
        ipl_name="Revolution Laser Tag & Arcade, MI, USA",
        timezone_offset="-05:00",
        timezone_name="America/New_York",
        competitive=True
    ),
    Site(
        id="20-7",
        name="Lasergame Říčany",
        ipl_name="Ricany Lasergame, Ricany, CZ",
        timezone_offset="+02:00",
        timezone_name="Europe/Prague",
        competitive=True
    ),
    Site(
        id="21-8",
        name="PowerLaser Stuttgart",
        ipl_name="PowerLaser, Stuttgart, Germany",
        timezone_offset="+02:00",
        timezone_name="Europe/Berlin",
        competitive=True
    ),
    Site(
        id="21-70",
        name="LaserTag Darmstadt",
        ipl_name="Lasertag Deutschland 1, Darmstadt, Germany",
        timezone_offset="+02:00",
        timezone_name="Europe/Berlin",
        competitive=True
    ),
    Site(
        id="1-58",
        name="Wollongong Revolution",
        ipl_name="Revolution Laser Arena, Wollongong, NSW, AU",
        timezone_offset="+11:00",
        timezone_name="Australia/Sydney",
        competitive=True
    ),
    Site(
        id="3-7",
        name="Auckland Game Over",
        ipl_name="Game Over, Albany, NZ",
        timezone_offset="+13:00",
        timezone_name="Pacific/Auckland",
        competitive=True
    ),
    Site(
        id="7-2",
        name="Peterborough",
        ipl_name="Laserforce Peterborough",
        timezone_offset="+00:00",
        timezone_name="Europe/London",
        competitive=True
    ),
    Site(
        id="7-13",
        name="Cheltenham",
        ipl_name="Funky Laser, Cheltenham, UK",
        timezone_offset="+00:00",
        timezone_name="Europe/London",
        competitive=True
    ),
    Site(
        id="1-64",
        name="Sydney Underworld",
        ipl_name="Underworld Laser, Menai, NSW, AU",
        timezone_offset="+11:00",
        timezone_name="Australia/Sydney",
        competitive=True
    ),
    Site(
        id="7-8",
        name="Huddersfield",
        ipl_name="LaserZone, Huddersfield, UK",
        timezone_offset="+00:00",
        timezone_name="Europe/London",
        competitive=True
    ),
    Site(
        id="20-18",
        name="Lasergame Beroun",
        ipl_name="Lasergame Beroun, Czech Republic",
        timezone_offset="+02:00",
        timezone_name="Europe/Prague",
        competitive=True
    ),
    Site(
        id="4-80",
        name="Lost Worlds",
        ipl_name="Lost Worlds Entertainment, City of Industry, CA",
        timezone_offset="-08:00",
        timezone_name="America/Los_Angeles",
        competitive=True
    ),
    Site(
        id="4-3",
        name="Carmichael",
        ipl_name="Lasertag Of Carmichael",
        timezone_offset="-08:00",
        timezone_name="America/Los_Angeles",
        competitive=False
    ),
]

SITE_BY_ID = {site.id: site for site in SITES}
SITE_BY_NAME = {site.name: site for site in SITES}
SITE_BY_IPL_NAME = {
    site.ipl_name: site
    for site in SITES
    if site.ipl_name is not None
}

COMPETITIVE_SITES = {
    site.id: site
    for site in SITES
    if site.competitive
}

@dataclass
class RgbColor:
    """An RGB value, with each component having a value between 0 and 255."""
    red: int
    green: int
    blue: int

    @property
    def rgb_tuple(self) -> tuple[int, int, int]:
        """Returns the color as a tuple of (red, green, blue)."""
        return self.red, self.green, self.blue

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
        return len(self.color)

    def __str__(self):
        return self.color

    def __repr__(self):
        return f'"{self.color}"'

    def __json__(self):
        return f'"{self.color}"'

    def __hash__(self):
        return self.color.__hash__()

class TeamType(Enum):
    # neutral team, sometimes None is used instead of this
    NEUTRAL = _TeamDefinition(color="neutral", element="Neutral", css_class="neutral-team", css_color_name="#9ca3af",
                              dim_color=RgbColor(red=68, green=68, blue=68), plain_color=RgbColor(red=255, green=255, blue=255))
    NONE = _TeamDefinition(color="none", element="None", css_class="none-team", css_color_name="#9ca3af",
                           dim_color=RgbColor(red=68, green=68, blue=68), plain_color=RgbColor(red=255, green=255, blue=255))

    RED = _TeamDefinition(color="red", element="Fire", css_class="fire-team", css_color_name="orangered",
                          dim_color=RgbColor(red=68, green=17, blue=0), plain_color=RgbColor(red=255, green=69, blue=0))
    GREEN = _TeamDefinition(color="green", element="Earth", css_class="earth-team", css_color_name="greenyellow",
                            dim_color=RgbColor(red=43, green=60, blue=12), plain_color=RgbColor(red=173, green=255, blue=47))
    BLUE = _TeamDefinition(color="blue", element="Ice", css_class="ice-team", css_color_name="#0096FF",
                           dim_color=RgbColor(red=0, green=37, blue=68), plain_color=RgbColor(red=0, green=150, blue=255))
    # new additions for laserball ramps mode
    YELLOW = _TeamDefinition(color="yellow", element="Yellow", css_class="yellow-team", css_color_name="gold",
                             dim_color=RgbColor(red=68, green=68, blue=0), plain_color=RgbColor(red=255, green=215, blue=0))
    PURPLE = _TeamDefinition(color="purple", element="Purple", css_class="purple-team", css_color_name="#A020F0",
                             dim_color=RgbColor(red=34, green=0, blue=68), plain_color=RgbColor(red=160, green=32, blue=240))
    # powerlaser stuttgart has a pink team
    PINK = _TeamDefinition(color="pink", element="Pink", css_class="pink-team", css_color_name="#FF69B4",
                           dim_color=RgbColor(red=68, green=17, blue=34), plain_color=RgbColor(red=255, green=105, blue=180))

    def __call__(cls, value, *args, **kw):
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
        """CSS class to use to show text using the color of this Team."""
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
    def plain_color(self) -> RgbColor:
        """Color to use for this team."""
        return self.value.plain_color

    @property
    def name(self) -> str:
        """The display name, like "Earth Team"."""
        return f"{self.element} Team"

    @property
    def short_name(self):
        """Returns the name without 'Team' in it to keep it short."""
        return re.sub(r"\s*Team\s*", "", self.name)


# Mapping of opposing teams in SM5 games. TODO: Fix
SM5_ENEMY_TEAM = {
    TeamType.GREEN: TeamType.RED,
    TeamType.RED: TeamType.GREEN,
}

# Name to team

NAME_TO_TEAM = {
    # neutral/none
    "Neutral": TeamType.NEUTRAL,
    None: TeamType.NONE,
    "Unknown": TeamType.NONE,
    "None": TeamType.NONE,
    # real teams
    "Fire": TeamType.RED,
    "Earth": TeamType.GREEN,
    "Red": TeamType.RED,
    "Green": TeamType.GREEN,
    "Blue": TeamType.BLUE,
    "Ice": TeamType.BLUE,
    # some arenas have different team names
    # laserball ramps
    "Yellow": TeamType.YELLOW,
    "Purple": TeamType.PURPLE,
    # powerlaser stuttgart
    "Pink": TeamType.PINK,
}

# Ways we can lock a specific player to a position or group
# of positions during matchmaking.

class RoleLock(Enum):
    NONE = "none"
    COMMANDER = "commander"
    HEAVY = "heavy"
    SCOUT = "scout"
    AMMO = "ammo"
    MEDIC = "medic"
    THREE_HIT = "3-hit"
    ONE_HIT = "1-hit"
    RESUPPLY = "resupply"
    NON_RESUPPLY = "non-resupply"
    OFFENSE = "offense"
    DEFENSE = "defense"

    @property
    def display_name(self) -> str:
        """Returns a display name for the role lock."""
        return self.value.title()
    
    @property
    def allowed_roles(self) -> list["IntRole"]:
        """Returns a list of roles that are allowed for this role lock."""
        if self in [RoleLock.COMMANDER, RoleLock.HEAVY, RoleLock.SCOUT, RoleLock.AMMO, RoleLock.MEDIC]:
            return [IntRole.from_role(Role(self.value))]
        elif self == RoleLock.THREE_HIT:
            return [IntRole.COMMANDER, IntRole.HEAVY]
        elif self == RoleLock.ONE_HIT:
            return [IntRole.SCOUT, IntRole.AMMO, IntRole.MEDIC]
        elif self == RoleLock.RESUPPLY:
            return [IntRole.AMMO, IntRole.MEDIC]
        elif self == RoleLock.NON_RESUPPLY:
            return [IntRole.COMMANDER, IntRole.HEAVY, IntRole.SCOUT]
        elif self == RoleLock.OFFENSE:
            return [IntRole.COMMANDER, IntRole.SCOUT]
        elif self == RoleLock.DEFENSE:
            return [IntRole.HEAVY, IntRole.AMMO, IntRole.MEDIC]
        else: # no lock
            return [IntRole.COMMANDER, IntRole.HEAVY, IntRole.SCOUT, IntRole.AMMO, IntRole.MEDIC]

class Role(models.TextChoices):
    COMMANDER = "commander"
    HEAVY = "heavy"
    SCOUT = "scout"
    AMMO = "ammo"
    MEDIC = "medic"


class GameType(models.TextChoices):
    SM5 = "sm5"
    LASERBALL = "laserball"


class EventType(models.TextChoices):
    # basic and sm5 events
    MISSION_START = "0100"  # Arguments: "* Mission Start *"
    MISSION_END = "0101"  # Arguments: "* Mission End *"
    SHOT_EMPTY = "0200"  # unused?
    MISS = "0201"  # Arguments: "(entity 1)", " misses" (this is NOT shown on scoreboard, only in logs)
    MISS_BASE = "0202"  # Arguments: "(entity 1)", " misses ", "(entity 2)". Entity 2 is a base
    HIT_BASE = "0203"  # Arguments: "(entity 1)", " zaps ", "(entity 2)". Entity 2 is a base
    DESTROY_BASE = "0204"  # Arguments: "(entity 1)", " destroys ", "(entity 2)". Entity 2 is a base
    DAMAGED_OPPONENT = "0205"  # Arguments: "(entity 1)", " zaps ", "(entity 2)"
    DOWNED_OPPONENT = "0206"  # Arguments: "(entity 1)", " zaps ", "(entity 2)"
    DAMANGED_TEAM = "0207"  # unused?
    DOWNED_TEAM = "0208"  # unused?
    WARBOT_ZAP = "0209"  # Arguments: "(entity 1)", " zaps ", "(entity 2)". Entity 1 is a warbot, entity 2 is a player
    LOCKING = "0300"  # (aka missile start) Arguments: "(entity 1)", " locking ", "(entity 2)"
    MISSILE_BASE_MISS = "0301" # you have to be really bad to trigger this event
    MISSILE_BASE_DAMAGE = "0302" # not used in sm5
    MISSILE_BASE_DESTROY = "0303"  # Arguments: "(entity 1)", " destroys ", "(entity 2)"
    MISSILE_MISS = "0304" # Arguments: "(entity 1)", " misses ", "(entity 2)"
    MISSILE_DAMAGE_OPPONENT = "0305"  # unused? theres no way for a missile to not down/destroy in sm5
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
    WIN_TICKETS = "0901"  # Arguments: "(entity 1)", " wins ", "(int:tickets)"
    REWARD = "0902"  # Arguments: "(entity 1)", " earns a reward!"
    CLAIM_BEACON = "0B00"  # Arguments: "(entity 1)", " claims a beacon"
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


class IntRole(models.IntegerChoices):
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
        return names.get(self.value, "Other")

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


class PlayerStateType(models.IntegerChoices):
    ACTIVE = 0
    UNKNOWN = 1  # unused?
    RESETTABLE = 2
    DOWN = 3

class EntityType(models.TextChoices):
    PLAYER = "player"
    TARGET = "standard-target"
    GENERATOR_TARGET = "generator-target"
    BEACON = "beacon"
    REFEREE = "referee"
    WARBOT = "warbot" # zap players with 209 events
    FLAG = "flag"
    PHASER_STATION = "phaser-station"
    GALLERY_TARGET = "gallery-target"
    SERPENT = "serpent"
    RELOAD = "reload"
    VORTEX = "vortex"
    MINI_TARGET = "mini-target"
    UNKNOWN = "unknown"

class EntityEndType(models.IntegerChoices):
    KICKED = 1
    MISSION_COMPLETED = 2
    ELIMINATED = 4
    KICKED_BY_REFEREE = 17 # legacy, livesLeft should be set to 0 in this case

class Permission(models.IntegerChoices):
    USER = 0
    ADMIN = 1
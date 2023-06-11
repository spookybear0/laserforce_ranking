from dataclasses import dataclass, field
from typing import List
from enum import Enum


class Role(Enum):
    BASE = 0
    COMMANDER = 1
    HEAVY = 2
    SCOUT = 3
    AMMO = 4
    MEDIC = 5


class Team(Enum):
    RED = 0
    GREEN = 1
    NEUTRAL = 2


class Level(Enum):
    NONE = 0
    RECRUIT = 1
    GUNNER = 2
    TROOPER = 3
    CAPTAIN = 4
    STARLORD = 5
    LASERMASTER = 6
    CONQUERER = 7
    TITAN = 8
    LEGEND = 9


@dataclass
class Teams:
    id: int
    name: str
    color_enum: int  # unknown how this works
    color_name: str
    players: List["Entity"] = field(default_factory=list)


@dataclass
class Entity:
    time: int
    id: str  # ipl token id
    type: str
    codename: str
    team: int
    level: int
    role: Role  # enum role of entity
    battlesuit: str


@dataclass
class Event:
    time: int
    type: int
    entity1: str  # ipl token id
    action: str
    entity2: str  # ipl token id


@dataclass
class ScoreChange:
    time: int
    entity: str  # ipl token id
    old: int  # score before change (new - delta)
    delta: int  # how much it changed (new - old)
    new: int  # after the change (old + delta)


@dataclass
class EntityEnd:
    time: int
    id: str
    type: int
    score: int


@dataclass
class SM5Stat:
    id: str
    shotsHit: int
    shotsFired: int
    timesZapped: int
    timesMissiled: int
    missileHits: int
    nukesDetonated: int
    nukesActivated: int
    nukeCancels: int
    medicHits: int
    ownMedicHits: int
    medicNukes: int
    scoutRapid: int
    lifeBoost: int
    ammoBoost: int
    livesLeft: int
    shotsLeft: int
    penalties: int
    shot3Hit: int
    ownNukeCancels: int
    shotOpponent: int
    shotTeam: int
    missiledOpponent: int
    missiledTeam: int


@dataclass
class SM5_TDF_Game:
    # info
    file_version: float = None
    program_version: float = None
    center: str = None

    # mission info
    type: int = None
    description: str = None
    start_time: int = None
    duration: int = None
    penalties: int = None

    # team info
    teams: List[Teams] = field(default_factory=list)

    bases: List[Entity] = field(default_factory=list)

    # players and targets init
    entities: List[Entity] = field(default_factory=list)

    # game events (including zaps)
    events: List[Event] = field(default_factory=list)

    # each time scores were updated
    score_changes: List[ScoreChange] = field(default_factory=list)

    # final score (when eliminated or game end) (INCLUDES BASE, score=0)
    entity_end: List[EntityEnd] = field(default_factory=list)

    # each players sm5 stats
    sm5_stats: List[SM5Stat] = field(default_factory=list)


def comment(game, data):
    return game


def info(game, data):
    game.file_version = float(data[0])
    game.program_version = float(data[1])
    game.center = data[2]
    return game


def mission(game, data):
    game.type = int(data[0])
    game.description = data[1]
    game.start_time = int(data[2])
    game.duration = int(data[3])
    game.penalties = int(data[4])
    return game


def team(game, data):
    if not game.teams:
        game.teams = []
    game.teams.append(Teams(int(data[0]), data[1], int(data[2]), data[3]))
    return game


def entity_start(game: SM5_TDF_Game, data):
    if not game.entities:
        game.entities = []
    ent = Entity(
        int(data[0]),
        data[1],
        data[2],
        data[3],
        Team(int(data[4])),
        int(data[5]),
        Role(int(data[6])),
        data[7],
    )
    game.entities.append(ent)

    if ent.role == Role.BASE:
        if not game.bases:
            game.bases = []
        game.bases.append(ent)
    else:
        for team in game.teams:
            if team.id == int(data[4]):
                team.players.append(ent)
                break

    return game


def event(game, data):
    if not game.events:
        game.events = []
    game.events.append(
        Event(
            int(data[0]),
            int(data[1]),
            data[2] if len(data) > 2 else None,
            data[3][:-1][1:]
            if len(data) > 3 and data[3].endswith(" ")
            else data[3][1:]
            if len(data) > 3
            else None,  # removes pre and after spaces
            data[4] if len(data) > 4 else None,
        )
    )
    return game


def score(game, data):
    if not game.score_changes:
        game.score_changes = []
    game.score_changes.append(
        ScoreChange(int(data[0]), data[1], int(data[2]), int(data[3]), int(data[4]))
    )
    return game


def entity_end(game, data):
    if not game.entity_end:
        game.entity_end = []
    game.entity_end.append(EntityEnd(int(data[0]), data[1], int(data[2]), int(data[3])))
    return game


def sm5_stats(game, data):
    if not game.sm5_stats:
        game.sm5_stats = []
    game.sm5_stats.append(
        SM5Stat(
            data[0],
            int(data[1]),
            int(data[2]),
            int(data[3]),
            int(data[4]),
            int(data[5]),
            int(data[6]),
            int(data[7]),
            int(data[8]),
            int(data[9]),
            int(data[10]),
            int(data[11]),
            int(data[12]),
            int(data[13]),
            int(data[14]),
            int(data[15]),
            int(data[16]),
            int(data[17]),
            int(data[18]),
            int(data[19]),
            int(data[20]),
            int(data[21]),
            int(data[22]),
            int(data[23]),
        )
    )
    return game


def parse_sm5_game(file_location: str) -> SM5_TDF_Game:
    file = open(file_location, "r", encoding="utf-16")

    game = SM5_TDF_Game()

    count = 0
    while True:
        count += 1

        line = file.readline()

        if not line:
            break  # eof

        cases = {
            ";": comment,  # skips
            "0": info,  # system info
            "1": mission,  # mission info
            "2": team,  # all teams identifiers
            "3": entity_start,  # entity init
            "4": event,  # all events (including system)
            "5": score,  # all score changes (kind of redundent but important for 3 hits and stuff)
            "6": entity_end,  # final score at the end (or when eliminated) (INCLUDES BASE, score=0)
            "7": sm5_stats,  # final sm5 stats
        }

        first_char = line[0]

        line = line.split("\t")[
            1:
        ]  # remove first element of data list because it is already parsed
        line[-1] = line[-1].strip("\n")  # remove newline

        # get first char and use switch case to decide which function will decode it
        game = cases[first_char](game, line)

    file.close()

    return game
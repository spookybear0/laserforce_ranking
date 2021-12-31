from dataclasses import dataclass
from typing import List
from enum import Enum

class Role(Enum):
    BASE=0
    COMMANDER=1
    HEAVY=2
    SCOUT=3
    AMMO=4
    MEDIC=5
    
class Team(Enum):
    RED=0
    GREEN=1
    NEUTRAL=2
    
class Level(Enum):
    NONE=0
    RECRUIT=1
    GUNNER=2
    TROOPER=3
    CAPTAIN=4
    STARLORD=5
    LASERMASTER=6
    CONQUERER=7
    TITAN=8
    LEGEND=9

@dataclass
class Teams:
    id: int=None
    name: str=None
    color_enum: int=None # unknown how this works
    color_name: str=None
    
@dataclass
class Entity:
    time: int=None
    id: str=None # ipl token id
    type: str=None
    codename: str=None
    team: int=None
    level: int=None
    role: Role=None # enum role of entity
    battlesuit: str=None

@dataclass
class Event:
    time: int=None
    type: int=None
    entity1: str=None # ipl token id
    action: str=None
    entity2: str=None # ipl token id

@dataclass
class ScoreChange:
    time: int=None
    entity: str=None # ipl token id
    old: int=None # score before change (new - delta)
    delta: int=None # how much it changed (new - old)
    new: int=None # after the change (old + delta)
    
@dataclass
class EntityEnd:
    time: int=None
    id: str=None
    type: int=None
    score: int=None
    
@dataclass
class SM5Stat:
    id: str=None
    shotsHit: int=None
    shotsFired: int=None
    timesZapped: int=None
    timesMissiled: int=None
    missileHits: int=None
    nukesDetonated: int=None
    nukesActivated: int=None
    nukeCancels: int=None
    medicHits: int=None
    ownMedicHits: int=None
    medicNukes: int=None
    scoutRapid: int=None
    lifeBoost: int=None
    ammoBoost: int=None
    livesLeft: int=None
    shotsLeft: int=None
    penalties: int=None
    shot3Hit: int=None
    ownNukeCancels: int=None
    shotOpponent: int=None
    shotTeam: int=None
    missiledOpponent: int=None
    missiledTeam: int=None

@dataclass
class TDF_Game:
    # info
    file_version: float=None
    program_version: float=None
    center: str=None
    
    # mission info
    type: int=None
    description: str=None
    start_time: int=None
    duration: int=None
    penalties: int=None
    
    # team info
    teams: List[Teams]=None
    
    # players and targets init
    entities: List[Entity]=None
    
    # game events (including zaps)
    events: List[Event]=None
    
    # each time scores were updated
    score_changes: List[ScoreChange]=None
    
    # final score (when eliminated or game end) (INCLUDES BASE, score=0)
    entity_end: List[EntityEnd]=None

    # each players sm5 stats
    sm5_stats: List[SM5Stat]=None

def comment(game, data): return game

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
    if not game.teams: game.teams = []
    game.teams.append(Teams(int(data[0]), data[1], int(data[2]), data[3]))
    return game

def entity_start(game, data):
    if not game.entities: game.entities = []
    game.entities.append(Entity(int(data[0]), data[1], data[2], data[3], Team(int(data[4])), int(data[5]), Role(int(data[6])), data[7]))
    return game

def event(game, data):
    if not game.events: game.events = []
    game.events.append(Event(int(data[0]),
                             int(data[1]),
                             data[2] if len(data) > 2 else None,
                             data[3][:-1][1:] if len(data) > 3 and data[3].endswith(" ") else data[3][1:] if len(data) > 3 else None, # removes pre and after spaces
                             data[4] if len(data) > 4 else None))
    return game

def score(game, data):
    if not game.score_changes: game.score_changes = []
    game.score_changes.append(ScoreChange(int(data[0]), data[1], int(data[2]), int(data[3]), int(data[4])))
    return game

def entity_end(game, data):
    if not game.entity_end: game.entity_end = []
    game.entity_end.append(EntityEnd(int(data[0]), data[1], int(data[2]), int(data[3])))
    return game

def sm5_stats(game, data):
    if not game.sm5_stats: game.sm5_stats = []
    game.sm5_stats.append(SM5Stat(data[0], int(data[1]), int(data[2]), int(data[3]), int(data[4]), int(data[5]),
                                   int(data[6]), int(data[7]), int(data[8]), int(data[9]), int(data[10]), int(data[11]),
                                   int(data[12]), int(data[13]), int(data[14]), int(data[15]), int(data[16]), int(data[17]),
                                   int(data[18]), int(data[19]), int(data[20]), int(data[21]), int(data[22]), int(data[23])))
    return game


def parse_game(file_location: str) -> TDF_Game:
    file = open(file_location, "r", encoding="utf-16")
    
    game = TDF_Game()

    count = 0
    while True: # c++-like parsing
        count += 1
        
        line = file.readline()
        
        if not line: break # eof
        
        cases = {
            ";": comment, # skips
            "0": info, # system info
            "1": mission, # mission info
            "2": team, # all teams identifiers
            "3": entity_start, # entity init
            "4": event, # all events (including system)
            "5": score, # all score changes (kind of redundent but important for 3 hits and stuff)
            "6": entity_end, # final score at the end (or when eliminated) (INCLUDES BASE, score=0)
            "7": sm5_stats # final sm5 stats
        }
        
        first_char = line[0]
        
        line = line.split("\t")[1:] # remove first element of data list because it is already parsed
        line[-1] = line[-1].strip("\n") # remove newline
        
        game = cases[first_char](game, line) # get first char and use switch case to decide which function will decode it 
    
    file.close()
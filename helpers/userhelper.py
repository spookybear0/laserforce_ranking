from typing import List, Optional
import sys

def in_ipynb() -> bool:
    return "ipykernel" in sys.modules

if not in_ipynb():
    from shared import app
from db.game import EntityEnds, EntityStarts
from db.player import Player
from db.types import IntRole
from db.sm5 import SM5Game
from statistics import median
import bcrypt

async def player_from_token(game: SM5Game, token: str) -> EntityStarts:
    return await game.entity_starts.filter(entity_id=token).first()

async def get_median_role_score(player: Optional[Player]=None) -> List[int]:
    """
    Returns a list of median scores for each role for a player.

    If player is None, returns a list of median scores for each role for all players.
    """
    data = []

    for role in range(1, 6):
        try:
            if player:    
                score = median(await EntityEnds.filter(entity__entity_id=player.entity_id, entity__role=IntRole(role), entity__sm5games__ranked=True).values_list("score", flat=True))
            else:
                score = median(await EntityEnds.filter(entity__role=IntRole(role), entity__sm5games__ranked=True).values_list("score", flat=True))
        except Exception:
            score = 0
        if score:
            data.append(int(score))
        else:
            data.append(0)

    return data

def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    """
    Checks a password against a hash using bcrypt

    Takes a plaintext password and a hashed password
    """
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def to_hex(tag: str) -> str:
    return "LF/0D00" + hex(int(tag)).strip("0x").upper()

def to_decimal(tag: str) -> str:
    return "000" + str(int(tag.strip("LF/").strip("0D00"), 16))
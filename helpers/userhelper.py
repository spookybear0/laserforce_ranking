from objects import Team, Role, GameType, SM5GamePlayer, LaserballGamePlayer
from objects import Player as LegacyPlayer
from typing import List, Union, Dict, Optional
from laserforce import Player as IPLPlayer
from shared import app
from db.models import EntityStarts, SM5Game, EntityEnds, Player, IntRole
from statistics import median
import bcrypt

async def player_from_token(game: SM5Game, token: str) -> EntityStarts:
    return await game.entity_starts.filter(entity_id=token).first()

async def get_median_role_score(player: Optional[Player]=None):
    """
    Returns a list of median scores for each role for a player.

    If player is None, returns a list of median scores for each role for all players.
    """
    data = []

    for role in range(1, 6):
        if player:
            score = median(await EntityEnds.filter(entity__entity_id=player.ipl_id, entity__role=IntRole(role), entity__sm5games__ranked=True).values_list("score", flat=True))
        else:
            score = median(await EntityEnds.filter(entity__role=IntRole(role), entity__sm5games__ranked=True).values_list("score", flat=True))
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

### BELOW IS DEPRECATED ###

sql = app.ctx.sql

async def get_players(amount: int = 100, start: int = 0) -> List[Player]:
    """
    Returns players (but not associated with rankings) from database
    """
    q = await sql.fetchall(
        "SELECT id FROM players ORDER BY id, id ASC LIMIT %s OFFSET %s",
        (amount, start)
    )
    ret = []
    for id_ in q:
        ret.append(await LegacyPlayer.from_id(id_[0]))
    return ret

async def database_player(player: IPLPlayer) -> None:
    """
    Databases a player from a `laserforce.py` `IPLPlayer`
    """
    player.id = "-".join(player.id) # convert list to str
    db_player: Player = await Player.from_player_id(player.id)

    # TODO: implement Player.update() and Player.create()
    if db_player:
        db_player.codename = player.codename
        await db_player.update()
    else:
        await db_player.create()
    return db_player

async def player_cron():
    for i in range(10000):
        try:
            player: IPLPlayer = await IPLPlayer.from_id(f"4-43-{i}")
        except LookupError:  # player does not exist
            continue

        await database_player(player)
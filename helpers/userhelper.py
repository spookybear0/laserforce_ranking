from objects import Team, Role, Player, GameType, SM5GamePlayer, LaserballGamePlayer
from laserforce import Player as IPLPlayer
from typing import List, Union, Dict
from shared import sql

async def get_total_players() -> int:
    """
    Returns total amount of players in database
    """
    q = await sql.fetchone("SELECT COUNT(*) FROM players")
    return q[0]

async def get_top(mode: GameType, amount: int = 100, start: int = 0) -> List[Player]:
    """
    Returns top players from database in given mode
    amount and start are used for pagination
    """
    mode = mode.value

    q = await sql.fetchall(
        "SELECT player_id FROM players ORDER BY %s - 3 * %s, player_id ASC LIMIT %s OFFSET %s",
        (mode + "_mu", mode + "_sigma", amount, start)
    )
    ret = []
    for player_id in q:
        ret.append(await Player.from_player_id(player_id))
    return ret

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
        ret.append(await Player.from_id(id_[0]))
    return ret

async def get_data_from_form_sm5(players: List, game_players: List, data: Dict, team: Team) -> None:
    """
    Mutates `players` and `game_players` with data from `data` sm5 mode
    """
    team_ = team.value[0] # green = "g", red = "r", blue = "b"
    for i in range(1, 8):
        try:
            player_name = data[f"{team_}name{i}"]
            player_role = data[f"{team_}role{i}"]
            player_score = data[f"{team_}score{i}"]
            if player_name == "" or player_role == "" or player_score == "":
                break
        except KeyError:
            break
        
        player = await Player.from_name(player_name)

        if not player: # player doens't exist
            raise ValueError("Invalid data!")
        
        player_id = player.player_id
        game = SM5GamePlayer(player_id, 0, team, Role(player_role), int(player_score))
        game_players.append(game)
        player.game_player = game
        players.append(player)

async def get_data_from_form_laserball(players: list, game_players: list, data: dict, team: Team):
    """
    Mutates `players` and `game_players` with data from `data` laserball mode
    """
    team_ = team.value[0] # green = "g", red = "r", blue = "b"
    for i in range(1, 8):
        try:
            player_name = data[f"{team_}name{i}"]
            player_goals = data[f"{team_}goals{i}"]
            player_assists = data[f"{team_}assists{i}"]
            player_steals = data[f"{team_}steals{i}"]
            player_clears = data[f"{team_}clears{i}"]
            player_blocks = data[f"{team_}blocks{i}"]
            if not player_name or not player_goals or not player_assists or not player_steals or not player_clears or not player_blocks:
                break
        except KeyError:
            break
        
        player = await Player.from_name(player_name)

        if not player: # player doens't exist
            raise ValueError("Invalid data!")
        
        player_id = player.player_id
        game = LaserballGamePlayer(player_id, 0, team, player_goals, player_assists, player_steals, player_clears, player_blocks)
        game_players.append(game)
        player.game_player = game
        players.append(player)

async def database_player(player: IPLPlayer) -> None:
    """
    Databases a player from a `laserforce.py` `IPLPlayer`
    """
    player.id: str = "-".join(player.id) # convert list to str
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
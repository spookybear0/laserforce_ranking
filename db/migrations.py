from db.models import Player, LegacySM5Game, LegacyLaserballGame, LegacySM5GamePlayer, LegacyLaserballGamePlayer
from shared import app
from helpers.userhelper import get_players
from helpers.gamehelper import get_all_games
from objects import GameType, Team, Role
from sanic import log

try:
    sql = app.ctx.sql
except AttributeError:
    sql = None


async def migrate_from_sql(migrate_legacy: bool = False):
    if sql is None: # if i end up removing old database support
        raise NotImplementedError("SQL not initialized")

    log.info("Running migration from legacy SQL database")

    for player in await get_players(amount=2000):
        log.debug(f"migrating player {player.id}")
        await Player.create(player_id=player.player_id, ipl_id=player.ipl_id,
                            codename=player.codename, sm5_mu=player.sm5_mu, sm5_sigma=player.sm5_sigma,
                            laserball_mu=player.laserball_mu, laserball_sigma=player.laserball_sigma,
        )

    if not migrate_legacy:
        return

    for game in await get_all_games():
        log.debug(f"migrating game {game.id}")

        if game.tdf is None:
            game.tdf = ""

        if game.type == GameType.SM5:
            g = await LegacySM5Game.create(id=game.id, winner=game.winner, tdf_name=game.tdf, timestamp=game.timestamp)

            all_players = []

            for p in game.players:
                gp = p.game_player
                p_ = await LegacySM5GamePlayer.create(player_dbid=p.id, game_dbid=game.id, team=gp.team, role=gp.role, score=gp.score)
                all_players.append(p_)

            await g.players.add(*all_players)

        elif game.type == GameType.LASERBALL:
            g = await LegacyLaserballGame.create(id=game.id, winner=game.winner, tdf_name=game.tdf, timestamp=game.timestamp)

            all_players = []

            for p in game.players:
                gp = p.game_player
                p_ = await LegacyLaserballGamePlayer.create(player_dbid=p.id, game_dbid=game.id, team=gp.team,
                                                        goals=gp.goals, assists=gp.assists, clears=gp.clears, blocks=gp.blocks,
                                                        steals=gp.steals)
                all_players.append(p_)

            await g.players.add(*all_players)
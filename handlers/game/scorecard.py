
from sanic import Request
from shared import app
from typing import List
from utils import render_template
from db.models import IntRole, SM5Game, EntityEnds, EntityStarts, SM5Stats, LaserballStats
from sanic import exceptions
from helpers.statshelper import sentry_trace


async def get_entity_end(entity):
    return await EntityEnds.filter(entity=entity).first()


async def get_sm5stats(entity):
    return await SM5Stats.filter(entity=entity).first()


async def get_laserballstats(entity):
    return await LaserballStats.filter(entity=entity).first()


def _stat_str(key: str, value: str, condition: bool = True):
    return [{"key": key, "value": value}] if condition else []


def _stat(key: str, value: int, condition: bool = True):
    return _stat_str(key, str(value), condition)


def _players_in_team(all_players: List[dict], team_index: int):
    """Returns subset of the list of players - only those in the given team."""
    return [
        player for player in all_players if player["team"] == team_index
    ]


async def _count_zaps(game: SM5Game, zapping_entity_id: str, zapped_entity_id: str) -> int:
    """Returns the number of times one entity zapped another."""
    return await (game.events.filter(
        arguments__filter={"0": zapping_entity_id}
    ).filter(
        arguments__filter={"1": " zaps "}
    ).filter(
        arguments__filter={"2": zapped_entity_id}
    ).count())


async def _count_missiles(game: SM5Game, missiling_entity_id: str, missiled_entity_id: str) -> int:
    """Returns the number of times one entity missiled another."""
    return await (game.events.filter(
        arguments__filter={"0": missiling_entity_id}
    ).filter(
        arguments__filter={"1": " missiles "}
    ).filter(
        arguments__filter={"2": missiled_entity_id}
    ).count())


@app.get("/game/<type:str>/<id:int>/scorecard/<entity_end_id:int>")
@sentry_trace
async def scorecard(request: Request, type: str, id: int, entity_end_id: int) -> str:
    if type == "sm5":
        game = await SM5Game.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Game not found")
        
        entity_end = await EntityEnds.filter(id=entity_end_id).first()

        if not entity_end:
            raise exceptions.NotFound("Scorecard not found")
        
        entity_start = await entity_end.entity
        stats = await SM5Stats.filter(entity_id=entity_start.id).first()

        can_missile = entity_start.role == IntRole.COMMANDER or entity_start.role == IntRole.HEAVY
        can_nuke = entity_start.role == IntRole.COMMANDER
        accuracy = (stats.shots_hit / stats.shots_fired) if stats.shots_fired != 0 else 0
        kd_ratio = stats.shot_opponent / stats.times_zapped if stats.times_zapped > 0 else 1

        main_stats = (
              _stat("Score", entity_end.score) +
              _stat("Lives left", stats.lives_left) +
              _stat("Shots left", stats.shots_left, entity_start.role != IntRole.AMMO) +
              _stat("Shots fired", stats.shots_fired) +
              _stat_str("Accuracy", "%.2f%%" % (accuracy * 100)) +
              _stat_str("K/D", "%.2f" % kd_ratio) +
              _stat("Missiles fired", stats.missile_hits, can_missile) +
              _stat("Missiled team", stats.missiled_team, can_missile) +
              _stat("Nukes detonated", stats.nukes_detonated, can_nuke) +
              _stat("Nukes canceled", stats.nuke_cancels, can_nuke) +
              _stat("Medic hits", stats.medic_hits)
        )

        entity_starts: List[EntityStarts] = game.entity_starts
        player_entities = [
            player for player in list(entity_starts) if player.type == "player"
        ]

        # TODO: This could be done in a single query with a nifty group_by,
        #   but group_by doesn"t seem to work well with JSON columns.

        all_players = ([
            {
                "name": player.name,
                "team": (await player.team).index,
                "entity_end_id": (await EntityEnds.filter(entity=player.id).first()).id,
                "role": player.role,
                "score": (await EntityEnds.filter(entity=player.id).first()).score,
                "you_zapped": await _count_zaps(game, entity_start.entity_id, player.entity_id),
                "zapped_you": await _count_zaps(game, player.entity_id, entity_start.entity_id),
                "you_missiled": await _count_missiles(game, entity_start.entity_id, player.entity_id),
                "missiled_you": await _count_missiles(game, player.entity_id, entity_start.entity_id),
            } for player in player_entities
        ])
        all_players.sort(key=lambda x: x["score"], reverse=True)

        teams = [
            {
                "name": "Earth Team",
                "class_name": "earth",
                "score": await game.get_green_score(),
                "players": _players_in_team(all_players, 1)
            },
            {
                "name": "Fire Team",
                "class_name": "fire",
                "score": await game.get_red_score(),
                "players": _players_in_team(all_players, 0)
            },
        ]

        return await render_template(
            request,
            "game/scorecard_sm5.html",
            game=game,
            entity_start=entity_start,
            entity_end=entity_end,
            main_stats=main_stats,
            teams=teams,
        )


from dataclasses import dataclass
from sanic import Request
from shared import app
from typing import List, Optional
from utils import render_template
from db.models import IntRole, SM5Game, EntityEnds, EntityStarts, SM5Stats, LaserballStats, LaserballGame, EventType
from helpers.statshelper import sentry_trace, _millis_to_time, count_zaps, count_missiles, count_blocks
from sanic import exceptions

def get_players_from_team(all_players: List[dict], team_index: int):
    """Returns subset of the list of players - only those in the given team."""
    return [
        player for player in all_players if player["team"] == team_index
    ]


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

        main_stats = {
            "Score": entity_end.score,
            "Lives left": stats.lives_left,
            "Shots left": stats.shots_left,
            "Shots fired": stats.shots_fired,
            "Accuracy": "%.2f%%" % (accuracy * 100),
            "K/D": "%.2f" % kd_ratio,
            "Missiles fired": stats.missile_hits,
            "Missiled team": stats.missiled_team,
            "Nukes detonated": stats.nukes_detonated,
            "Nukes canceled": stats.nuke_cancels,
            "Medic hits": stats.medic_hits,
        }

        bases_destroyed = await (game.events.filter(type=EventType.DESTROY_BASE).
                                 filter(arguments__filter={"0": entity_start.entity_id}).count())

        # Parts that make up the final score.
        # Scores taken from https://www.iplaylaserforce.com/games/space-marines-sm5/
        # TODO: rename?
        score_components = [
            {
                "name": "Missiles",
                "score": stats.missiled_opponent * 500,
                "color": "#ff23cd",
            },
            {
                "name": "Zaps",
                "score": stats.shot_opponent * 100,
                "color": "#29dc19",
            },
            {
                "name": "Bases",
                "score": bases_destroyed * 1001,
                "color": "#1284fe",
            },
            {
                "name": "Nukes",
                "score": stats.nukes_detonated * 500,
                "color": "#e98f08",
            },
        ]

        # Parts that count against the own score.
        # TODO: rename?
        negative_score_components = [
            {
                "name": "Zap own team",
                "score": stats.shot_team * 100,
                "color": "#119903",
            },
            {
                "name": "Missiled own team",
                "score": stats.missiled_team * 500,
                "color": "#880155",
            },
            {
                "name": "Got zapped",
                "score": stats.times_zapped * 20,
                "color": "#29dc19",
            },
            {
                "name": "Got missiled",
                "score": stats.times_missiled * 100,
                "color": "#ff23cd",
            },
        ]

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
                "you_zapped": await count_zaps(game, entity_start.entity_id, player.entity_id),
                "zapped_you": await count_zaps(game, player.entity_id, entity_start.entity_id),
                "you_missiled": await count_missiles(game, entity_start.entity_id, player.entity_id),
                "missiled_you": await count_missiles(game, player.entity_id, entity_start.entity_id),
            } for player in player_entities
        ])
        all_players.sort(key=lambda x: x["score"], reverse=True)

        teams = [
            {
                "name": "Earth Team",
                "class_name": "earth",
                "score": await game.get_green_score(),
                "players": get_players_from_team(all_players, 1)
            },
            {
                "name": "Fire Team",
                "class_name": "fire",
                "score": await game.get_red_score(),
                "players": get_players_from_team(all_players, 0)
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
            score_component_labels=", ".join([f"\"{component['name']}\"" for component in score_components]),
            score_component_colors=", ".join([f"\"{component['color']}\"" for component in score_components]),
            score_component_values=", ".join([str(component['score']) for component in score_components]),
            negative_score_component_labels=", ".join([f"\"{component['name']}\"" for component in negative_score_components]),
            negative_score_component_colors=", ".join([f"\"{component['color']}\"" for component in negative_score_components]),
            negative_score_component_values=", ".join([str(component['score']) for component in negative_score_components])
        )

    if type == "lb":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Game not found")

        entity_end = await EntityEnds.filter(id=entity_end_id).first()

        if not entity_end:
            raise exceptions.NotFound("Scorecard not found")

        entity_start = await entity_end.entity
        stats = await LaserballStats.filter(entity_id=entity_start.id).first()

        possession_times = await game.get_possession_times()

        accuracy = (stats.shots_hit / stats.shots_fired) if stats.shots_fired != 0 else 0

        main_stats = {
            "Score": stats['score'],
            "Shots fired": stats.shots_fired,
            "Accuracy": "%.2f%%" % (accuracy * 100),
            "Possession": _millis_to_time(possession_times.get(entity_start.entity_id)),
            "Goals": stats.goals,
            "Assists": stats.assists,
            "Passes": stats.passes,
            "Steals": stats.steals,
            "Clears": stats.clears,
            "Blocks": stats.blocks,
        }

        entity_starts: List[EntityStarts] = game.entity_starts
        player_entities = [
            player for player in list(entity_starts) if player.type == "player"
        ]

        player_stats = {
            player.id: await LaserballStats.filter(entity_id=player.id).first() for player in player_entities
        }

        all_players = ([
            {
                "name": player['name'],
                "team": (await player.team).index,
                "entity_end_id": (await EntityEnds.filter(entity=player.id).first()).id,
                "score": player_stats[player.id]['score'],
                "ball_possession": _millis_to_time(possession_times.get(player.entity_id, 0)),
                "you_blocked": await count_blocks(game, entity_start.entity_id, player.entity_id),
                "blocked_you": await count_blocks(game, player.entity_id, entity_start.entity_id),
                "blocks": player_stats[player.id].blocks,
                "goals": player_stats[player.id].goals,
                "passes": player_stats[player.id].passes,
                "clears": player_stats[player.id].clears,
                "steals": player_stats[player.id].steals,
                "assists": player_stats[player.id].assists,
            } for player in player_entities
        ])
        all_players.sort(key=lambda x: x["score"], reverse=True)

        teams = [
            {
                "name": "Ice Team",
                "class_name": "ice",
                "score": await game.get_blue_score(),
                "players": get_players_from_team(all_players, 1)
            },
            {
                "name": "Fire Team",
                "class_name": "fire",
                "score": await game.get_red_score(),
                "players": get_players_from_team(all_players, 0)
            },
        ]

        return await render_template(
            request,
            "game/scorecard_laserball.html",
            game=game,
            entity_start=entity_start,
            entity_end=entity_end,
            main_stats=main_stats,
            teams=teams,
        )



from numpy import arange
from sanic import Request

from helpers.gamehelper import SM5_STATE_COLORS, get_players_from_team
from helpers.sm5helper import get_sm5_player_stats
from helpers.tooltips import TOOLTIP_INFO
from shared import app
from typing import List
from utils import render_template
from db.types import IntRole, Team, LineChartData, RgbColor
from db.sm5 import SM5Game
from db.game import EntityEnds, EntityStarts
from db.laserball import LaserballGame, LaserballStats
from helpers.statshelper import sentry_trace, millis_to_time, count_blocks, \
    get_sm5_single_player_score_graph_data
from sanic import exceptions


# Modifiers for the score card colors of other players. One of these will be applied
# to the color so it's ever so slightly different.
_RGB_MODIFIERS = [RgbColor(0, 0, 16), RgbColor(0, 16, 0), RgbColor(16, 0, 0)]


def _chart_values(values: list[int]) -> str:
    """Creates a string to be used in JavaScript for a list of integers."""
    return "[%s]" % ", ".join([str(value) for value in values])


def _get_score_chart_color(player_id: int, scorecard_player_id: int, team: Team, index: int) -> str:
    # If it's the player this score card is for, use the proper color:
    if scorecard_player_id == player_id:
        return team.css_color_name

    # Use the dim color, but slightly change it based on index so they don't all look the
    # same.
    modifier = _RGB_MODIFIERS[index % 3].multiply(int(index / 3))
    return team.dim_color.add(modifier).rgb_value


def _chart_strings(values: list[str]) -> str:
    """Creates a string to be used in JavaScript for a list of strings.

    Note that this will not escape the strings - they should not contain any double quotes."""
    return "[%s]" % ", ".join(f"\"{value}\"" for value in values)


@app.get("/game/<type:str>/<id:int>/scorecard/<entity_end_id:int>")
@sentry_trace
async def scorecard(request: Request, type: str, id: int, entity_end_id: int) -> str:
    if type == "sm5":
        game = await SM5Game.filter(id=id).prefetch_related("entity_starts", "entity_ends").first()

        if not game:
            raise exceptions.NotFound("Game not found")

        entity_end = await EntityEnds.filter(id=entity_end_id).first()

        if not entity_end:
            raise exceptions.NotFound("Scorecard not found")

        entity_start = await entity_end.entity

        if not entity_start:
            raise exceptions.NotFound("Scorecard not found")

        full_stats = await get_sm5_player_stats(game, entity_start)

        if entity_end_id not in full_stats.all_players:
            raise exceptions.NotFound("Scorecard not found")

        player_stats = full_stats.all_players[entity_end_id]

        can_missile = player_stats.role == IntRole.COMMANDER or player_stats.role == IntRole.HEAVY
        can_nuke = player_stats.role == IntRole.COMMANDER

        main_stats = {
            "Score": player_stats.score,
            "Lives left": player_stats.lives_left,
            "Shots left": player_stats.shots_left,
            "Shots fired": player_stats.shots_fired,
            "Accuracy": "%.2f%%" % (player_stats.accuracy * 100),
            "K/D": "%.2f" % player_stats.kd_ratio,
            "Missiles fired": player_stats.missile_hits,
            "Missiled team": player_stats.missiled_team,
            "Nukes detonated": player_stats.nukes_detonated,
            "Nukes canceled": player_stats.nuke_cancels,
            "Medic hits": player_stats.medic_hits,
        }

        score_composition = [
            {
                "name": component,
                "color": "#00cc00" if score > 0 else "#dd0000",
                "score": score,
            }
            for component, score in player_stats.score_components.items() if score != 0
        ]

        score_composition.sort(key=lambda x: x["score"], reverse=True)

        state_distribution_labels = list(player_stats.state_distribution.keys())
        state_distribution_values = list(player_stats.state_distribution.values())
        state_distribution_colors = [SM5_STATE_COLORS[state] for state in player_stats.state_distribution.keys()]

        score_chart_data = [
            LineChartData(
                label=player.name,
                color=_get_score_chart_color(player.entity_start.id, entity_start.id, player.team, index),
                data=await get_sm5_single_player_score_graph_data(game, player.entity_start.id),
                borderWidth=6 if entity_start.id == player.entity_start.id else 3
            ) for index, player in enumerate(full_stats.all_players.values())
        ]

        return await render_template(
            request,
            "game/scorecard_sm5.html",
            game=game,
            entity_start=entity_start,
            entity_end=entity_end,
            main_stats=main_stats,
            teams=full_stats.teams,
            score_composition_labels=", ".join([f"\"{component['name']}\"" for component in score_composition]),
            score_composition_colors=", ".join([f"\"{component['color']}\"" for component in score_composition]),
            score_composition_values=", ".join([str(component['score']) for component in score_composition]),
            state_distribution_labels=_chart_strings(state_distribution_labels),
            state_distribution_values=_chart_values(state_distribution_values),
            state_distribution_colors=_chart_strings(state_distribution_colors),
            score_chart_labels=[t for t in arange(0, 900000 // 1000 // 60 + 0.5, 0.5)],
            score_chart_data=score_chart_data,
            tooltip_info=TOOLTIP_INFO,
        )

    if type == "laserball":
        game = await LaserballGame.filter(id=id).prefetch_related("entity_starts").first()

        if not game:
            raise exceptions.NotFound("Game not found")

        entity_end = await EntityEnds.filter(id=entity_end_id).first()

        if not entity_end:
            raise exceptions.NotFound("Scorecard not found")

        entity_start = await entity_end.entity
        stats = await LaserballStats.filter(entity_id=entity_start.id).first()

        if not stats:
            raise exceptions.NotFound("Scorecard not found")

        possession_times = await game.get_possession_times()

        accuracy = (stats.shots_hit / stats.shots_fired) if stats.shots_fired != 0 else 0

        main_stats = {
            "Score": stats.score,
            "Shots fired": stats.shots_fired,
            "Accuracy": "%.2f%%" % (accuracy * 100),
            "Possession": millis_to_time(possession_times.get(entity_start.entity_id)),
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
                "name": player.name,
                "team": (await player.team).index,
                "entity_end_id": (await EntityEnds.filter(entity=player.id).first()).id,
                "score": player_stats[player.id].score,
                "ball_possession": millis_to_time(possession_times.get(player.entity_id, 0)),
                "you_blocked": await count_blocks(game, entity_start.entity_id, player.entity_id),
                "blocked_you": await count_blocks(game, player.entity_id, entity_start.entity_id),
                "mvp_points": "%.2f" % player_stats[player.id].mvp_points,
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
                "score": await game.get_team_score(Team.BLUE),
                "players": get_players_from_team(all_players, 1)
            },
            {
                "name": "Fire Team",
                "class_name": "fire",
                "score": await game.get_team_score(Team.RED),
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



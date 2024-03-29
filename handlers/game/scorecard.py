from numpy import arange
from sanic import Request

from helpers.formattinghelper import create_ratio_string
from helpers.gamehelper import SM5_STATE_LABEL_MAP, SM5_STATE_COLORS, get_players_from_team
from shared import app
from typing import List
from utils import render_template
from db.types import IntRole, EventType, PlayerStateDetailType, Team
from db.sm5 import SM5Game, SM5Stats
from db.game import EntityEnds, EntityStarts
from db.laserball import LaserballGame, LaserballStats
from helpers.statshelper import sentry_trace, _millis_to_time, count_zaps, count_missiles, count_blocks, \
    get_player_state_distribution, get_sm5_score_components, get_sm5_kd_ratio, get_sm5_single_player_score_graph_data, \
    get_sm5_player_alive_times, get_player_state_distribution_pie_chart
from sanic import exceptions


def _chart_values(values: list[int]) -> str:
    """Creates a string to be used in JavaScript for a list of integers."""
    return "[%s]" % ", ".join([str(value) for value in values])



def _calc_ratio(numerator: int, divisor: int) -> float:
    return float(numerator) / float(divisor) if divisor else 0.0


def _chart_strings(values: list[str]) -> str:
    """Creates a string to be used in JavaScript for a list of strings.

    Note that this will not escape the strings - they should not contain any double quotes."""
    return "[%s]" % ", ".join(f"\"{value}\"" for value in values)


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

        if not stats:
            raise exceptions.NotFound("Scorecard not found")

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

        score_components = await get_sm5_score_components(game, stats, entity_start)

        score_composition = [
            {
                "name": component,
                "color": "#00cc00" if score > 0 else "#dd0000",
                "score": score,
            }
            for component, score in score_components.items() if score != 0
        ]

        score_composition.sort(key=lambda x: x["score"], reverse=True)

        state_distribution = await get_player_state_distribution(entity_start, entity_end, game.player_states, game.events,
                                                                 SM5_STATE_LABEL_MAP)

        state_distribution_labels = list(state_distribution.keys())
        state_distribution_values = list(state_distribution.values())
        state_distribution_colors = [SM5_STATE_COLORS[state] for state in state_distribution.keys()]

        entity_starts: List[EntityStarts] = game.entity_starts
        player_entities = [
            player for player in list(entity_starts) if player.type == "player"
        ]

        player_entity_ends = {
            player.id: await EntityEnds.filter(entity=player.id).first() for player in player_entities
        }

        player_sm5_stats = {
            player.id: await SM5Stats.filter(entity_id=player.id).first() for player in player_entities
        }

        game_duration = await game.get_actual_game_duration()

        for player in player_entities:
            if player.id not in player_sm5_stats or player_sm5_stats.get(player.id) is None:
                raise exceptions.NotFound("Player stats not found")

        all_players = ([
            {
                "name": player.name,
                "team": (await player.team).index,
                "entity_end_id": player_entity_ends[player.id].id,
                "role": player.role,
                "css_class": "player%s%s" % (" active_player" if player.id == entity_start.id else "",
                                             " eliminated_player" if player_sm5_stats[player.id] or player_sm5_stats[player.id].lives_left == 0 else ""),
                "score": player_entity_ends[player.id].score,
                "lives_left": player_sm5_stats[player.id].lives_left if player.id in player_sm5_stats else "",
                "time_in_game_values": get_sm5_player_alive_times(game_duration, player_entity_ends[player.id]),
                "kd_ratio": ("%.2f" % get_sm5_kd_ratio(player_sm5_stats[player.id])) if player.id in player_sm5_stats else "",
                "mvp_points": "%.2f" % await player_sm5_stats[player.id].mvp_points(),
                "you_zapped": await count_zaps(game, entity_start.entity_id, player.entity_id),
                "zapped_you": await count_zaps(game, player.entity_id, entity_start.entity_id),
                "hit_ratio": create_ratio_string(_calc_ratio(await count_zaps(game, entity_start.entity_id, player.entity_id), await count_zaps(game, player.entity_id, entity_start.entity_id))),
                "you_missiled": await count_missiles(game, entity_start.entity_id, player.entity_id),
                "missiled_you": await count_missiles(game, player.entity_id, entity_start.entity_id),
                "state_distribution": get_player_state_distribution_pie_chart(await get_player_state_distribution(player, player_entity_ends[player.id],
                                                                              game.player_states, game.events, SM5_STATE_LABEL_MAP), SM5_STATE_COLORS)
            } for player in player_entities
        ])
        all_players.sort(key=lambda x: x["score"], reverse=True)

        teams = [
            {
                "name": "Earth Team",
                "class_name": "earth",
                "score": await game.get_team_score(Team.GREEN),
                "players": get_players_from_team(all_players, 1)
            },
            {
                "name": "Fire Team",
                "class_name": "fire",
                "score": await game.get_team_score(Team.RED),
                "players": get_players_from_team(all_players, 0)
            },
        ]

        score_chart_data = await get_sm5_single_player_score_graph_data(game, entity_start.id)

        return await render_template(
            request,
            "game/scorecard_sm5.html",
            game=game,
            entity_start=entity_start,
            entity_end=entity_end,
            main_stats=main_stats,
            teams=teams,
            score_composition_labels=", ".join([f"\"{component['name']}\"" for component in score_composition]),
            score_composition_colors=", ".join([f"\"{component['color']}\"" for component in score_composition]),
            score_composition_values=", ".join([str(component['score']) for component in score_composition]),
            state_distribution_labels=_chart_strings(state_distribution_labels),
            state_distribution_values=_chart_values(state_distribution_values),
            state_distribution_colors=_chart_strings(state_distribution_colors),
            score_chart_labels=[t for t in arange(0, 900000//1000//60+0.5, 0.5)],
            score_chart_data=score_chart_data
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
                "name": player.name,
                "team": (await player.team).index,
                "entity_end_id": (await EntityEnds.filter(entity=player.id).first()).id,
                "score": player_stats[player.id].score,
                "ball_possession": _millis_to_time(possession_times.get(player.entity_id, 0)),
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



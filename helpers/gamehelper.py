"""Various constants and helpers when displaying stats about individual games.

This is different from statshelper in that it does not calculate stats, it
only deals with getting and extracting and visualizing data.
"""
from collections import defaultdict
from typing import List, Dict

from sanic import exceptions

from db.game import EntityStarts, EntityEnds, PlayerInfo
from db.types import PlayerStateDetailType, Team

"""Map of every possible player state and the display name for it in SM5 games.

Multiple player states map to the same name since they're intended to be lumped
together - in SM5, we don't care if a player is down because of a nuke or a
missile.
"""
SM5_STATE_LABEL_MAP = {
    PlayerStateDetailType.ACTIVE: "Active",
    PlayerStateDetailType.DOWN_ZAPPED: "Down",
    PlayerStateDetailType.DOWN_MISSILED: "Down",
    PlayerStateDetailType.DOWN_NUKED: "Down",
    PlayerStateDetailType.DOWN_FOR_OTHER: "Down",
    PlayerStateDetailType.DOWN_FOR_RESUP: "Down (Resup)",
    PlayerStateDetailType.RESETTABLE: "Resettable",
}

"""Map of every SM5 player state and the color to use when visualizing it.

All keys in this dict map to values in SM5_STATE_LABEL_MAP."""
SM5_STATE_COLORS = {
    "Active": "#11dd11",
    "Down": "#993202",
    "Down (Resup)": "#8702ab",
    "Resettable": "#cbd103",
}


def get_players_from_team(all_players: List[dict], team_index: int) -> List[dict]:
    """Returns subset of the list of players - only those in the given team.

    Each player object is a dict that has a "team" member with a team_index.
    """
    return [
        player for player in all_players if player["team"] == team_index
    ]


async def get_team_rosters(entity_starts: List[EntityStarts], entity_ends: List[EntityEnds]) -> dict[
    Team, List[PlayerInfo]]:
    """Returns a dict with each team and a list of players in each.

    Non-player entities will be ignored. The values will be a list of names, either the
    name if the player is not logged in, or the entity ID if the player is logged in.

    Players without a matching entity_end will not be added.
    """
    result = defaultdict(list)

    entity_ends_dict = {
        (await entity.entity).id: entity for entity in entity_ends
    }

    for player in entity_starts:
        if player.type != "player":
            continue

        player_team = (await player.team).enum
        team_roster = result[player_team]

        entity_end = entity_ends_dict[player.id] if player.id in entity_ends_dict else None
        display_name = player.name if player.entity_id.startswith("@") else player.entity_id

        if entity_end:
            team_roster.append(PlayerInfo(entity_start=player, entity_end=entity_end, display_name=display_name))

    return result


def get_player_display_names(players: List[PlayerInfo]) -> List[str]:
    """Extracts all the display names from a list of players."""
    return [player.display_name for player in players]


def get_matchmaking_teams(team_rosters: Dict[Team, List[PlayerInfo]]) -> (
    List[str], List[str]):
    """Returns display names for each player in both teams.

    The first returned list will always be the red team unless there is no red
    team. The second one will be the other team.

    Args:
        team_rosters: All teams and their players, as returned by
            get_team_rosters().
    """
    if len(team_rosters.keys()) < 2:
        raise exceptions.ServerError("Game has fewer than two teams in it")

    team1, team2 = iter(team_rosters.keys())

    if Team.RED in team_rosters:
        players_matchmake_team1 = get_player_display_names(team_rosters[Team.RED])

        # Pick whichever other team there is to be the other one.
        other_team = team2 if team1 == Team.RED else team1
        players_matchmake_team2 = get_player_display_names(team_rosters[other_team])
    else:
        # We shouldn't have an SM5 game where red doesn't play, but maybe
        # somebody messed with the game editor.
        players_matchmake_team1 = get_player_display_names(team_rosters[team1])
        players_matchmake_team2 = get_player_display_names(team_rosters[team2])

    return players_matchmake_team1, players_matchmake_team2

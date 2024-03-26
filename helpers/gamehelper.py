"""Various constants and helpers when displaying stats about individual games.

This is different from statshelper in that it does not calculate stats, it
only deals with getting and extracting and visualizing data.
"""
from typing import List

from db.types import PlayerStateDetailType

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
    """Returns subset of the list of players - only those in the given team."""
    return [
        player for player in all_players if player["team"] == team_index
    ]

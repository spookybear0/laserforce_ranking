from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ReplayCellChange:
    # Name of the row this update is for.
    row_id: str

    column: int

    # The new value for this particular cell.
    new_value: str


@dataclass
class ReplayRowChange:
    # Name of the row this update is for.
    row_id: str

    # The new CSS class for this row.
    new_css_class: str


@dataclass
class ReplayEvent:
    # The time at which this event happened.
    timestamp_millis: int

    # The message to show in the scrolling event box. With HTML formatting.
    message: str

    cell_changes: List[ReplayCellChange]

    row_changes: List[ReplayRowChange]


@dataclass
class ReplayPlayer:
    # The innerHTML for each column.
    cells: List[str]

    # The row identifier, will be used in the ID of each row and cell.
    row_id: str


@dataclass
class ReplayTeam:
    # Display name for the team.
    name: str

    # CSS class to use for the team.
    css_class: str

    # A list of all players.
    players: List[ReplayPlayer]


@dataclass
class Replay:
    events: List[ReplayEvent]

    teams: List[ReplayTeam]

    # Names of the columns in each team table.
    column_headers: List[str]

    # Export this entire replay to JavaScript code.
    def export_to_js(self) -> str:
        result = ""

        for column in self.column_headers:
            result += f"add_column('{column}');\n"

        for team in self.teams:
            result += f"add_team('{team.name}');\n"

            for player in team.players:
                result += f"add_player({player.cells});\n"

        result += "events = [\n"
        for events in self.events:
            result += f"  {events.timestamp_millis},'{events.message}'"

        return result

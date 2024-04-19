from dataclasses import dataclass
from typing import List


def _escape_string(text: str) -> str:
    return text.replace("'", "\\'")


@dataclass
class ReplayCellChange:
    # Name of the row this update is for.
    row_id: str

    column: int

    # The new value for this particular cell.
    new_value: str

    def to_js_string(self):
        return f'["{self.row_id}",{self.column},"{self.new_value}"]'


@dataclass
class ReplayRowChange:
    # Name of the row this update is for.
    row_id: str

    # The new CSS class for this row.
    new_css_class: str

    def to_js_string(self):
        return f'["{self.row_id}","{self.new_css_class}"]'


@dataclass
class ReplaySound:
    # List of possible assets to use for this sound.
    asset_urls: List[str]

    # ID to identify this sound.
    id: int = 0


@dataclass
class ReplayEvent:
    # The time at which this event happened.
    timestamp_millis: int

    # The message to show in the scrolling event box. With HTML formatting.
    message: str

    # Scores for all teams, or empty if nothing has changed.
    team_scores: List[int]

    cell_changes: List[ReplayCellChange]

    row_changes: List[ReplayRowChange]

    sounds: List[ReplaySound]


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

    # ID for the table.
    id: str

    # A list of all players.
    players: List[ReplayPlayer]


@dataclass
class Replay:
    events: List[ReplayEvent]

    teams: List[ReplayTeam]

    sounds: List[ReplaySound]

    # Names of the columns in each team table.
    column_headers: List[str]

    # Export this entire replay to JavaScript code.
    def export_to_js(self) -> str:
        result = ""

        for column in self.column_headers:
            result += f"add_column('{column}');\n"

        for sound in self.sounds:
            result += f"register_sound({sound.id}, {sound.asset_urls});\n"

        for team in self.teams:
            result += f"add_team('{team.name}', '{team.id}', '{team.css_class}');\n"

            for player in team.players:
                cells = [_escape_string(cell) for cell in player.cells]
                result += f"add_player('{team.id}', '{player.row_id}', {cells});\n"

        result += "events = [\n"
        for event in self.events:
            cell_changes = [cell_change.to_js_string() for cell_change in event.cell_changes]
            row_changes = [row_change.to_js_string() for row_change in event.row_changes]
            sound_ids = [sound.id for sound in event.sounds]
            result += f"  [{event.timestamp_millis},'{_escape_string(event.message)}',[{','.join(cell_changes)}],[{','.join(row_changes)}],{event.team_scores},{sound_ids}],\n"

        result += "];\n\n"

        result += """
            document.addEventListener("DOMContentLoaded", function() {
                startReplay();
            });
            """

        return result

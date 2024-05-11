from dataclasses import dataclass
from typing import List, Optional


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
    id: int

    # Preload priority. Sounds with the highest priority preload first.
    priority: int = 0

    # If true, this sound must be loaded before playback can begin.
    required: bool = False


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

    # If there are sounds, their stereo balance should be here (-1=left, 0=center, 1=right).
    sound_stereo_balance: float = 0.0


@dataclass
class ReplayPlayer:
    # The innerHTML for each column.
    cells: List[str]

    # The row identifier, will be used in the ID of each row and cell.
    row_id: str

    # CSS class to initially use for this player.
    css_class: str


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

    # Sound to play before the replay starts
    intro_sound: Optional[ReplaySound]

    # Sound to play when the actual game starts, after the intro sound
    start_sound: Optional[ReplaySound]

    # Names of the columns in each team table.
    column_headers: List[str]

    # If not empty, the tables should be sorted by these column, in order of significance.
    sort_columns_index: List[int]

    # Export this entire replay to JavaScript code.
    def export_to_js(self) -> str:
        result = ""

        for column in self.column_headers:
            result += f"addColumn('{column}');\n"

        for sound in self.sounds:
            result += f"registerSound({sound.id}, {sound.asset_urls}, {sound.priority}, {str(sound.required).lower()});\n"

        # Load the sounds in order of priority.
        if self.sounds:
            highest_priority = max([sound.priority for sound in self.sounds])

            result += "let sound_promise = Promise.resolve();\n"

            while highest_priority >= 0:
                sounds = [sound for sound in self.sounds if sound.priority == highest_priority]

                if sounds:
                    for sound in sounds:
                        result += f"loadSound({sound.id});\n"

                highest_priority -= 1

        for team in self.teams:
            result += f"addTeam('{team.name}', '{team.id}', '{team.css_class}');\n"

            for player in team.players:
                result += f"addPlayer('{team.id}', '{player.row_id}', '{player.css_class}');\n"

        result += "function resetPlayers() {\n"
        result += "  player_values = {\n"

        for team in self.teams:
            for player in team.players:
                for index, cell in enumerate(player.cells):
                    result += f"    '{player.row_id}_{index}': '{_escape_string(cell)}',\n"
        result += """
          };
          Object.entries(player_values).forEach(([cell, value]) => {
            document.getElementById(cell).innerHTML = value;
          });
        }
        
        resetPlayers();
        """

        result += f"setSortColumns({self.sort_columns_index});\n"

        if self.intro_sound:
            result += f"setIntroSound({self.intro_sound.id});\n"

        if self.start_sound:
            result += f"setStartSound({self.start_sound.id});\n"

        result += "events = [\n"
        for event in self.events:
            cell_changes = [cell_change.to_js_string() for cell_change in event.cell_changes]
            row_changes = [row_change.to_js_string() for row_change in event.row_changes]
            sound_ids = [sound.id for sound in event.sounds]
            result += (f"  [{event.timestamp_millis},'{_escape_string(event.message)}',[{','.join(cell_changes)}],"
                       f"[{','.join(row_changes)}],{event.team_scores},{event.sound_stereo_balance},{sound_ids}],\n")

        result += "];\n\n"

        result += """
            document.addEventListener("DOMContentLoaded", function() {
                checkPendingAssets();
            });
            """

        return result

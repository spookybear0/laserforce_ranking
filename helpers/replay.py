from dataclasses import dataclass
from typing import List, Optional

from db.game import Events, Teams, PlayerInfo
from db.types import EventType, Team


def _escape_string(text: str) -> str:
    return text.replace("'", "\\'")


@dataclass
class ReplayCellChange:
    """Describes a cell in a team table being changed."""
    # Name of the row this update is for.
    row_id: str

    column: int

    # The new value for this particular cell.
    new_value: str

    def to_js_string(self):
        return f'["{self.row_id}",{self.column},"{self.new_value}"]'


@dataclass
class ReplayRowChange:
    """Describes a row in a team table being changed (typically its CSS class)."""
    # Name of the row this update is for.
    row_id: str

    # The new CSS class for this row.
    new_css_class: str

    def to_js_string(self):
        return f'["{self.row_id}","{self.new_css_class}"]'


@dataclass
class ReplaySound:
    """Describes a sound that may be used during a replay.

    One sound may comprise multiple sound assets that are chosen randomly.
    """
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
    """Describes a single event during the replay."""
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
    """Describes a player """
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


@dataclass
class PlayerState:
    """Representation of the current state of a player as the replay events are being generated."""
    row_index: int
    row_id: str
    team: Team
    name: str
    downed: bool

    def __hash__(self):
        return self.row_index


class ReplayGenerator:
    """Base class for a gametype-specific replay generator."""

    def __init__(self):
        self.teams = {}
        self.team_scores = dict[Team, int]()
        self.team_sound_balance = dict[Team, float]()
        self.team_rosters = dict[Team, List[PlayerInfo]]()

        self.entity_id_to_player = dict[str, str]()
        self.entity_id_to_nonplayer_name = dict[str, str]()

        self.events = []
        self.cell_changes = []
        self.row_changes = []
        self.entity_starts = []

        # Map from a player and the timestamp at which the player will be back up. The key is the _Player object.
        self.player_reup_times = dict[PlayerState, int]()

        self.sounds = []
        self.stereo_balance = 0.0

    async def generate(self, game) -> Replay:
        pass

    def init_teams(self):
        self.entity_id_to_nonplayer_name = {
            entity.entity_id: entity.name for entity in self.entity_starts if entity.entity_id[0] == "@"
        }

    def process_events(self, events: List[Events], event_handler):
        for event in events:
            timestamp = event.time
            old_team_scores = self.team_scores.copy()

            # Before we process the event, let's see if there's a player coming back up. Look up all the timestamps when
            # someone is coming back up.
            players_reup_timestamps = [
                reup_timestamp for reup_timestamp in self.player_reup_times.values() if reup_timestamp < timestamp
            ]

            if players_reup_timestamps:
                # Create events for all the players coming back up one by one.
                players_reup_timestamps.sort()

                row_changes = []

                # Walk through them in order. It's likely that there are multiple players with identical timestamps
                # (like after a nuke in SM5), so we can't use a dict here.
                for reup_timestamp in players_reup_timestamps:
                    # Find the first player with this particular timestamp. There may be multiple after a nuke. But who
                    # cares. We'll eventually get them one by one.
                    for player, player_reup_timestamp in self.player_reup_times.items():
                        if player_reup_timestamp == reup_timestamp:
                            self.player_reup_times.pop(player)
                            row_changes.append(ReplayRowChange(player.row_id, player.team.css_class))
                            player.downed = False
                            break

                    # Create a dummy event to update the UI.
                    self.events.append(
                        ReplayEvent(reup_timestamp, "", cell_changes=[], row_changes=row_changes, team_scores=[],
                                    sounds=[]))

            # Translate the arguments of the event into HTML if they reference entities.
            message = ""

            # Note that we don't care about players missing.
            if event.type != EventType.MISS:
                for argument in event.arguments:
                    if argument[0] == "@":
                        message += self.create_entity_reference(argument)
                    elif argument[0] == '#':
                        message += self.create_entity_reference(argument)
                    else:
                        message += argument

            player1 = None
            player2 = None

            if event.arguments[0] in self.entity_id_to_player:
                player1 = self.entity_id_to_player[event.arguments[0]]

            if len(event.arguments) > 2 and event.arguments[2] in self.entity_id_to_player:
                player2 = self.entity_id_to_player[event.arguments[2]]

            self.row_changes = []
            self.cell_changes = []
            self.sounds = []

            self.handle_event(event, player1, player2)

            if self.team_scores == old_team_scores:
                new_team_scores = []
            else:
                new_team_scores = [
                    self.team_scores[team] for team in self.team_rosters.keys()
                ]

            replay_event = ReplayEvent(timestamp_millis=timestamp, message=message, cell_changes=self.cell_changes,
                                       row_changes=self.row_changes, team_scores=new_team_scores, sounds=self.sounds,
                                       sound_stereo_balance=self.stereo_balance)

            self.events.append(replay_event)

    def add_sound(self, sound, team: Teams):
        self.sounds.append(sound)
        self.stereo_balance = self.team_sound_balance[team]

    def handle_event(self, event: Events, player1, player2) -> ReplayEvent:
        pass

    def create_entity_reference(self, argument: str) -> str:
        if argument in self.entity_id_to_nonplayer_name:
            return self.entity_id_to_nonplayer_name[argument]

        player = self.entity_id_to_player[argument]
        css_class = player.team.css_class
        return f'<span class="{css_class}">{player.name}</span>'

from dataclasses import dataclass
from typing import List, Dict

from db.laserball import LaserballGame
from db.types import EventType, Team
from helpers.gamehelper import get_team_rosters
from helpers.replay import Replay, ReplayTeam, ReplayPlayer, ReplayEvent, ReplayCellChange, \
    ReplayRowChange


@dataclass
class _Player:
    row_index: int
    row_id: str
    team: Team
    name: str
    downed: bool = False
    goals: int = 0
    assists: int = 0
    steals: int = 0
    clears: int = 0
    passes: int = 0
    blocks: int = 0
    score: int = 0
    total_shots_fired: int = 0
    total_shots_hit: int = 0

    def __hash__(self):
        return self.row_index


_GOALS_COLUMN = 1
_ASSISTS_COLUMN = 2
_STEALS_COLUMN = 3
_CLEARS_COLUMN = 4
_PASSES_COLUMN = 5
_BLOCKS_COLUMN = 6
_ACCURACY_COLUMN = 7

_EVENTS_SUCCESSFUL_HITS = {
    EventType.PASS,
    EventType.GOAL,
    EventType.STEAL,
    EventType.BLOCK,
    EventType.CLEAR,
}

_EVENTS_INVOLVING_SHOTS = {
    EventType.MISS,
    EventType.MISS_BASE,
    EventType.PASS,
    EventType.GOAL,
    EventType.STEAL,
    EventType.BLOCK,
    EventType.CLEAR,
}

_EVENTS_DOWNING_PLAYER = {
    EventType.STEAL,
    EventType.BLOCK,
}

_AUDIO_PREFIX = "/assets/laserball/audio/"


@dataclass
class _Team:
    players: List[_Player]


async def create_laserball_replay(game: LaserballGame) -> Replay:
    entity_starts = await game.entity_starts.all()
    team_rosters = await get_team_rosters(entity_starts,
                                          await game.entity_ends.all())
    # Set up the teams and players.
    column_headers = ["Codename", "Goals", "Assists", "Steals", "Clears", "Passes", "Blocks", "Accuracy"]

    replay_teams = []
    entity_id_to_player = {}
    row_index = 1

    teams = {}
    team_scores = {}
    team_goals = {}
    team_sound_balance = {}

    entity_id_to_nonplayer_name = {
        entity.entity_id: entity.name for entity in entity_starts if entity.entity_id[0] == "@"
    }

    sound_balance = -0.5

    for team, players in team_rosters.items():
        replay_player_list = []
        players_in_team = []
        team_scores[team] = 0
        team_goals[team] = 0
        team_sound_balance[team] = sound_balance
        sound_balance += 1.0

        if sound_balance > 1.0:
            sound_balance -= 2.0

        for player_info in players:
            cells = [player_info.display_name, "0", "0", "0", "0", "0", "0", ""]
            row_id = f"r{row_index}"

            player = _Player(row_index=row_index,
                             row_id=row_id, team=team, name=player_info.display_name)

            replay_player_list.append(ReplayPlayer(cells=cells, row_id=row_id))
            row_index += 1

            entity_id_to_player[player_info.entity_start.entity_id] = player
            players_in_team.append(player)

        replay_team = ReplayTeam(name=team.name, css_class=team.css_class, id=f"{team.element.lower()}_team",
                                 players=replay_player_list)
        replay_teams.append(replay_team)
        teams[team] = players_in_team

    events = []

    # Map from a player and the timestamp at which the player will be back up. The key is the _Player object.
    player_reup_times = {}

    # Now let's walk through the events one by one and translate them into UI events.
    for event in await game.events.all():

        timestamp = event.time
        old_team_goals = team_goals.copy()
        sounds = []
        stereo_balance = 0.0

        # Before we process the event, let's see if there's a player coming back up. Look up all the timestamps when
        # someone is coming back up.
        players_reup_timestamps = [
            reup_timestamp for reup_timestamp in player_reup_times.values() if reup_timestamp < timestamp
        ]

        if players_reup_timestamps:
            # Create events for all the players coming back up one by one.
            players_reup_timestamps.sort()

            row_changes = []

            # Walk through them in order. It's likely that there are multiple players with identical timestamps (usually
            # after a nuke), so we can't use a dict here.
            for reup_timestamp in players_reup_timestamps:
                # Find the first player with this particular timestamp. There may be multiple after a nuke. But who
                # cares. We'll eventually get them one by one.
                for player, player_reup_timestamp in player_reup_times.items():
                    if player_reup_timestamp == reup_timestamp:
                        player_reup_times.pop(player)
                        row_changes.append(ReplayRowChange(player.row_id, player.team.css_class))
                        break

                # Create a dummy event to update the UI.
                events.append(ReplayEvent(reup_timestamp, "", cell_changes=[], row_changes=row_changes, team_scores=[],
                                          sounds=[]))

        # Translate the arguments of the event into HTML if they reference entities.
        message = ""

        # Note that we don't care about players missing.
        if event.type != EventType.MISS:
            for argument in event.arguments:
                if argument[0] == "@":
                    message += _create_entity_reference(argument, entity_id_to_player, entity_id_to_nonplayer_name)
                elif argument[0] == '#':
                    message += _create_entity_reference(argument, entity_id_to_player, entity_id_to_nonplayer_name)
                else:
                    message += argument

        cell_changes = []
        row_changes = []
        player1 = None
        player2 = None

        if event.arguments[0] in entity_id_to_player:
            player1 = entity_id_to_player[event.arguments[0]]

        if len(event.arguments) > 2 and event.arguments[2] in entity_id_to_player:
            player2 = entity_id_to_player[event.arguments[2]]

        # Count successful hits.
        if event.type in _EVENTS_SUCCESSFUL_HITS:
            player1.total_shots_hit += 1

        # Count shots. This must be done after counting hits so we can get the right accuracy.
        if event.type in _EVENTS_INVOLVING_SHOTS:
            player1.total_shots_fired += 1
            cell_changes.append(ReplayCellChange(row_id=player1.row_id, column=_ACCURACY_COLUMN,
                                                 new_value="%.2f%%" % (
                                                         player1.total_shots_hit * 100 / player1.total_shots_fired)))

        # Handle each event.
        match event.type:
            case EventType.BLOCK:
                _add_score(player1, 1, cell_changes, team_scores)
                _add_blocks(player1, 1, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.PASS:
                _add_score(player1, 1, cell_changes, team_scores)
                _add_passes(player1, 1, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.STEAL:
                _add_score(player1, 100, cell_changes, team_scores)
                _add_steals(player1, 1, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.GOAL:
                _add_score(player1, 10000, cell_changes, team_scores)
                _add_goals(player1, 1, cell_changes)
                stereo_balance = team_sound_balance[player1.team]
                team_goals[player1.team] += 1
                #sounds.append(downed_audio)

            case EventType.ASSIST:
                _add_score(player1, 10000, cell_changes, team_scores)
                _add_assists(player1, 1, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                #sounds.append(downed_audio)

            case EventType.CLEAR:
                _add_clears(player1, 1, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                #sounds.append(downed_audio)

            case EventType.PENALTY:
                _add_score(player1, -1000, cell_changes, team_scores)

        # Handle a player being down.
        if event.type in _EVENTS_DOWNING_PLAYER:
            _down_player(player2, row_changes, event.time, player_reup_times)

        if team_goals == old_team_goals:
            new_team_scores = []
        else:
            new_team_scores = [
                team_goals[team] for team in team_rosters.keys()
            ]

        events.append(ReplayEvent(timestamp_millis=timestamp, message=message, cell_changes=cell_changes,
                                  row_changes=row_changes, team_scores=new_team_scores, sounds=sounds,
                                  sound_stereo_balance=stereo_balance))

    return Replay(
        events=events,
        teams=replay_teams,
        column_headers=column_headers,
        sounds=[],
        intro_sound=None,
        start_sound=None,
    )


def _down_player(player: _Player, row_changes: List[ReplayRowChange], timestamp_millis: int,
                 player_reup_times: Dict[_Player, int]):
    row_changes.append(ReplayRowChange(row_id=player.row_id, new_css_class=player.team.dim_css_class))

    # The player will be back up 8 seconds from now.
    player_reup_times[player] = timestamp_millis + 8000


def _add_score(player: _Player, points_to_add: int, cell_changes: List[ReplayCellChange], team_scores: Dict[Team, int]):
    player.score += points_to_add
    team_scores[player.team] += points_to_add


def _add_assists(player: _Player, assists_to_add: int, cell_changes: List[ReplayCellChange]):
    player.assists += assists_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_ASSISTS_COLUMN, new_value=str(player.assists)))


def _add_blocks(player: _Player, blocks_to_add: int, cell_changes: List[ReplayCellChange]):
    player.blocks += blocks_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_BLOCKS_COLUMN, new_value=str(player.blocks)))


def _add_goals(player: _Player, goals_to_add: int, cell_changes: List[ReplayCellChange]):
    player.goals += goals_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_GOALS_COLUMN, new_value=str(player.goals)))


def _add_clears(player: _Player, clears_to_add: int, cell_changes: List[ReplayCellChange]):
    player.clears += clears_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_CLEARS_COLUMN, new_value=str(player.clears)))


def _add_passes(player: _Player, passes_to_add: int, cell_changes: List[ReplayCellChange]):
    player.passes += passes_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_PASSES_COLUMN, new_value=str(player.passes)))


def _add_steals(player: _Player, steals_to_add: int, cell_changes: List[ReplayCellChange]):
    player.steals += steals_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_STEALS_COLUMN, new_value=str(player.steals)))


def _add_assists(player: _Player, assists_to_add: int, cell_changes: List[ReplayCellChange]):
    player.assists += assists_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_ASSISTS_COLUMN, new_value=str(player.assists)))


def _add_assists(player: _Player, assists_to_add: int, cell_changes: List[ReplayCellChange]):
    player.assists += assists_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_ASSISTS_COLUMN, new_value=str(player.assists)))


def _create_entity_reference(argument: str, entity_id_to_player: dict, entity_id_to_nonplayer_name: dict) -> str:
    if argument in entity_id_to_nonplayer_name:
        return entity_id_to_nonplayer_name[argument]

    player = entity_id_to_player[argument]
    css_class = player.team.css_class
    return f'<span class="{css_class}">{player.name}</span>'

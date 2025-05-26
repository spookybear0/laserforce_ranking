from dataclasses import dataclass
from typing import List

from db.game import Events
from db.laserball import LaserballGame
from db.types import EventType, Team
from helpers.gamehelper import get_team_rosters
from helpers.replay import Replay, ReplayTeam, ReplayPlayer, ReplayCellChange, \
    ReplayRowChange, PlayerState, ReplayGenerator


@dataclass(kw_only=True)
class _Player(PlayerState):
    goals: int = 0
    assists: int = 0
    steals: int = 0
    clears: int = 0
    passes: int = 0
    blocks: int = 0

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


class ReplayGeneratorLaserball(ReplayGenerator):
    def __init__(self):
        super().__init__()

        self.team_goals = dict[Team, int]()
        self.ball_owner = None

    async def generate(self, game: LaserballGame) -> Replay:
        self.entity_starts = await game.entity_starts.all()
        self.team_rosters = await get_team_rosters(self.entity_starts,
                                                   await game.entity_ends.all())
        # Set up the teams and players.
        column_headers = ["Codename", "Goals", "Assists", "Steals", "Clears", "Passes", "Blocks", "Accuracy"]

        replay_teams = []
        row_index = 1

        sound_balance = -0.5

        for team, players in self.team_rosters.items():
            replay_player_list = []
            players_in_team = []
            self.team_scores[team] = 0
            self.team_goals[team] = 0
            self.team_sound_balance[team] = sound_balance
            sound_balance += 1.0

            if sound_balance > 1.0:
                sound_balance -= 2.0

            for player_info in players:
                cells = [player_info.display_name, "0", "0", "0", "0", "0", "0", ""]
                row_id = f"r{row_index}"

                player = _Player(row_index=row_index,
                                 row_id=row_id, team=team, name=player_info.display_name)

                replay_player_list.append(ReplayPlayer(cells=cells, row_id=row_id, css_class=player.team.css_class))
                row_index += 1

                self.entity_id_to_player[player_info.entity_start.entity_id] = player
                players_in_team.append(player)

            replay_team = ReplayTeam(name=team.name, css_class=team.css_class, id=f"{team.element.lower()}_team",
                                     players=replay_player_list)
            replay_teams.append(replay_team)
            self.teams[team] = players_in_team

        self.init_teams()

        self.ball_owner = None

        self.process_events(await game.events.all(), self.handle_event)

        return Replay(
            events=self.events,
            teams=replay_teams,
            column_headers=column_headers,
            sounds=[],
            intro_sound=None,
            start_sound=None,
            sort_columns_index=[_GOALS_COLUMN, _ASSISTS_COLUMN, _STEALS_COLUMN, _BLOCKS_COLUMN],
            game_start_real_world_timestamp=None,
        )

    def handle_event(self, event: Events, player1, player2):
        timestamp = event.time
        old_team_goals = self.team_goals.copy()
        old_ball_owner = self.ball_owner
        sounds = []
        stereo_balance = 0.0

        # Count successful hits.
        if event.type in _EVENTS_SUCCESSFUL_HITS:
            player1.total_shots_hit += 1

        # Count shots. This must be done after counting hits so we can get the right accuracy.
        if event.type in _EVENTS_INVOLVING_SHOTS:
            player1.total_shots_fired += 1
            self.cell_changes.append(ReplayCellChange(row_id=player1.row_id, column=_ACCURACY_COLUMN,
                                                      new_value="%.2f%%" % (
                                                          player1.total_shots_hit * 100 / player1.total_shots_fired)))

        # Handle each event.
        match event.type:
            case EventType.GETS_BALL:
                self.ball_owner = player1

            case EventType.BLOCK:
                self._add_score(player1, 1)
                self._add_blocks(player1, 1)
                # stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.PASS:
                self._add_score(player1, 1)
                self._add_passes(player1, 1)
                self.ball_owner = player2
                # stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.STEAL:
                self._add_score(player1, 100)
                self._add_steals(player1, 1)
                self.ball_owner = player1
                # stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.GOAL:
                self._add_score(player1, 10000)
                self._add_goals(player1, 1)
                self.team_goals[player1.team] += 1
                # stereo_balance = team_sound_balance[player1.team]
                # sounds.append(downed_audio)

            case EventType.ASSIST:
                self._add_score(player1, 10000)
                self._add_assists(player1, 1)
                # stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.CLEAR:
                self._add_clears(player1, 1)
                ball_owner = player2
                # stereo_balance = team_sound_balance[player2.team]
                # sounds.append(downed_audio)

            case EventType.PENALTY:
                self._add_score(player1, -1000)

        if self.ball_owner != old_ball_owner:
            if old_ball_owner:
                self.row_changes.append(
                    ReplayRowChange(row_id=old_ball_owner.row_id, new_css_class=old_ball_owner.team.css_class))

            if self.ball_owner:
                self.row_changes.append(ReplayRowChange(row_id=self.ball_owner.row_id, new_css_class='ball-owner'))

        # Handle a player being down.
        if event.type in _EVENTS_DOWNING_PLAYER:
            self._down_player(player2, event.time)

        if self.team_goals == old_team_goals:
            new_team_scores = []
        else:
            new_team_scores = [
                self.team_goals[team] for team in self.team_rosters.keys()
            ]

    def _down_player(self, player: _Player, timestamp_millis: int):
        self.row_changes.append(ReplayRowChange(row_id=player.row_id, new_css_class=player.team.down_css_class))

        # The player will be back up 8 seconds from now.
        self.player_reup_times[player] = timestamp_millis + 8000

    def _add_score(self, player: _Player, points_to_add: int):
        player.score += points_to_add
        self.team_scores[player.team] += points_to_add

    def _add_assists(self, player: _Player, assists_to_add: int):
        player.assists += assists_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_ASSISTS_COLUMN, new_value=str(player.assists)))

    def _add_blocks(self, player: _Player, blocks_to_add: int):
        player.blocks += blocks_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_BLOCKS_COLUMN, new_value=str(player.blocks)))

    def _add_goals(self, player: _Player, goals_to_add: int):
        player.goals += goals_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_GOALS_COLUMN, new_value=str(player.goals)))

    def _add_clears(self, player: _Player, clears_to_add: int):
        player.clears += clears_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_CLEARS_COLUMN, new_value=str(player.clears)))

    def _add_passes(self, player: _Player, passes_to_add: int):
        player.passes += passes_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_PASSES_COLUMN, new_value=str(player.passes)))

    def _add_steals(self, player: _Player, steals_to_add: int):
        player.steals += steals_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_STEALS_COLUMN, new_value=str(player.steals)))

    def _add_assists(self, player: _Player, assists_to_add: int):
        player.assists += assists_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_ASSISTS_COLUMN, new_value=str(player.assists)))


async def create_laserball_replay(game: LaserballGame) -> Replay:
    generator = ReplayGeneratorLaserball()
    return await generator.generate(game)

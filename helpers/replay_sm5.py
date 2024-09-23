from dataclasses import dataclass
from typing import List

from db.game import Events
from db.sm5 import SM5Game
from db.types import IntRole, EventType, Team
from helpers.gamehelper import get_team_rosters
from helpers.replay import Replay, ReplayTeam, ReplayPlayer, ReplayCellChange, \
    ReplayRowChange, ReplaySound, ReplayGenerator, PlayerState
from helpers.sm5helper import SM5_ROLE_DETAILS, Sm5RoleDetails


@dataclass(kw_only=True)
class _Player(PlayerState):
    lives: int
    shots: int
    missiles: int
    role: IntRole
    role_details: Sm5RoleDetails
    times_got_shot: int = 0
    times_shot_others: int = 0
    rapid_fire: bool = False
    special_points: int = 0

    def __hash__(self):
        return self.row_index


_SCORE_COLUMN = 2
_LIVES_COLUMN = 3
_SHOTS_COLUMN = 4
_MISSILES_COLUMN = 5
_SPEC_COLUMN = 6
_ACCURACY_COLUMN = 7
_KD_COLUMN = 8

_EVENTS_COSTING_SHOTS = {
    EventType.MISS,
    EventType.MISS_BASE,
    EventType.HIT_BASE,
    EventType.DESTROY_BASE,
    EventType.DAMAGED_OPPONENT,
    EventType.DOWNED_OPPONENT,
    EventType.DAMANGED_TEAM,
    EventType.DOWNED_TEAM,
}

_EVENTS_COSTING_MISSILES = {
    EventType.MISSILE_MISS,
    EventType.MISSILE_DAMAGE_TEAM,
    EventType.MISSILE_DOWN_TEAM,
    EventType.MISSILE_DAMAGE_OPPONENT,
    EventType.MISSILE_DOWN_OPPONENT,
    EventType.MISSILE_BASE_MISS,
    EventType.MISSILE_BASE_DAMAGE,
    EventType.MISISLE_BASE_DESTROY,
}

_EVENTS_SUCCESSFUL_HITS = {
    EventType.HIT_BASE,
    EventType.DESTROY_BASE,
    EventType.DAMAGED_OPPONENT,
    EventType.DOWNED_OPPONENT,
    EventType.DAMANGED_TEAM,
    EventType.DOWNED_TEAM,
}

_EVENTS_COSTING_LIVES = {
    EventType.DOWNED_OPPONENT: 1,
    EventType.DOWNED_TEAM: 1,
    EventType.MISSILE_DOWN_OPPONENT: 2,
    EventType.MISSILE_DOWN_TEAM: 2,
}

_EVENTS_GIVING_SPECIAL_POINTS = {
    EventType.DAMAGED_OPPONENT: 1,
    EventType.DESTROY_BASE: 5,
    EventType.DOWNED_OPPONENT: 1,
    EventType.MISSILE_BASE_DAMAGE: 5,
    EventType.MISISLE_BASE_DESTROY: 5,
    EventType.MISSILE_DAMAGE_OPPONENT: 2,
    EventType.MISSILE_DOWN_OPPONENT: 2,
}

# Points awarded to player1 in an event.
_EVENTS_ADDING_TO_SCORE = {
    EventType.BASE_AWARDED: 1001,
    EventType.DAMAGED_OPPONENT: 100,
    EventType.DAMANGED_TEAM: -100,
    EventType.DESTROY_BASE: 1001,
    EventType.DETONATE_NUKE: 500,
    EventType.DOWNED_OPPONENT: 100,
    EventType.DOWNED_TEAM: -100,
    EventType.MISSILE_BASE_DAMAGE: 1001,
    EventType.MISISLE_BASE_DESTROY: 1001,
    EventType.MISSILE_DAMAGE_OPPONENT: 500,
    EventType.MISSILE_DAMAGE_TEAM: -500,
    EventType.MISSILE_DOWN_OPPONENT: 500,
    EventType.MISSILE_DOWN_TEAM: -500,
}

_EVENTS_DOWNING_PLAYER = {
    EventType.DOWNED_OPPONENT,
    EventType.DOWNED_TEAM,
    EventType.MISSILE_DOWN_OPPONENT,
    EventType.MISSILE_DOWN_TEAM,
    EventType.RESUPPLY_LIVES,
    EventType.RESUPPLY_AMMO,
}

_START_AUDIO = 0
_ALARM_START_AUDIO = 1
_RESUPPLY_AUDIO = 2
_DOWNED_AUDIO = 3
_BASE_DESTROYED_AUDIO = 4
_RAPID_FIRE_AUDIO = 5
_MISSILE_AUDIO = 6
_ZAP_OWN_AUDIO = 7
_NUKE_AUDIO = 8
_ELIMINATION_AUDIO = 9
_BOOST_AUDIO = 10
_DO_IT_AUDIO = 11

_AUDIO_PREFIX = "/assets/sm5/audio/"


def _create_role_image(role: IntRole) -> str:
    return f'<img src="/assets/sm5/roles/{str(role).lower()}.png" alt="{role}" width="30" height="30">'


@dataclass
class _Team:
    players: List[_Player]


class ReplayGeneratorSm5(ReplayGenerator):
    def __init__(self):
        super().__init__()

        self.team_players_alive = dict[Team, int]()
        self.start_audio = ReplaySound(
            [f"{_AUDIO_PREFIX}Start.0.wav", f"{_AUDIO_PREFIX}Start.1.wav", f"{_AUDIO_PREFIX}Start.2.wav",
             f"{_AUDIO_PREFIX}Start.3.wav"], _START_AUDIO, priority=2, required=True)
        self.alarm_start_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/General Quarters.wav"], _ALARM_START_AUDIO,
                                             priority=1)
        self.resupply_audio = ReplaySound(
            [f"{_AUDIO_PREFIX}Effect/Resupply.0.wav", f"{_AUDIO_PREFIX}Effect/Resupply.1.wav",
             f"{_AUDIO_PREFIX}Effect/Resupply.2.wav", f"{_AUDIO_PREFIX}Effect/Resupply.3.wav",
             f"{_AUDIO_PREFIX}Effect/Resupply.4.wav"], _RESUPPLY_AUDIO)
        self.downed_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/Scream.0.wav", f"{_AUDIO_PREFIX}Effect/Scream.1.wav",
                                         f"{_AUDIO_PREFIX}Effect/Scream.2.wav", f"{_AUDIO_PREFIX}Effect/Shot.0.wav",
                                         f"{_AUDIO_PREFIX}Effect/Shot.1.wav"], _DOWNED_AUDIO)
        self.base_destroyed_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/Boom.wav"], _BASE_DESTROYED_AUDIO)
        self.rapid_fire_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Rapid Fire.0.wav",
            f"{_AUDIO_PREFIX}Rapid Fire.1.wav",
            f"{_AUDIO_PREFIX}Rapid Fire.2.wav",
            f"{_AUDIO_PREFIX}Rapid Fire.3.wav",
        ],
            _RAPID_FIRE_AUDIO)
        self.missile_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Missile.0.wav",
            f"{_AUDIO_PREFIX}Missile.1.wav",
            f"{_AUDIO_PREFIX}Missile.2.wav",
        ],
            _MISSILE_AUDIO)
        self.zap_own_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Zap Own.0.wav",
            f"{_AUDIO_PREFIX}Zap Own.1.wav",
            f"{_AUDIO_PREFIX}Zap Own.2.wav",
            f"{_AUDIO_PREFIX}Zap Own.3.wav",
        ],
            _ZAP_OWN_AUDIO)
        self.nuke_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Nuke.0.wav",
            f"{_AUDIO_PREFIX}Nuke.1.wav",
            f"{_AUDIO_PREFIX}Nuke.2.wav",
        ],
            _NUKE_AUDIO)
        self.elimination_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Elimination.wav",
        ],
            _ELIMINATION_AUDIO)
        self.boost_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Boost.0.wav",
            f"{_AUDIO_PREFIX}Boost.1.wav",
            f"{_AUDIO_PREFIX}Boost.2.wav",
        ],
            _BOOST_AUDIO)
        self.do_it_audio = ReplaySound([
            f"{_AUDIO_PREFIX}Do It.wav",
        ],
            _DO_IT_AUDIO)

        self.sound_assets = [
            self.start_audio,
            self.alarm_start_audio,
            self.resupply_audio,
            self.downed_audio,
            self.base_destroyed_audio,
            self.rapid_fire_audio,
            self.missile_audio,
            self.zap_own_audio,
            self.nuke_audio,
            self.elimination_audio,
            self.boost_audio,
            self.do_it_audio,
        ]

    async def generate(self, game: SM5Game) -> Replay:
        self.entity_starts = await game.entity_starts.all()
        self.team_rosters = await get_team_rosters(self.entity_starts,
                                                   await game.entity_ends.all())

        # Set up the teams and players.
        column_headers = ["Role", "Codename", "Score", "Lives", "Shots", "Missiles", "Spec", "Accuracy", "K/D"]
        replay_teams = []
        row_index = 1

        sound_balance = -0.5

        for team, players in self.team_rosters.items():
            replay_player_list = []
            players_in_team = []
            self.team_scores[team] = 0
            self.team_sound_balance[team] = sound_balance
            sound_balance += 1.0

            if sound_balance > 1.0:
                sound_balance -= 2.0

            for player_info in players:
                if player_info.entity_start.role not in SM5_ROLE_DETAILS:
                    # Shouldn't happen - a player with an unknown SM5 role?
                    continue

                role = player_info.entity_start.role
                role_details = SM5_ROLE_DETAILS[role]

                cells = [_create_role_image(player_info.entity_start.role), player_info.display_name, "0",
                         str(role_details.initial_lives), "0", str(role_details.missiles), "0", "", ""]
                row_id = f"r{row_index}"

                player = _Player(lives=role_details.initial_lives, shots=role_details.shots, row_index=row_index,
                                 role=role, row_id=row_id, missiles=role_details.missiles,
                                 role_details=role_details, team=team, name=player_info.display_name)

                replay_player_list.append(ReplayPlayer(cells=cells, row_id=row_id, css_class=player.team.css_class))
                row_index += 1

                self.entity_id_to_player[player_info.entity_start.entity_id] = player
                players_in_team.append(player)

            replay_team = ReplayTeam(name=team.name, css_class=team.css_class, id=f"{team.element.lower()}_team",
                                     players=replay_player_list)
            replay_teams.append(replay_team)
            self.teams[team] = players_in_team
            self.team_players_alive[team] = len(players_in_team)

        self.init_teams()

        self.process_events(await game.events.all(), self.handle_event)

        return Replay(
            events=self.events,
            teams=replay_teams,
            column_headers=column_headers,
            sounds=self.sound_assets,
            intro_sound=self.start_audio,
            start_sound=self.alarm_start_audio,
            sort_columns_index=[_SCORE_COLUMN]
        )

    def handle_event(self, event: Events, player1, player2):
        # Count successful hits. Must be done before removing the shot so the accuracy is correct.
        if event.type in _EVENTS_SUCCESSFUL_HITS:
            player1.total_shots_hit += 1

        # Remove a shot if the player just zapped, and update accuracy.
        if event.type in _EVENTS_COSTING_SHOTS:
            if player1.role != IntRole.AMMO:
                self._add_shots(player1, -1)

            player1.total_shots_fired += 1

            # Recompute accuracy.
            self.cell_changes.append(ReplayCellChange(row_id=player1.row_id, column=_ACCURACY_COLUMN,
                                                      new_value="%.2f%%" % (
                                                          player1.total_shots_hit * 100 / player1.total_shots_fired)))

        # Handle losing lives.
        if event.type in _EVENTS_COSTING_LIVES:
            self._add_lives(player2, -_EVENTS_COSTING_LIVES[event.type])

        if event.type in _EVENTS_COSTING_MISSILES:
            player1.missiles -= 1
            self.cell_changes.append(
                ReplayCellChange(row_id=player1.row_id, column=_MISSILES_COLUMN, new_value=str(player1.missiles)))

        if event.type in _EVENTS_GIVING_SPECIAL_POINTS:
            # Heavy doesn't get special points, and neither do scouts with rapid fire.
            if player1.role != IntRole.HEAVY and not player1.rapid_fire:
                self._add_special_points(player1, _EVENTS_GIVING_SPECIAL_POINTS[event.type])

        if event.type in _EVENTS_ADDING_TO_SCORE:
            self._add_score(player1, _EVENTS_ADDING_TO_SCORE[event.type])

        # Handle each event.
        match event.type:
            case EventType.RESUPPLY_LIVES:
                self._add_lives(player2, player2.role_details.lives_resupply)
                self.add_sound(self.resupply_audio, player2.team)

            case EventType.RESUPPLY_AMMO:
                self._add_shots(player2, player2.role_details.shots_resupply)
                self.add_sound(self.resupply_audio, player2.team)

            case EventType.ACTIVATE_RAPID_FIRE:
                player1.rapid_fire = True
                self._add_special_points(player1, -10)
                self.add_sound(self.rapid_fire_audio, player1.team)

            case EventType.HIT_BASE:
                self.add_sound(self.do_it_audio, player1.team)

            case EventType.DESTROY_BASE | EventType.MISISLE_BASE_DESTROY | EventType.MISSILE_BASE_DAMAGE:
                self.add_sound(self.base_destroyed_audio, player1.team)

            case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                self._add_score(player2, -20)
                self._increase_times_shot_others(player1)
                self._increase_times_got_shot(player2)
                self.add_sound(self.downed_audio, player2.team)

            case EventType.DAMANGED_TEAM | EventType.DOWNED_TEAM:
                self._add_score(player2, -20)
                self._increase_times_shot_others(player1)
                self._increase_times_got_shot(player2)
                self.add_sound(self.zap_own_audio, player2.team)

            case EventType.MISSILE_DOWN_OPPONENT | EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_TEAM | EventType.MISSILE_DAMAGE_TEAM:
                self._add_score(player2, -100)
                self.add_sound(self.missile_audio, player2.team)

            case EventType.DEACTIVATE_RAPID_FIRE:
                player1.rapid_fire = False

            case EventType.ACTIVATE_NUKE:
                self._add_special_points(player1, -20)
                self.add_sound(self.nuke_audio, player1.team)

            case EventType.DETONATE_NUKE:
                for team in self.teams:
                    if team != player1.team:
                        for player in self.teams[team]:
                            self._add_lives(player, -3)
                            self._down_player(player, event.time)

            case EventType.AMMO_BOOST:
                for player in self.teams[player1.team]:
                    if not player.downed:
                        self._add_shots(player, player.role_details.shots_resupply)
                self.add_sound(self.boost_audio, player1.team)

            case EventType.LIFE_BOOST:
                for player in self.teams[player1.team]:
                    if not player.downed:
                        self._add_lives(player, player.role_details.lives_resupply)
                self.add_sound(self.boost_audio, player1.team)

            case EventType.PENALTY:
                self._add_score(player1, -1000) # TODO: replace this with the penalty amount from the game info

        # Handle a player being down.
        if event.type in _EVENTS_DOWNING_PLAYER:
            self._down_player(player2, event.time)

    def _down_player(self, player: _Player, timestamp_millis: int):
        if player.lives == 0:
            return

        self.row_changes.append(ReplayRowChange(row_id=player.row_id, new_css_class=player.team.down_css_class))

        # The player will be back up 8 seconds from now.
        self.player_reup_times[player] = timestamp_millis + 8000
        player.rapid_fire = False
        player.downed = True

    def _add_lives(self, player: _Player, lives_to_add: int):
        previous_lives = player.lives

        player.lives = max(min(player.lives + lives_to_add, player.role_details.lives_max), 0)

        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_LIVES_COLUMN, new_value=str(player.lives)))

        if player.lives == 0 and previous_lives > 0:
            player.downed = True
            self.row_changes.append(ReplayRowChange(row_id=player.row_id, new_css_class="eliminated_player"))

            self.team_players_alive[player.team] -= 1

            if self.team_players_alive[player.team] == 0:
                # The entire team has been eliminated.
                self.add_sound(self.elimination_audio, player.team)

            # This player ain't coming back up.
            if player in self.player_reup_times:
                self.player_reup_times.pop(player)
            return

    def _add_shots(self, player: _Player, shots_to_add: int):
        player.shots = max(min(player.shots + shots_to_add, player.role_details.shots_max), 0)

        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_SHOTS_COLUMN, new_value=str(player.shots)))

    def _increase_times_shot_others(self, player: _Player):
        player.times_shot_others += 1
        self._update_kd(player)

    def _increase_times_got_shot(self, player: _Player):
        player.times_got_shot += 1
        self._update_kd(player)

    def _update_kd(self, player: _Player):
        kd_str = ''

        if player.times_got_shot > 0:
            kd_str = "%0.2f" % (player.times_shot_others / player.times_got_shot)

        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_KD_COLUMN, new_value=kd_str))

    def _add_special_points(self, player: _Player, points_to_add: int):
        player.special_points += points_to_add

        # 99 special points are the cap.
        player.special_points = min(player.special_points, 99)

        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_SPEC_COLUMN, new_value=str(player.special_points)))

    def _add_score(self, player: _Player, points_to_add: int):
        player.score += points_to_add
        self.cell_changes.append(
            ReplayCellChange(row_id=player.row_id, column=_SCORE_COLUMN, new_value=str(player.score)))

        self.team_scores[player.team] += points_to_add


async def create_sm5_replay(game: SM5Game) -> Replay:
    generator = ReplayGeneratorSm5()
    return await generator.generate(game)

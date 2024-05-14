from dataclasses import dataclass
from typing import List, Dict

from db.sm5 import SM5Game
from db.types import IntRole, EventType, Team
from helpers.gamehelper import get_team_rosters
from helpers.replay import Replay, ReplayTeam, ReplayPlayer, ReplayEvent, ReplayCellChange, \
    ReplayRowChange, ReplaySound
from helpers.sm5helper import SM5_ROLE_DETAILS, Sm5RoleDetails


@dataclass
class _Player:
    lives: int
    shots: int
    row_index: int
    row_id: str
    missiles: int
    role: IntRole
    role_details: Sm5RoleDetails
    team: Team
    name: str
    downed: bool = False
    times_got_shot: int = 0
    times_shot_others: int = 0
    rapid_fire: bool = False
    score: int = 0
    special_points: int = 0
    total_shots_fired: int = 0
    total_shots_hit: int = 0

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

_AUDIO_PREFIX = "/assets/sm5/audio/"


@dataclass
class _Team:
    players: List[_Player]


async def create_sm5_replay(game: SM5Game) -> Replay:
    game_duration = await game.get_actual_game_duration()
    entity_starts = await game.entity_starts.all()
    team_rosters = await get_team_rosters(entity_starts,
                                          await game.entity_ends.all())

    # Set up the teams and players.
    column_headers = ["Role", "Codename", "Score", "Lives", "Shots", "Missiles", "Spec", "Accuracy", "K/D"]
    replay_teams = []
    entity_id_to_player = {}
    row_index = 1

    teams = {}
    team_scores = {}
    team_sound_balance = {}

    entity_id_to_nonplayer_name = {
        entity.entity_id: entity.name for entity in entity_starts if entity.entity_id[0] == "@"
    }

    sound_balance = -0.5

    for team, players in team_rosters.items():
        replay_player_list = []
        players_in_team = []
        team_scores[team] = 0
        team_sound_balance[team] = sound_balance
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

            entity_id_to_player[player_info.entity_start.entity_id] = player
            players_in_team.append(player)

        replay_team = ReplayTeam(name=team.name, css_class=team.css_class, id=f"{team.element.lower()}_team",
                                 players=replay_player_list)
        replay_teams.append(replay_team)
        teams[team] = players_in_team

    events = []

    # Map from a player and the timestamp at which the player will be back up. The key is the _Player object.
    player_reup_times = {}

    start_audio = ReplaySound(
        [f"{_AUDIO_PREFIX}Start.0.wav", f"{_AUDIO_PREFIX}Start.1.wav", f"{_AUDIO_PREFIX}Start.2.wav",
         f"{_AUDIO_PREFIX}Start.3.wav"], _START_AUDIO, priority=2, required=True)
    alarm_start_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/General Quarters.wav"], _ALARM_START_AUDIO, priority=1)
    resupply_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/Resupply.0.wav", f"{_AUDIO_PREFIX}Effect/Resupply.1.wav",
                                  f"{_AUDIO_PREFIX}Effect/Resupply.2.wav", f"{_AUDIO_PREFIX}Effect/Resupply.3.wav",
                                  f"{_AUDIO_PREFIX}Effect/Resupply.4.wav"], _RESUPPLY_AUDIO)
    downed_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/Scream.0.wav", f"{_AUDIO_PREFIX}Effect/Scream.1.wav",
                                f"{_AUDIO_PREFIX}Effect/Scream.2.wav", f"{_AUDIO_PREFIX}Effect/Shot.0.wav",
                                f"{_AUDIO_PREFIX}Effect/Shot.1.wav"], _DOWNED_AUDIO)
    base_destroyed_audio = ReplaySound([f"{_AUDIO_PREFIX}Effect/Boom.wav"], _BASE_DESTROYED_AUDIO)

    sound_assets = [
        start_audio,
        alarm_start_audio,
        resupply_audio,
        downed_audio,
        base_destroyed_audio,
    ]

    # Now let's walk through the events one by one and translate them into UI events.
    for event in await game.events.all():

        timestamp = event.time
        old_team_scores = team_scores.copy()
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

        # Count successful hits. Must be done before removing the shot so the accuracy is correct.
        if event.type in _EVENTS_SUCCESSFUL_HITS:
            player1.total_shots_hit += 1

        # Remove a shot if the player just zapped, and update accuracy.
        if event.type in _EVENTS_COSTING_SHOTS:
            if player1.role != IntRole.AMMO:
                _add_shots(player1, -1, cell_changes)

            player1.total_shots_fired += 1

            # Recompute accuracy.
            cell_changes.append(ReplayCellChange(row_id=player1.row_id, column=_ACCURACY_COLUMN,
                                                 new_value="%.2f%%" % (
                                                         player1.total_shots_hit * 100 / player1.total_shots_fired)))

        # Handle losing lives.
        if event.type in _EVENTS_COSTING_LIVES:
            _add_lives(player2, -_EVENTS_COSTING_LIVES[event.type], cell_changes, row_changes, player_reup_times)

        if event.type in _EVENTS_COSTING_MISSILES:
            player1.missiles -= 1
            cell_changes.append(
                ReplayCellChange(row_id=player1.row_id, column=_MISSILES_COLUMN, new_value=str(player1.missiles)))

        if event.type in _EVENTS_GIVING_SPECIAL_POINTS:
            # Heavy doesn't get special points, and neither do scouts with rapid fire.
            if player1.role != IntRole.HEAVY and not player1.rapid_fire:
                _add_special_points(player1, _EVENTS_GIVING_SPECIAL_POINTS[event.type], cell_changes)

        if event.type in _EVENTS_ADDING_TO_SCORE:
            _add_score(player1, _EVENTS_ADDING_TO_SCORE[event.type], cell_changes, team_scores)

        # Handle each event.
        match event.type:
            case EventType.RESUPPLY_LIVES:
                _add_lives(player2, player2.role_details.lives_resupply, cell_changes, row_changes, player_reup_times)
                sounds.append(resupply_audio)
                stereo_balance = team_sound_balance[player2.team]

            case EventType.RESUPPLY_AMMO:
                _add_shots(player2, player2.role_details.shots_resupply, cell_changes)
                sounds.append(resupply_audio)
                stereo_balance = team_sound_balance[player2.team]

            case EventType.ACTIVATE_RAPID_FIRE:
                player1.rapid_fire = True
                _add_special_points(player1, -10, cell_changes)
                stereo_balance = team_sound_balance[player1.team]

            case EventType.DESTROY_BASE | EventType.MISISLE_BASE_DESTROY | EventType.MISSILE_BASE_DAMAGE:
                sounds.append(base_destroyed_audio)
                stereo_balance = team_sound_balance[player1.team]

            case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                _add_score(player2, -20, cell_changes, team_scores)
                _increase_times_shot_others(player1, cell_changes)
                _increase_times_got_shot(player2, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                sounds.append(downed_audio)

            case EventType.DAMANGED_TEAM | EventType.DOWNED_TEAM:
                _add_score(player2, -20, cell_changes, team_scores)
                _increase_times_shot_others(player1, cell_changes)
                _increase_times_got_shot(player2, cell_changes)
                stereo_balance = team_sound_balance[player2.team]
                sounds.append(downed_audio)

            case EventType.MISSILE_DOWN_OPPONENT | EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_TEAM | EventType.MISSILE_DAMAGE_TEAM:
                _add_score(player2, -100, cell_changes, team_scores)
                stereo_balance = team_sound_balance[player2.team]
                # TODO: Use missile sound once we have it
                sounds.append(downed_audio)

            case EventType.DEACTIVATE_RAPID_FIRE:
                player1.rapid_fire = False

            case EventType.ACTIVATE_NUKE:
                _add_special_points(player1, -20, cell_changes)
                stereo_balance = team_sound_balance[player1.team]

            case EventType.DETONATE_NUKE:
                for team in teams:
                    if team != player1.team:
                        for player in teams[team]:
                            _add_lives(player, -3, cell_changes, row_changes, player_reup_times)
                            _down_player(player, row_changes, event.time, player_reup_times)

                stereo_balance = team_sound_balance[player1.team]
                sounds.append(base_destroyed_audio)

            case EventType.AMMO_BOOST:
                for player in teams[player1.team]:
                    if not player.downed:
                        _add_shots(player, player.role_details.shots_resupply, cell_changes)
                sounds.append(resupply_audio)
                stereo_balance = team_sound_balance[player1.team]

            case EventType.LIFE_BOOST:
                for player in teams[player1.team]:
                    if not player.downed:
                        _add_lives(player, player.role_details.lives_resupply, cell_changes, row_changes,
                                   player_reup_times)
                sounds.append(resupply_audio)
                stereo_balance = team_sound_balance[player1.team]

            case EventType.PENALTY:
                _add_score(player2, -1000, cell_changes, team_scores)

        # Handle a player being down.
        if event.type in _EVENTS_DOWNING_PLAYER:
            _down_player(player2, row_changes, event.time, player_reup_times)

        if team_scores == old_team_scores:
            new_team_scores = []
        else:
            new_team_scores = [
                team_scores[team] for team in team_rosters.keys()
            ]

        events.append(ReplayEvent(timestamp_millis=timestamp, message=message, cell_changes=cell_changes,
                                  row_changes=row_changes, team_scores=new_team_scores, sounds=sounds,
                                  sound_stereo_balance=stereo_balance))

    return Replay(
        events=events,
        teams=replay_teams,
        column_headers=column_headers,
        sounds=sound_assets,
        intro_sound=start_audio,
        start_sound=alarm_start_audio,
        sort_columns_index=[_SCORE_COLUMN]
    )


def _down_player(player: _Player, row_changes: List[ReplayRowChange], timestamp_millis: int,
                 player_reup_times: Dict[_Player, int]):
    if player.lives == 0:
        return

    row_changes.append(ReplayRowChange(row_id=player.row_id, new_css_class=player.team.down_css_class))

    # The player will be back up 8 seconds from now.
    player_reup_times[player] = timestamp_millis + 8000
    player.rapid_fire = False


def _add_lives(player: _Player, lives_to_add: int, cell_changes: List[ReplayCellChange],
               row_changes: List[ReplayRowChange], player_reup_times: Dict[_Player, int]):
    player.lives = max(min(player.lives + lives_to_add, player.role_details.lives_max), 0)

    cell_changes.append(ReplayCellChange(row_id=player.row_id, column=_LIVES_COLUMN, new_value=str(player.lives)))

    if player.lives == 0:
        row_changes.append(ReplayRowChange(row_id=player.row_id, new_css_class="eliminated_player"))

        # This player ain't coming back up.
        if player in player_reup_times:
            player_reup_times.pop(player)
        return


def _add_shots(player: _Player, shots_to_add: int, cell_changes: List[ReplayCellChange]):
    player.shots = max(min(player.shots + shots_to_add, player.role_details.shots_max), 0)

    cell_changes.append(ReplayCellChange(row_id=player.row_id, column=_SHOTS_COLUMN, new_value=str(player.shots)))


def _increase_times_shot_others(player: _Player, cell_changes: List[ReplayCellChange]):
    player.times_shot_others += 1
    _update_kd(player, cell_changes)


def _increase_times_got_shot(player: _Player, cell_changes: List[ReplayCellChange]):
    player.times_got_shot += 1
    _update_kd(player, cell_changes)


def _update_kd(player: _Player, cell_changes: List[ReplayCellChange]):
    kd_ratio = player.times_shot_others / player.times_got_shot if player.times_got_shot > 0 else 0.0
    cell_changes.append(ReplayCellChange(row_id=player.row_id, column=_KD_COLUMN, new_value="%.02f" % kd_ratio))


def _add_special_points(player: _Player, points_to_add: int, cell_changes: List[ReplayCellChange]):
    player.special_points += points_to_add

    # 99 special points are the cap.
    player.special_points = min(player.special_points, 99)

    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_SPEC_COLUMN, new_value=str(player.special_points)))


def _add_score(player: _Player, points_to_add: int, cell_changes: List[ReplayCellChange], team_scores: Dict[Team, int]):
    player.score += points_to_add
    cell_changes.append(
        ReplayCellChange(row_id=player.row_id, column=_SCORE_COLUMN, new_value=str(player.score)))

    team_scores[player.team] += points_to_add


def _create_role_image(role: IntRole) -> str:
    return f'<img src="/assets/sm5/roles/{str(role).lower()}.png" alt="{role}" width="30" height="30">'


def _create_entity_reference(argument: str, entity_id_to_player: dict, entity_id_to_nonplayer_name: dict) -> str:
    if argument in entity_id_to_nonplayer_name:
        return entity_id_to_nonplayer_name[argument]

    player = entity_id_to_player[argument]
    css_class = player.team.css_class
    return f'<span class="{css_class}">{player.name}</span>'

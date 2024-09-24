"""Various helpers specifically for SM5 games.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict

import pytz
from tortoise.expressions import Q

from db.game import EntityStarts, PlayerInfo, EntityEnds
from db.sm5 import SM5Game, SM5Stats
from db.types import Team, IntRole, PieChartData, EventType, LineChartData
from helpers.cachehelper import cache
from helpers.gamehelper import get_team_rosters, SM5_STATE_LABEL_MAP, SM5_STATE_COLORS
from helpers.statshelper import PlayerCoreGameStats, get_player_state_distribution, get_sm5_score_components, \
    count_zaps, count_missiles, TeamCoreGameStats, get_sm5_player_alive_times, get_sm5_player_alive_labels, \
    get_player_state_distribution_pie_chart, get_sm5_player_alive_colors, TimeSeriesRawData, TimeSeriesDataPoint

# TODO: A lot of stuff from statshelper.py should be moved here. But let's do that separately to keep the commit size
#  reasonable.

# Artificial timestamps for default values. We can't use datetime.min and datetime.max because they are naive.
_MIN_DATETIME = datetime(1976, 1, 1, tzinfo=pytz.utc)
_MAX_DATETIME = datetime(2035, 12, 31, tzinfo=pytz.utc)


@dataclass
class PlayerSm5GameStats(PlayerCoreGameStats):
    """The stats for a player in one SM5 game."""
    stats: SM5Stats

    # Number of milliseconds the player spent alive (and dead) in the game. Can be plugged into a pie chart.
    alive_time_values: List[int]

    # Labels for alive_time_values. Can be plugged into a pie chart.
    alive_time_labels: List[str]

    # Colors for alive_time_values. Can be plugged into a pie chart.
    alive_time_colors: List[str]

    # Number of lives over time, for every 30 seconds. Only valid if the stats were created with
    # compute_lives_over_time set to true.
    lives_over_time: List[int]

    # How many times this player zapped the main player (for score cards). None if this wasn't computed.
    zapped_main_player: Optional[int]

    # How many times this player got zapped by the main player (for score cards). None if this wasn't computed.
    zapped_by_main_player: Optional[int]

    # How many times this player missiled the main player (for score cards). None if this wasn't computed.
    missiled_main_player: Optional[int]

    # How many times this player got zapped by the main player (for score cards). None if this wasn't computed.
    missiled_by_main_player: Optional[int]

    # String expressing the hit ratio between this player and the main player. None if this wasn't computed.
    main_player_hit_ratio: Optional[str]

    @property
    def lives_left(self) -> int:
        return self.stats.lives_left

    @property
    def shots_left(self) -> int:
        return self.stats.shots_left

    @property
    def shot_team(self) -> int:
        return self.stats.shot_team

    @property
    def missile_hits(self) -> int:
        return self.stats.missile_hits

    @property
    def missiled_team(self) -> int:
        return self.stats.missiled_team

    @property
    def missiled_opponent(self) -> int:
        return self.stats.missiled_opponent

    @property
    def times_missiled(self) -> int:
        return self.stats.times_missiled

    @property
    def nukes_detonated(self) -> int:
        return self.stats.nukes_detonated

    @property
    def nuke_cancels(self) -> int:
        return self.stats.nuke_cancels

    @property
    def medic_hits(self) -> int:
        return self.stats.medic_hits

    @property
    def penalties(self) -> int:
        return self.stats.penalties

    @property
    def role(self) -> Optional[IntRole]:
        return self.entity_start.role if self.entity_start else None

    @property
    def state_distribution_pie_chart(self) -> PieChartData:
        return get_player_state_distribution_pie_chart(self.state_distribution, SM5_STATE_COLORS)


@dataclass
class Sm5PlayerGameStatsSum(PlayerSm5GameStats):
    """Fake SM5 player game stats for the sum of all players in a team."""
    total_score: int

    total_gross_positive_score: int

    average_points_per_minute: int

    average_lives_left: int

    average_shots_left: int

    total_shot_team: int

    total_missile_hits: int

    total_times_missiled: int

    total_missiled_team: int

    total_missiled_opponent: int

    total_medic_hits: int

    average_time_alive_millis: int

    total_penalties: int

    @property
    def name(self) -> str:
        return "Total"

    @property
    def score(self) -> int:
        return self.total_score

    @property
    def lives_left(self) -> int:
        return self.average_lives_left

    @property
    def shots_left(self) -> int:
        return self.average_shots_left

    @property
    def points_per_minute(self) -> int:
        return self.average_points_per_minute

    def get_gross_positive_score(self) -> int:
        return self.total_gross_positive_score

    @property
    def shot_team(self) -> int:
        return self.total_shot_team

    @property
    def missile_hits(self) -> int:
        return self.total_missile_hits

    @property
    def times_missiled(self) -> int:
        return self.total_times_missiled

    @property
    def missiled_team(self) -> int:
        return self.total_missiled_team

    @property
    def missiled_opponent(self) -> int:
        return self.total_missiled_opponent

    @property
    def medic_hits(self) -> int:
        return self.total_medic_hits

    @property
    def time_in_game_millis(self) -> int:
        return self.average_time_alive_millis

    @property
    def penalties(self) -> int:
        return self.total_penalties


@dataclass
class TeamSm5GameStats(TeamCoreGameStats):
    """The stats for a team for one SM5 game."""
    players: List[PlayerSm5GameStats]

    # The stats for every player in the game, plus a fake stat at the end with the sum (or average) of all players.
    @property
    def players_with_sum(self):
        return self.players + [self.sum_player]

    # A fake player that has the sum (or average where appropriate) of all players in the team.
    sum_player: Sm5PlayerGameStatsSum

    # Average number of lives across all players over time, for every 30 seconds. Only valid if the stats were created
    # with compute_lives_over_time set to true.
    lives_over_time: List[float]

    def get_player_infos(self) -> List[PlayerInfo]:
        return [player.player_info for player in self.players]


@dataclass
class Sm5RoleDetails:
    initial_lives: int
    lives_resupply: int
    lives_max: int
    shots: int
    shots_resupply: int
    shots_max: int
    missiles: int


SM5_ROLE_DETAILS = {
    IntRole.COMMANDER: Sm5RoleDetails(initial_lives=15, lives_resupply=4, lives_max=30, shots=30, shots_resupply=5,
                                      shots_max=60, missiles=5),
    IntRole.HEAVY: Sm5RoleDetails(initial_lives=10, lives_resupply=3, lives_max=20, shots=20, shots_resupply=5,
                                  shots_max=40, missiles=5),
    IntRole.SCOUT: Sm5RoleDetails(initial_lives=15, lives_resupply=5, lives_max=30, shots=30, shots_resupply=10,
                                  shots_max=60, missiles=0),
    IntRole.AMMO: Sm5RoleDetails(initial_lives=10, lives_resupply=3, lives_max=20, shots=15, shots_resupply=0,
                                 shots_max=15, missiles=0),
    IntRole.MEDIC: Sm5RoleDetails(initial_lives=20, lives_resupply=0, lives_max=20, shots=15, shots_resupply=5,
                                  shots_max=30, missiles=0),
}


@dataclass
class FullSm5Stats:
    # All teams, sorted by team score (highest to lowest).
    teams: List[TeamSm5GameStats]

    # Dict with all players from all teams. Key is the entity end ID.
    all_players: dict[int, PlayerSm5GameStats]

    def get_teams(self) -> List[Team]:
        return [team.team for team in self.teams]

    def get_team_rosters(self) -> Dict[Team, List[PlayerInfo]]:
        return {
            team.team: team.get_player_infos() for team in self.teams
        }

    def get_lives_over_time_team_average_line_chart(self) -> List[LineChartData]:
        return [
            LineChartData(
                label=f"{team.element} Team Average Lives",
                color=team.css_color_name,
                data=team.lives_over_time,
            )
            for team in self.teams
        ]


@cache()
async def get_sm5_player_stats(game: SM5Game, main_player: Optional[EntityStarts] = None,
                               compute_lives_over_time: bool = False) -> FullSm5Stats:
    """Returns all teams with all player stats for an SM5 game.

    Returns:
        A list of teams and all the players within them. The teams will be sorted by highest score.
    """
    teams = []
    all_players = {}

    game_duration = await game.get_actual_game_duration()

    team_rosters = await get_team_rosters(game.entity_starts, game.entity_ends)
    live_over_time_per_player = {}

    if compute_lives_over_time:
        live_over_time_per_player = await get_sm5_lives_over_time(game, team_rosters, 30000)

    for team in team_rosters.keys():
        players = []
        avg_state_distribution = {}
        avg_score_components = {}
        sum_mvp_points = 0
        sum_shots_fired = 0
        sum_shots_hit = 0
        sum_shots_left = 0
        sum_lives_left = 0
        avg_lives_over_time = {}
        sum_shot_opponent = 0
        sum_times_zapped = 0
        sum_zapped_main_player = 0
        sum_zapped_by_main_player = 0
        sum_missiled_main_player = 0
        sum_missiled_by_main_player = 0
        sum_score = 0
        sum_penalties = 0
        sum_points_per_minute = 0
        sum_gross_positive_score = 0
        sum_shot_team = 0
        sum_missile_hits = 0
        sum_times_missiled = 0
        sum_missiled_team = 0
        sum_missiled_opponent = 0
        sum_medic_hits = 0
        sum_time_alive = 0

        for player in team_rosters[team]:
            stats = await SM5Stats.filter(entity_id=player.entity_start.id).first()

            if not stats:
                # This player might have been kicked before the game was over. Don't include in the actual result.
                continue

            score_components = await get_sm5_score_components(game, stats, player.entity_start)

            state_distribution = await get_player_state_distribution(player.entity_start, player.entity_end,
                                                                     game.player_states,
                                                                     game.events,
                                                                     SM5_STATE_LABEL_MAP)

            zapped_main_player = None
            zapped_by_main_player = None
            missiled_main_player = None
            missiled_by_main_player = None
            main_player_hit_ratio = None
            is_main_player = False

            if main_player:
                is_main_player = player.entity_start.id == main_player.id
                zapped_main_player = await count_zaps(game, player.entity_start.entity_id, main_player.entity_id)
                zapped_by_main_player = await count_zaps(game, main_player.entity_id, player.entity_start.entity_id)
                missiled_main_player = await count_missiles(game, player.entity_start.entity_id, main_player.entity_id)
                missiled_by_main_player = await count_missiles(game, main_player.entity_id,
                                                               player.entity_start.entity_id)

                main_player_hit_ratio = "%.2f" % _calc_ratio(zapped_by_main_player, zapped_main_player)

            lives_over_time = live_over_time_per_player[
                player.entity_end.id] if player.entity_end.id in live_over_time_per_player else []

            player = PlayerSm5GameStats(
                team=team,
                player_info=player,
                css_class="player%s%s" % (" active_player" if is_main_player else "",
                                          " eliminated_player" if stats.lives_left == 0 else ""),
                state_distribution=state_distribution,
                score_components=score_components,
                mvp_points=await stats.mvp_points(),
                shots_fired=stats.shots_fired,
                shots_hit=stats.shots_hit,
                lives_over_time=lives_over_time,
                shot_opponent=stats.shot_opponent,
                times_zapped=stats.times_zapped,
                stats=stats,
                alive_time_values=get_sm5_player_alive_times(game_duration, player.entity_end),
                alive_time_labels=get_sm5_player_alive_labels(game_duration, player.entity_end),
                alive_time_colors=get_sm5_player_alive_colors(game_duration, player.entity_end),
                zapped_main_player=zapped_main_player,
                zapped_by_main_player=zapped_by_main_player,
                missiled_main_player=missiled_main_player,
                missiled_by_main_player=missiled_by_main_player,
                main_player_hit_ratio=main_player_hit_ratio,
            )

            players.append(player)
            all_players[player.entity_end.id] = player

            # Run a tally so we can compute the sum/average for the team.
            sum_score += player.score
            sum_penalties += player.penalties
            sum_gross_positive_score += player.get_gross_positive_score()
            sum_points_per_minute += player.points_per_minute
            sum_mvp_points += player.mvp_points
            sum_shots_fired += player.shots_fired
            sum_shots_hit += player.shots_hit
            sum_shots_left += player.shots_left
            sum_lives_left += player.lives_left
            avg_lives_over_time = {}
            sum_shot_opponent += player.shot_opponent
            sum_times_zapped += player.times_zapped
            sum_zapped_main_player += player.zapped_main_player if player.zapped_main_player else 0
            sum_zapped_by_main_player += player.zapped_by_main_player if player.zapped_by_main_player else 0
            sum_missiled_main_player += player.missiled_main_player if player.missiled_main_player else 0
            sum_missiled_by_main_player += player.missiled_by_main_player if player.missiled_by_main_player else 0
            sum_shot_team += player.shot_team
            sum_missile_hits += player.missile_hits
            sum_times_missiled += player.times_missiled
            sum_missiled_team += player.missiled_team
            sum_missiled_opponent += player.missiled_opponent
            sum_medic_hits += player.medic_hits
            sum_time_alive += player.time_in_game_millis

        # Create the lives-over-time average for the entire team.
        lives_over_time_team_average = []

        # Get the array length for any player. Every array has the same length.
        player_count = len(players)
        if player_count:
            keyframes = len(players[0].lives_over_time)

            for index in range(0, keyframes):
                lives_sum = sum([player.lives_over_time[index] for player in players])
                lives_over_time_team_average.append(lives_sum / player_count)

        # Fake the player count to 1 if there aren't any so we don't divide by 0. All the numbers will be 0 anyway so
        # it won't make a difference.
        average_divider = player_count if player_count else 1

        # Create the sum of all players in the game.
        sum_player = Sm5PlayerGameStatsSum(
            team=team,
            player_info=None,
            css_class="team_totals",
            total_score=sum_score,
            total_gross_positive_score=sum_gross_positive_score,
            total_penalties=sum_penalties,
            average_points_per_minute=int(sum_points_per_minute / average_divider),
            state_distribution=avg_state_distribution,
            score_components=avg_score_components,
            mvp_points=sum_mvp_points / average_divider,
            shots_fired=sum_shots_fired,
            shots_hit=sum_shots_hit,
            average_shots_left=int(sum_shots_left / average_divider),
            average_lives_left=int(sum_lives_left / average_divider),
            lives_over_time=avg_lives_over_time,
            shot_opponent=sum_shot_opponent,
            times_zapped=sum_times_zapped,
            stats=None,
            alive_time_values=get_sm5_player_alive_times(game_duration, player.entity_end),
            alive_time_labels=get_sm5_player_alive_labels(game_duration, player.entity_end),
            alive_time_colors=get_sm5_player_alive_colors(game_duration, player.entity_end),
            zapped_main_player=sum_zapped_main_player,
            zapped_by_main_player=sum_zapped_by_main_player,
            missiled_main_player=sum_missiled_main_player,
            missiled_by_main_player=sum_missiled_by_main_player,
            main_player_hit_ratio="%.2f" % _calc_ratio(sum_zapped_by_main_player, sum_zapped_main_player),
            total_shot_team=sum_shot_team,
            total_missiled_team=sum_missiled_team,
            total_missiled_opponent=sum_missiled_opponent,
            total_missile_hits=sum_missile_hits,
            total_times_missiled=sum_times_missiled,
            total_medic_hits=sum_medic_hits,
            average_time_alive_millis=int(sum_time_alive / average_divider),
        )

        # Sort the roster by score.
        players.sort(key=lambda x: x.score, reverse=True)
        teams.append(
            TeamSm5GameStats(
                team=team,
                score=await game.get_team_score(team),
                score_adjustment=game.get_team_score_adjustment(team),
                players=players,
                sum_player=sum_player,
                lives_over_time=lives_over_time_team_average
            ))

    # Sort teams by score.
    teams.sort(key=lambda x: x.score, reverse=True)

    return FullSm5Stats(
        teams=teams,
        all_players=all_players,
    )


@cache()
async def get_sm5_lives_over_time(game: SM5Game, team_roster: dict[Team, List[PlayerInfo]], granularity_millis: int) -> \
        dict[int, list[int]]:
    lives_timeline = defaultdict(list)
    current_lives = {}

    entity_id_to_end_id = {}
    entity_id_to_team = {}
    entity_id_to_role_details = {}

    # Set up all players with their initial amount of lives as per role.
    for team, roster in team_roster.items():
        for player in roster:
            entity_id = player.entity_start.entity_id

            role_details = SM5_ROLE_DETAILS[player.entity_start.role]
            entity_id_to_role_details[entity_id] = role_details
            current_lives[player.entity_end.id] = role_details.initial_lives
            # Events use the string entity ID, so let's create a quick lookup.
            entity_id_to_end_id[entity_id] = player.entity_end.id
            entity_id_to_team[entity_id] = team

    _create_lives_snapshot(lives_timeline, current_lives)

    next_snapshot = granularity_millis

    events = await game.events.filter(Q(type=EventType.DOWNED_OPPONENT) | Q(type=EventType.DOWNED_TEAM)
                                      | Q(type=EventType.MISSILE_DOWN_OPPONENT) | Q(type=EventType.MISSILE_DOWN_TEAM)
                                      | Q(type=EventType.RESUPPLY_LIVES) | Q(type=EventType.DETONATE_NUKE)).all()

    for event in events:
        time_millis = event.time

        while time_millis > next_snapshot:
            _create_lives_snapshot(lives_timeline, current_lives)
            next_snapshot += granularity_millis

        match event.type:
            case EventType.DOWNED_OPPONENT | EventType.DOWNED_TEAM:
                if event.entity2 in entity_id_to_end_id:
                    _remove_lives(current_lives, entity_id_to_end_id, event.entity2, 1)

            case EventType.MISSILE_DOWN_TEAM | EventType.MISSILE_DOWN_OPPONENT:
                if event.entity2 in entity_id_to_end_id:
                    _remove_lives(current_lives, entity_id_to_end_id, event.entity2, 3)

            case EventType.RESUPPLY_LIVES:
                role_details = entity_id_to_role_details[event.entity2]
                _add_lives(current_lives, entity_id_to_end_id, event.entity2,
                           role_details.lives_resupply, role_details.lives_max)

            case EventType.DETONATE_NUKE:
                nuking_team = entity_id_to_team[event.entity1]

                for team, roster in team_roster.items():
                    if team != nuking_team:
                        for player in roster:
                            _remove_lives(current_lives, entity_id_to_end_id, player.entity_start.entity_id, 3)

    # Keep writing snapshots until we have covered the full duration of the game.
    duration = await game.get_actual_game_duration()

    while next_snapshot <= duration + granularity_millis:
        _create_lives_snapshot(lives_timeline, current_lives)
        next_snapshot += granularity_millis

    return lives_timeline


async def get_sm5_rating_over_time(entity_id: str, min_time: datetime = _MIN_DATETIME,
                                   max_time: datetime = _MAX_DATETIME) -> \
        Optional[TimeSeriesRawData]:
    """Creates a time series of the SM5 rating for a specific player.

    entity_id: Entity ID of the player to get the rating for.
    min_time: Earliest timestamp to get data for (no lower bound if not set)
    max_time: Latest timestamp to get data for (no upper bound if not set)
    """
    # Get all the EntityEnds for this player.
    entity_ends = await EntityEnds.filter(entity__entity_id=entity_id, sm5games__ranked=True,
                                          sm5games__mission_name__icontains="space marines",
                                          current_rating_mu__isnull="", current_rating_sigma__isnull="").all()

    # Create a lookup map.
    entity_end_lookup = {
        entity.id: entity for entity in entity_ends
    }

    # We also need the actual SM5 games so we can get the date of each game.
    entity_to_games = {
        entity.id: await SM5Game.filter(entity_ends__id=entity.id).first() for entity in entity_ends
    }

    # We need the reverse mapping, game ID to entity.
    games_to_entity = {
        entity_to_games[entity_id].id: entity_end_lookup[entity_id] for entity_id in entity_to_games.keys()
    }

    # Map the game IDs to the games for easier reference.
    all_games = {
        game.id: game for game in entity_to_games.values() if game
    }

    # Create a list of all game IDs, sorted by timestamp. Trim the ones outside the time range.
    game_ids = [
        game.id for game in all_games.values() if min_time <= game.start_time < max_time
    ]

    # There is no data.
    if not game_ids:
        return None

    game_ids.sort(key=lambda game_id: all_games[game_id].start_time)
    min_date = all_games[game_ids[0]].start_time
    max_date = all_games[game_ids[-1]].start_time

    # Go through each game and compute the MVP at that time.
    data_points = [
        TimeSeriesDataPoint(all_games[game_id].start_time,
                            games_to_entity[game_id].current_rating_mu - 3 * games_to_entity[
                                game_id].current_rating_sigma) for game_id in game_ids
    ]

    return TimeSeriesRawData(
        min_date=min_date, max_date=max_date, data_points=data_points
    )

async def update_winner(game: SM5Game):
    """Updates the following fields in the game:

    last_team_standing, winner, winner_color.

    Will not call save() after the update is done.
    """
    # Determine whether one team eliminated the other.
    game.last_team_standing = await get_sm5_last_team_standing(game)

    # winner determination
    winner = game.last_team_standing

    if not winner:
        red_score = await game.get_team_score(Team.RED)
        green_score = await game.get_team_score(Team.GREEN)
        if red_score > green_score:
            winner = Team.RED
        elif red_score < green_score:
            winner = Team.GREEN
        else:  # tie or no winner or something crazy happened
            winner = None

    game.winner = winner
    game.winner_color = winner.value if winner else "none"



async def get_sm5_last_team_standing(game: SM5Game) -> Optional[Team]:
    """Returns the team that eliminated the other team.

    Returns an empty value if no team eliminated the other."""
    alive_player_count = {}
    entities = await game.entity_starts.all()

    for entity in entities:
        player = await SM5Stats.filter(entity__id=entity.id).first()

        if player and player.lives_left > 0:
            alive_player_count[(await entity.team).enum] = True

    # If there isn't exactly one team with alive players at the end, this wasn't an elimination game.
    if len(alive_player_count) != 1:
        return None

    return next(iter(alive_player_count.keys()))


def _create_lives_snapshot(lives_timeline: dict[int, list[int]], current_lives: dict[int, int]):
    for entity_end_id, lives in current_lives.items():
        lives_timeline[entity_end_id].append(lives)


def _remove_lives(current_lives: dict[int, int], entity_id_to_end_id: dict[str, int], entity_id: str,
                  lives_to_remove: int):
    if entity_id not in entity_id_to_end_id:
        return

    entity_end_id = entity_id_to_end_id[entity_id]
    current_lives[entity_end_id] -= lives_to_remove

    if current_lives[entity_end_id] < 0:
        current_lives[entity_end_id] = 0


def _add_lives(current_lives: dict[int, int], entity_id_to_end_id: dict[str, int], entity_id: str,
               lives_to_add: int, max_lives: int):
    if entity_id not in entity_id_to_end_id:
        return

    entity_end_id = entity_id_to_end_id[entity_id]
    current_lives[entity_end_id] = min(current_lives[entity_end_id] + lives_to_add, max_lives)


def _calc_ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0

"""Various helpers specifically for Laserball games.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict

from db.game import EntityStarts, PlayerInfo
from db.laserball import LaserballStats, LaserballGame
from db.types import Team
from helpers.cachehelper import cache
from helpers.gamehelper import get_team_rosters, SM5_STATE_LABEL_MAP
from helpers.statshelper import PlayerCoreGameStats, get_player_state_distribution, TeamCoreGameStats, count_blocks, \
    get_ticks_for_time_graph, millis_to_time


# TODO: A lot of stuff from statshelper.py should be moved here. But let's do that separately to keep the commit size
#  reasonable.

@dataclass
class PlayerLaserballGameStats(PlayerCoreGameStats):
    """The stats for a player in one LB game."""
    stats: LaserballStats

    # How long this player had ball possession for, in milliseconds.
    possession_time_millis: int

    # How many times this player blocked the main player (for score cards). None if this wasn't computed.
    blocked_main_player: Optional[int]

    # How many times this player got blocked by the main player (for score cards). None if this wasn't computed.
    blocked_by_main_player: Optional[int]

    # String expressing the hit ratio between this player and the main player. None if this wasn't computed.
    main_player_hit_ratio: Optional[str]

    @property
    def goals(self) -> int:
        return self.stats.goals

    @property
    def assists(self) -> int:
        return self.stats.assists

    @property
    def passes(self) -> int:
        return self.stats.passes

    @property
    def steals(self) -> int:
        return self.stats.steals

    @property
    def times_stolen(self) -> int:
        return self.stats.times_stolen

    @property
    def clears(self) -> int:
        return self.stats.clears

    @property
    def blocks(self) -> int:
        return self.stats.blocks

    @property
    def times_blocked(self) -> int:
        return self.stats.times_blocked

    @property
    def possession_time_str(self) -> str:
        return millis_to_time(self.possession_time_millis)

    @property
    def score(self) -> int:
        """The score, as used in Laserforce player stats.

        The formula: Score = (Goals + Assists) * 10000 + Steals * 100 + Blocks
        See also: https://www.iplaylaserforce.com/games/laserball/.
        """
        return (self.goals + self.assists) * 10000 + self.steals * 100 + self.blocks


@dataclass
class LaserballPlayerGameStatsSum(PlayerLaserballGameStats):
    """Fake Laserball player game stats for the sum of all players in a team."""
    total_score: int

    average_points_per_minute: int

    total_goals: int

    total_assists: int

    total_passes: int

    total_steals: int

    total_times_stolen: int

    total_clears: int

    total_blocks: int

    total_times_blocked: int

    @property
    def name(self) -> str:
        return "Total"

    @property
    def goals(self) -> int:
        return self.total_goals

    @property
    def assists(self) -> int:
        return self.total_assists

    @property
    def passes(self) -> int:
        return self.total_passes

    @property
    def steals(self) -> int:
        return self.total_steals

    @property
    def times_stolen(self) -> int:
        return self.total_times_stolen

    @property
    def clears(self) -> int:
        return self.total_clears

    @property
    def blocks(self) -> int:
        return self.total_blocks

    @property
    def times_blocked(self) -> int:
        return self.total_times_blocked

    @property
    def score(self) -> int:
        return self.total_score


@dataclass
class TeamLaserballGameStats(TeamCoreGameStats):
    """The stats for a team for one Laserball game."""
    players: List[PlayerLaserballGameStats]

    # Score over time, one data point every 30 seconds.
    team_score_graph: List[int]

    # The stats for every player in the game, plus a fake stat at the end with the sum (or average) of all players.
    @property
    def players_with_sum(self):
        return self.players + [self.sum_player]

    # A fake player that has the sum (or average where appropriate) of all players in the team.
    sum_player: LaserballPlayerGameStatsSum

    def get_player_infos(self) -> List[PlayerInfo]:
        return [player.player_info for player in self.players]


@dataclass
class FullLaserballStats:
    # All teams, sorted by team score (highest to lowest).
    teams: List[TeamLaserballGameStats]

    # Dict with all players from all teams. Key is the entity end ID.
    all_players: dict[int, PlayerLaserballGameStats]

    # Score graph (one data point every 30 seconds) for every team.
    score_chart_data: dict[Team, List[int]]

    # Round graph (current round for every 30 seconds during the game).
    score_chart_data_rounds: List[int]

    def get_teams(self) -> List[Team]:
        return [team.team for team in self.teams]

    def get_team_rosters(self) -> Dict[Team, List[PlayerInfo]]:
        return {
            team.team: team.get_player_infos() for team in self.teams
        }


@cache()
async def get_laserball_player_stats(game: LaserballGame,
                                     main_player: Optional[EntityStarts] = None) -> FullLaserballStats:
    """Returns all teams with all player stats for an LB game.

    Returns:
        A list of teams and all the players within them. The teams will be sorted by highest score.
    """
    teams = []
    all_players = {}
    game_duration = game.mission_duration

    team_rosters = await get_team_rosters(game.entity_starts, game.entity_ends)

    possession_times = await game.get_possession_times()

    for team in team_rosters.keys():
        players = []
        avg_state_distribution = {}
        avg_score_components = {}
        sum_shots_fired = 0
        sum_shots_hit = 0
        sum_shot_opponent = 0
        sum_blocked_main_player = 0
        sum_blocked_by_main_player = 0
        sum_score = 0
        sum_mvp_points = 0.0
        sum_points_per_minute = 0
        sum_goals = 0
        sum_assists = 0
        sum_steals = 0
        sum_times_stolen = 0
        sum_blocks = 0
        sum_clears = 0
        sum_passes = 0
        sum_times_blocked = 0
        sum_possession_time_millis = 0

        for player in team_rosters[team]:
            stats = await LaserballStats.filter(entity_id=player.entity_start.id).first()

            if not stats:
                # This player might have been kicked before the game was over. Don't include in the actual result.
                continue

            state_distribution = await get_player_state_distribution(player.entity_start, player.entity_end,
                                                                     game.player_states,
                                                                     game.events,
                                                                     SM5_STATE_LABEL_MAP)

            blocked_main_player = None
            blocked_by_main_player = None
            main_player_hit_ratio = None
            is_main_player = False

            entity_id = player.entity_start.entity_id

            if main_player:
                is_main_player = player.entity_start.id == main_player.id
                blocked_main_player = await count_blocks(game, entity_id, main_player.entity_id)
                blocked_by_main_player = await count_blocks(game, main_player.entity_id, entity_id)

                main_player_hit_ratio = "%.2f" % _calc_ratio(blocked_by_main_player, blocked_main_player)

            possession_time = possession_times[entity_id] if entity_id in possession_times else 0

            player = PlayerLaserballGameStats(
                team=team,
                player_info=player,
                css_class="player%s" % (" active_player" if is_main_player else ""),
                state_distribution=state_distribution,
                shots_fired=stats.shots_fired,
                shots_hit=stats.shots_hit,
                stats=stats,
                blocked_main_player=blocked_main_player,
                blocked_by_main_player=blocked_by_main_player,
                main_player_hit_ratio=main_player_hit_ratio,
                shot_opponent=stats.blocks + stats.steals,
                times_zapped=stats.times_blocked + stats.times_stolen,
                score_components={},
                mvp_points=stats.mvp_points,
                possession_time_millis=possession_time,
            )

            players.append(player)
            all_players[player.entity_end.id] = player

            # Run a tally so we can compute the sum/average for the team.
            sum_score += player.score
            sum_points_per_minute += player.points_per_minute
            sum_mvp_points += player.mvp_points
            sum_shots_fired += player.shots_fired
            sum_shots_hit += player.shots_hit
            sum_shot_opponent += player.shot_opponent
            sum_times_blocked += player.times_zapped
            sum_blocked_main_player += player.blocked_main_player if player.blocked_main_player else 0
            sum_blocked_by_main_player += player.blocked_by_main_player if player.blocked_by_main_player else 0
            sum_goals += player.goals
            sum_assists += player.assists
            sum_steals += player.steals
            sum_blocks += player.blocks
            sum_clears += player.clears
            sum_passes += player.passes
            sum_times_stolen += player.times_stolen
            sum_times_blocked += player.times_blocked
            sum_possession_time_millis += player.possession_time_millis

        player_count = len(players)

        # Fake the player count to 1 if there aren't any so we don't divide by 0. All the numbers will be 0 anyway so
        # it won't make a difference.
        average_divider = player_count if player_count else 1

        # Create the sum of all players in the game.
        sum_player = LaserballPlayerGameStatsSum(
            team=team,
            player_info=None,
            css_class="team_totals",
            total_score=sum_score,
            average_points_per_minute=int(sum_points_per_minute / average_divider),
            state_distribution=avg_state_distribution,
            score_components=avg_score_components,
            mvp_points=sum_mvp_points / average_divider,
            shots_fired=sum_shots_fired,
            shots_hit=sum_shots_hit,
            shot_opponent=sum_shot_opponent,
            times_zapped=sum_times_blocked,
            stats=None,
            blocked_main_player=sum_blocked_main_player,
            blocked_by_main_player=sum_blocked_by_main_player,
            main_player_hit_ratio="%.2f" % _calc_ratio(sum_blocked_by_main_player, sum_blocked_main_player),
            total_blocks=sum_blocks,
            total_goals=sum_goals,
            total_assists=sum_assists,
            total_clears=sum_clears,
            total_steals=sum_steals,
            total_passes=sum_passes,
            total_times_blocked=sum_times_blocked,
            total_times_stolen=sum_times_stolen,
            possession_time_millis=sum_possession_time_millis,
        )

        team_score_graph = [await game.get_team_score_at_time(team, time) for time in
                            get_ticks_for_time_graph(game_duration)]

        # Sort the roster by score.
        players.sort(key=lambda x: x.score, reverse=True)
        teams.append(
            TeamLaserballGameStats(
                team=team,
                score=await game.get_team_score(team),
                players=players,
                sum_player=sum_player,
                team_score_graph=team_score_graph,
            ))

    # Sort teams by score.
    teams.sort(key=lambda x: x.score, reverse=True)

    score_chart_data = {
        team.team: team.team_score_graph for team in teams
    }

    score_chart_data_rounds = [await game.get_rounds_at_time(t) for t in get_ticks_for_time_graph(game_duration)]

    return FullLaserballStats(
        teams=teams,
        all_players=all_players,
        score_chart_data=score_chart_data,
        score_chart_data_rounds=score_chart_data_rounds,
    )


def _calc_ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0

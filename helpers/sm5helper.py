"""Various helpers specifically for SM5 games.
"""
from dataclasses import dataclass
from typing import Optional, List

from db.game import EntityStarts, EntityEnds
from db.sm5 import SM5Game, SM5Stats
from db.types import Team, IntRole, PieChartData
from helpers.formattinghelper import create_ratio_string
from helpers.gamehelper import get_team_rosters, SM5_STATE_LABEL_MAP, SM5_STATE_COLORS
from helpers.statshelper import PlayerCoreGameStats, get_player_state_distribution, get_sm5_score_components, \
    count_zaps, count_missiles, TeamCoreGameStats, get_sm5_player_alive_times, get_sm5_player_alive_labels, \
    get_player_state_distribution_pie_chart


# TODO: A lot of stuff from statshelper.py should be moved here. But let's do that separately to keep the commit size
#  reasonable.

@dataclass
class PlayerSm5GameStats(PlayerCoreGameStats):
    """The stats for a player in one SM5 game."""
    stats: SM5Stats

    # Number of milliseconds the player spent alive (and dead) in the game. Can be plugged into a pie chart.
    alive_time_values: List[int]

    # Labels for alive_time_values. Can be plugged into a pie chart.
    alive_time_labels: List[str]

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
    def missile_hits(self) -> int:
        return self.stats.missile_hits

    @property
    def missiled_team(self) -> int:
        return self.stats.missiled_team

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
    def role(self) -> IntRole:
        return self.entity_start.role

    @property
    def state_distribution_pie_chart(self) -> PieChartData:
        return get_player_state_distribution_pie_chart(self.state_distribution, SM5_STATE_COLORS)


@dataclass
class TeamSm5GameStats(TeamCoreGameStats):
    """The stats for a team for one SM5 game."""
    players: List[PlayerSm5GameStats]


@dataclass
class FullSm5Stats:
    # All teams, sorted by team score (highest to lowest).
    teams: List[TeamSm5GameStats]

    # Dict with all players from all teams. Key is the entity end ID.
    all_players: dict[int, PlayerSm5GameStats]


async def get_sm5_player_stats(game: SM5Game, main_player: Optional[EntityStarts]) -> FullSm5Stats:
    """Returns all teams with all player stats for an SM5 game.

    Returns:
        A list of teams and all the players within them. The teams will be sorted by highest score.
    """
    teams = []
    all_players = {}

    game_duration = await game.get_actual_game_duration()

    team_rosters = await get_team_rosters(game.entity_starts, game.entity_ends)

    for team in team_rosters.keys():
        players = []
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

                main_player_hit_ratio = create_ratio_string(
                    _calc_ratio(zapped_by_main_player, zapped_main_player))

            player = PlayerSm5GameStats(
                team=team,
                entity_start=player.entity_start,
                entity_end=player.entity_end,
                css_class="player%s%s" % (" active_player" if is_main_player else "",
                                          " eliminated_player" if stats.lives_left == 0 else ""),
                state_distribution=state_distribution,
                score_components=score_components,
                mvp_points=await stats.mvp_points(),
                shots_fired=stats.shots_fired,
                shots_hit=stats.shots_hit,
                shot_opponent=stats.shot_opponent,
                times_zapped=stats.times_zapped,
                stats=stats,
                alive_time_values=get_sm5_player_alive_times(game_duration, player.entity_end),
                alive_time_labels=get_sm5_player_alive_labels(game_duration, player.entity_end),
                zapped_main_player=zapped_main_player,
                zapped_by_main_player=zapped_by_main_player,
                missiled_main_player=missiled_main_player,
                missiled_by_main_player=missiled_by_main_player,
                main_player_hit_ratio=main_player_hit_ratio,
            )

            players.append(player)
            all_players[player.entity_end.id] = player

        # Sort the roster by score.
        players.sort(key=lambda x: x.score, reverse=True)
        teams.append(
            TeamSm5GameStats(
                team=team,
                score=await game.get_team_score(team),
                players=players,
            ))

    # Sort teams by score.
    teams.sort(key=lambda x: x.score, reverse=True)

    return FullSm5Stats(
        teams=teams,
        all_players=all_players,
    )


def _calc_ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0

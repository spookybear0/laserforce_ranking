from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Callable, Any

from sentry_sdk import Hub, start_transaction
from tortoise.expressions import Q
from tortoise.fields import ManyToManyRelation
from tortoise.functions import Sum

from db.game import EntityEnds, EntityStarts, PlayerInfo
from db.laserball import LaserballGame, LaserballStats
from db.sm5 import SM5Game, SM5Stats
from db.types import IntRole, EventType, PlayerStateDetailType, PlayerStateType, PlayerStateEvent, Team, PieChartData
from helpers.cachehelper import cache

# stats helpers


# The frequency for ticks in time series graphs, in milliseconds.
_DEFAULT_TICKS_DURATION_MILLIS = 30000


@dataclass
class NotableEvent:
    """An important event during a game."""
    # Number of seconds into the gameplay at which this event occurred.
    seconds: int

    # The event that happened.
    event: str


@dataclass
class TimeSeriesDataPoint:
    """A single data point in a time series."""
    date: datetime

    value: float


@dataclass
class TimeSeriesRawData:
    """A collection of data points over a stretch of time.

    This object defines the start and end time and the data points. The data points are in no particular frequency,
    and there could be multiple points for the same date.
    """
    min_date: datetime

    max_date: datetime

    data_points: List[TimeSeriesDataPoint]


@dataclass
class TimeSeriesOrderedGraphData:
    """Data points that can be used to plot a time series with ChartJS.

    The object defines the time period and the data points in a specific interval.
    """
    min_date: datetime

    max_date: datetime

    interval: timedelta

    # The actual data, starting at min_date, each point at "interval" away from each other.
    data_points: List[float]

    # Labels for the graph.
    @property
    def labels(self) -> List[str]:
        return [
            (self.min_date + self.interval * offset).strftime("%Y/%m/%d") for offset in range(0, len(self.data_points))
        ]


@dataclass
class PlayerCoreGameStats:
    """The stats for a player for one game that apply to most game formats (at least both SM5 and LB)."""

    # Every player will have this object except for fake game stats, like the sum of a team.
    player_info: Optional[PlayerInfo]

    css_class: str

    team: Team

    # Total number of shots fired.
    shots_fired: int

    # Total number of shots that hit something.
    shots_hit: int

    # Total number of shots that hit an opponent.
    shot_opponent: int

    # Total number of times the player was hit by an opponent.
    times_zapped: int

    # Breakdown of the score.
    score_components: dict[str, int]

    @property
    def entity_start(self) -> Optional[EntityStarts]:
        return self.player_info.entity_start if self.player_info else None

    @property
    def entity_end(self) -> Optional[EntityEnds]:
        return self.player_info.entity_end if self.player_info else None

    @property
    def name(self) -> str:
        return self.entity_start.name if self.entity_start else ""

    @property
    def score(self) -> int:
        """Final score for this player."""
        return self.entity_end.score if self.entity_end else 0

    @property
    def time_in_game_millis(self) -> int:
        """How long this player was in the game (in milliseconds)."""
        return self.entity_end.time if self.entity_end else 0

    @property
    def time_in_game_str(self) -> str:
        """How long this player was in the game (as MM:SS)."""
        return millis_to_time(self.time_in_game_millis)

    # How many times the player spent in each state.
    #
    # The values are in milliseconds. The actual keys depend on the game type.
    state_distribution: dict[str, int]

    # MVP points. The formula depends on the game type.
    mvp_points: float

    @property
    def accuracy(self) -> float:
        """Accuracy, between 0.0 and 1.0."""
        return self.shots_hit / self.shots_fired if self.shots_fired else 0.0

    @property
    def accuracy_str(self) -> str:
        return "%.2f%%" % (self.accuracy * 100)

    @property
    def kd_ratio(self) -> float:
        """K/D ratio, number of zaps over number of times zapped."""
        return self.shot_opponent / self.times_zapped if self.times_zapped else 1.0

    @property
    def kd_ratio_str(self) -> str:
        return "%.2g (%d/%d)" % (self.kd_ratio, self.shot_opponent, self.times_zapped)

    @property
    def points_per_minute(self) -> int:
        return get_points_per_minute(self.entity_end)

    def get_gross_positive_score(self) -> int:
        return get_sm5_gross_positive_score(self.score_components)


@dataclass
class TeamCoreGameStats:
    """The stats for a team for one game that apply to most game formats (at least both SM5 and LB)."""
    # Final team score, including adjustments.
    score: int

    team: Team

    @property
    def name(self) -> str:
        return self.team.name

    @property
    def css_color_name(self) -> str:
        return self.team.css_color_name

    @property
    def css_class(self) -> str:
        return self.team.css_class

    @property
    def element(self) -> str:
        return self.team.element

    @property
    def color(self) -> str:
        return self.team.value.color

    @property
    def score_adjustment_string(self):
        """Returns the team score adjustment as a string. Empty string if there
        was no adjustment, otherwise in the format of
        " (+10000)"
        " (-5000)"
        """
        if self.score_adjustment == 0:
            return ""

        sign = "+" if self.score_adjustment > 0 else ""

        return f" ({sign}{self.score_adjustment})"


"""

General helpers

"""

"""Max duration between an event and its resulting changes (like state change) in related tables.

For example, this is the lost duration for which we would consider a state change to "DOWN"
to be the effect of a preceding "missiled" event.
This is typically less than 20ms. We're using 50 here just in case there is a bit of lag.
"""
_EVENT_LATENCY_THRESHOLD_MILLIS = 50


def millis_to_time(milliseconds: Optional[int]) -> str:
    """Converts milliseconds into an MM:SS string."""
    if milliseconds is None:
        return "00:00"

    return "%02d:%02d" % (milliseconds / 60000, milliseconds % 60000 / 1000)


def get_ticks_for_time_graph(game_duration_millis: int) -> range:
    """Returns a list of timestamps for ticks for a time series graph.

    The list will be one tick every 30 seconds, until 30 seconds after the duration
    of the game.
    """
    return range(0, game_duration_millis + _DEFAULT_TICKS_DURATION_MILLIS, _DEFAULT_TICKS_DURATION_MILLIS)


def create_time_series_ordered_graph(raw_data: Optional[TimeSeriesRawData], tick_count: int) -> \
        Optional[TimeSeriesOrderedGraphData]:
    # If there was no data at all, then return no data.
    if not raw_data:
        return None

    # There must be at least one data point.
    assert raw_data.data_points
    assert tick_count > 1

    if len(raw_data.data_points) == 1:
        # If it's just one data point, we can't really do much here.
        return TimeSeriesOrderedGraphData(raw_data.min_date, raw_data.max_date, interval=timedelta(0.0),
                                          data_points=[raw_data.data_points[0].value for _ in range(tick_count)])

    # Get the time delta between each tick.
    tick_delta = (raw_data.max_date - raw_data.min_date) / (tick_count - 1)

    # Get the time at each tick.
    data_points = []
    source_index = 0
    output_index = 0
    time = raw_data.min_date
    data_point_count = len(raw_data.data_points)

    while output_index < tick_count:
        while time > raw_data.data_points[source_index].date and source_index < data_point_count - 1:
            source_index += 1

        data_points.append(raw_data.data_points[source_index].value)
        output_index += 1
        time += tick_delta

    return TimeSeriesOrderedGraphData(
        min_date=raw_data.min_date,
        max_date=raw_data.max_date,
        interval=tick_delta,
        data_points=data_points,
    )


async def get_sm5_score_components(game: SM5Game, stats: SM5Stats, entity_start: EntityStarts) -> dict[str, int]:
    """Returns a dict with individual components that make up a player's total score.

    Each key is a component ("Missiles", "Nukes", etc), and the value is the amount of
    points - positive or negative - the player got for all these."""
    try:
        bases_destroyed = await (game.events.filter(
            Q(type=EventType.DESTROY_BASE) | Q(type=EventType.BASE_AWARDED) | Q(type=EventType.MISISLE_BASE_DESTROY)).
                                 filter(arguments__filter={"0": entity_start.entity_id}).count())
    except Exception:  # rare exception idk why it happens
        bases_destroyed = 0
        async for event in game.events:
            if event.type == EventType.DESTROY_BASE or event.type == EventType.BASE_AWARDED or \
                    event.type == EventType.MISISLE_BASE_DESTROY:
                bases_destroyed += 1

    # Scores taken from https://www.iplaylaserforce.com/games/space-marines-sm5/
    return {
        "Missiles": stats.missiled_opponent * 500,
        "Zaps": stats.shot_opponent * 100,
        "Bases": bases_destroyed * 1001,
        "Nukes": stats.nukes_detonated * 500,
        "Zap own team": stats.shot_team * -100,
        "Missiled own team": stats.missiled_team * -500,
        "Got zapped": stats.times_zapped * -20,
        "Got missiled": stats.times_missiled * -100,
    }


def get_sm5_gross_positive_score(score_components: dict[str, int]) -> int:
    """Returns the gross positive SM5 score (i.e. the score with all the negative components taken out.

    Args:
        score_components: The score components as returned by get_sm5_score_components().
    Returns:
        The positive part of the score (i.e. without penalties like getting zapped or missiling their own team)."""
    return sum([
        value for value in score_components.values() if value > 0
    ])


def get_points_per_minute(entity: EntityEnds) -> int:
    """Returns the points per minute scored for the duration the player was in the game."""
    return int(entity.score * 60000 / entity.time) if entity.time > 0 else 0


def get_sm5_kd_ratio(stats: SM5Stats) -> float:
    """Returns the K/D for a player.

    This is the number of zaps (not downs) over the number of times the player got zapped.
    1 if the player was never zapped."""
    return stats.shot_opponent / stats.times_zapped if stats.times_zapped > 0 else 1.0


def get_sm5_player_alive_times(game_duration_millis: int, player: EntityEnds) -> List[int]:
    # Only return one value if the player was never eliminated so the pie chart is 100% filled.
    if did_player_survive_sm5_game(game_duration_millis, player):
        return [player.time]

    return [player.time, game_duration_millis - player.time]


def get_sm5_player_alive_labels(game_duration_millis: int, player: EntityEnds) -> List[str]:
    # Only return one value if the player was never eliminated so the pie chart is 100% filled.
    if did_player_survive_sm5_game(game_duration_millis, player):
        return ["Alive"]

    return ["Alive", "Dead"]


def get_sm5_player_alive_colors(game_duration_millis: int, player: EntityEnds) -> List[str]:
    # Only return one value if the player was never eliminated so the pie chart is 100% filled.
    if did_player_survive_sm5_game(game_duration_millis, player):
        return ["#00ff00"]

    return ["#ff0000", "#000000"]


def did_player_survive_sm5_game(game_duration_millis: int, player: EntityEnds) -> bool:
    return player.time >= game_duration_millis


@cache()
async def get_sm5_single_player_score_graph_data(game: SM5Game, entity_id: int) -> List[int]:
    """Returns data for a score graph for one player.

    Returns a list with data points containing the current score at the given time, one for every 30 seconds.
    """
    return [await game.get_entity_score_at_time(entity_id, time) for time in range(0, 900000 + 30000, 30000)]


@cache()
async def get_sm5_single_team_score_graph_data(game: SM5Game, team: Team) -> List[int]:
    """Returns data for a score graph for one team.

    Returns a list with data points containing the current score at the given time, one for every 30 seconds.
    """
    return [await game.get_team_score_at_time(team, time) for time in range(0, 900000 + 30000, 30000)]


@cache()
async def get_sm5_team_score_graph_data(game: SM5Game, teams: List[Team]) -> dict[Team, List[int]]:
    """Returns data for a score graph for all teams.

    Returns a dict with an entry for each team. For each team, there will be a list of data points containing the team's
    current score at the given time, one for every 30 seconds.
    """
    return {
        team: await get_sm5_single_team_score_graph_data(game, team) for team in teams
    }


"""

Average score at time

"""


async def get_average_team_score_at_time_sm5(team: Team, time: int) -> int:
    """
    Gets the average score for one team at a given time
    by going through all games and finding the
    average team score at the given time
    """

    scores = []

    for game in await SM5Game.all():
        scores.append(await game.get_team_score_at_time(team, time))

    return sum(scores) // len(scores)


"""

More specific stats

"""


async def count_zaps(game: SM5Game, zapping_entity_id: str, zapped_entity_id: str) -> int:
    """Returns the number of times one entity zapped another."""
    return await (game.events.filter(entity1=zapping_entity_id,
                                     action=" zaps ",
                                     entity2=zapped_entity_id
                                     ).count())


async def count_blocks(game: LaserballGame, zapping_entity_id: str, zapped_entity_id: str) -> int:
    """Returns the number of times one entity blocked another."""
    return await (game.events.filter(entity1=zapping_entity_id,
                                     action=" blocks ",
                                     entity2=zapped_entity_id
                                     ).count())


async def count_missiles(game: SM5Game, missiling_entity_id: str, missiled_entity_id: str) -> int:
    """Returns the number of times one entity missiled another."""
    return await (game.events.filter(entity1=missiling_entity_id,
                                     action=" missiles ",
                                     entity2=missiled_entity_id
                                     ).count())


"""

Very general stats

"""


async def get_points_scored() -> int:
    """
    Gets the total points scored by going through
    all games and adding up the total points scored

    (SM5)
    """

    points = 0

    for entity in await EntityEnds.filter(sm5games__ranked=True,
                                          sm5games__mission_name__icontains="space marines").all():
        points += entity.score

    return points


async def get_nukes_launched() -> int:
    """
    Gets the total nukes launched by going through
    all games and adding up the total nukes launched
    """

    nukes = 0

    for stats in await SM5Stats.filter(nukes_detonated__gt=0).all():
        nukes += stats.nukes_detonated

    return nukes


async def get_nukes_cancelled() -> int:
    """
    Gets the total nukes cancelled by going through
    all games and adding up the total nukes cancelled
    """

    nukes = 0

    for stats in await SM5Stats.filter(nuke_cancels__gt=0).all():
        nukes += stats.nuke_cancels

    return nukes


async def get_medic_hits() -> int:
    """
    Gets the total medic hits by going through
    all games and adding up the total medic hits
    """

    hits = 0

    for stats in await SM5Stats.filter(medic_hits__gt=0).all():
        hits += stats.medic_hits

    return hits


async def get_own_medic_hits() -> int:
    """
    Gets the total own medic hits by going through
    all games and adding up the total own medic hits
    """

    hits = 0

    for stats in await SM5Stats.filter(own_medic_hits__gt=0).all():
        hits += stats.own_medic_hits

    return hits


# laserball totals

async def get_goals_scored() -> int:
    """
    Gets the total goals scored by going through
    all games and adding up the total goals scored

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("goals")).values_list("sum",
                                                                                                               flat=True))


async def get_assists() -> int:
    """
    Gets the total assists by going through
    all games and adding up the total assists

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("assists")).values_list("sum",
                                                                                                                 flat=True))


async def get_passes() -> int:
    """
    Gets the total passes by going through
    all games and adding up the total passes

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("passes")).values_list("sum",
                                                                                                                flat=True))


async def get_steals() -> int:
    """
    Gets the total steals by going through
    all games and adding up the total steals

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("steals")).values_list("sum",
                                                                                                                flat=True))


async def get_clears() -> int:
    """
    Gets the total clears by going through
    all games and adding up the total clears

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("clears")).values_list("sum",
                                                                                                                flat=True))


async def get_blocks() -> int:
    """
    Gets the total blocks by going through
    all games and adding up the total blocks

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("blocks")).values_list("sum",
                                                                                                                flat=True))


# top roles
# could be improved by accounting for the amount of games played
# could be combined into one function

async def get_top_role_players(amount: int = 5, role: IntRole = IntRole.COMMANDER, min_games: int = 5) -> List[
    Tuple[str, int, int]]:
    """
    Gets the top players of a given role by going through
    all games and getting the average score
    for each player

    If min_games is 0 or None, it will return all players
    """

    players = {}

    for entity_end in await EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines",
                                              entity__role=role).all():
        name = (await entity_end.entity).name
        if name not in players:
            players[name] = (0, 0)
        players[name] = (players[name][0] + entity_end.score, players[name][1] + 1)

    # filter out players with less than min_games games

    if min_games:  # if min_games is 0 or None, it will return all players
        players = {name: (score, games) for name, (score, games) in players.items() if games >= min_games}

    return sorted([(name, score // games, games) for name, (score, games) in players.items()], key=lambda x: x[1],
                  reverse=True)[:amount]


# get ranking accuracy

async def get_ranking_accuracy() -> float:
    """
    Ranks how accurate the ranking system is
    at predicting the winner of a game

    returns a float between 0 and 1
    """

    correct = 0
    total = 0

    for game in await SM5Game.filter(ranked=True).all():
        red_chance, green_chance = await game.get_win_chance_before_game()
        red_score, green_score = await game.get_team_score(Team.RED), await game.get_team_score(Team.GREEN)

        # see if scores are close enough
        if int(red_chance) == int(green_chance) and abs(red_score - green_score) <= 3000:
            # if so, add 2 to correct
            # it means we did a phoenomenal job at predicting the winner
            # technically this means our rating could be higher than 100%
            # but let's treat it like extra credit :)
            correct += 2
        elif red_chance >= green_chance and red_score > green_score:
            correct += 1
        elif green_chance >= red_chance and green_score > red_score:
            correct += 1
        total += 1

    return correct / total if total != 0 else 0


# performance helpers

def sentry_trace(func) -> Callable:
    """
    Async sentry tracing decorator
    """

    async def wrapper(*args, **kwargs) -> Any:
        transaction = Hub.current.scope.transaction
        if transaction:
            with transaction.start_child(op=func.__name__):
                return await func(*args, **kwargs)
        else:
            with start_transaction(op=func.__name__, name=func.__name__):
                return await func(*args, **kwargs)

    return wrapper


async def get_player_state_timeline(entity_start: EntityStarts,
                                    entity_end: EntityEnds,
                                    player_states: ManyToManyRelation,
                                    events: ManyToManyRelation) -> list[PlayerStateEvent]:
    """Returns a timeline of states for the given entity.

    The result is a list of state markers (timestamp and owning entity) in game order. The last entry will
    always be a sentinel: The timestamp is the end of the game, and the state is None.

    Args:
        entity_start: EntityStarts object for this entity.
        entity_end: EntityEnds object for this entity.
        player_states: The player_states object from the game model.
        events: The events object from the game model.
    """
    states = await player_states.filter(entity=entity_start.id).all()

    # Get every event where either a nuke was detonated, or where this entity was the target of
    # an action.
    entity_events = await events.filter(
        Q(type=EventType.DETONATE_NUKE) | Q(arguments__filter={"2": entity_start.entity_id})).all()

    # The entity starts in ACTIVE state.
    result = [PlayerStateEvent(timestamp_millis=0, state=PlayerStateDetailType.ACTIVE)]

    # We're going to walk through the state list and look for changes.
    event_index = 0
    event_count = len(entity_events)

    for state in states:
        new_state = PlayerStateDetailType.ACTIVE

        # Note that we're ignoring other states, like UNKNOWN - we'll treat it as ACTIVE.

        if state.state == PlayerStateType.RESETTABLE:
            new_state = PlayerStateDetailType.RESETTABLE
        elif state.state == PlayerStateType.DOWN:
            new_state = PlayerStateDetailType.DOWN_FOR_OTHER

            # If the player is down, let's find out why.
            while event_index < event_count - 1 and entity_events[event_index].time < state.time:
                event_index += 1

            # Go to all events that JUST happened to this entity and see what was going on.
            while True:
                event = entity_events[event_index]
                event_time = event.time
                if event_time < state.time - _EVENT_LATENCY_THRESHOLD_MILLIS:
                    # There is no relevant event within the given threshold. That's not expected,
                    # but there may be some special kind of event, maybe custom for the game mode.
                    # We're already defaulting to DOWN_FOR_OTHER.
                    break

                if event_time > state.time:
                    # Go further back, we're not there yet.
                    if event_index == 0:
                        # As above - we weirdly can't find a relevant event.
                        break

                    event_index -= 1
                    continue

                # Okay, we're now looking at the event that immediately preceded the DOWN state.
                if event.type == EventType.DETONATE_NUKE:
                    new_state = PlayerStateDetailType.DOWN_NUKED
                elif event.arguments[1] == " zaps ":
                    new_state = PlayerStateDetailType.DOWN_ZAPPED
                elif event.arguments[1] == " missiles ":
                    new_state = PlayerStateDetailType.DOWN_MISSILED
                elif event.arguments[1] == " resupplies ":
                    new_state = PlayerStateDetailType.DOWN_FOR_RESUP
                break

        result.append(PlayerStateEvent(timestamp_millis=state.time, state=new_state))

    # Finally, add a sentinel at the end so we count the time between the last state change and
    # the end of the game. We need to use EntityEnds.time, not the MISSION_END time, in case the entity
    # got eliminated.
    result.append(PlayerStateEvent(timestamp_millis=entity_end.time, state=None))

    return result


async def get_player_state_distribution(entity_start: EntityStarts,
                                        entity_end: EntityEnds,
                                        player_states: ManyToManyRelation,
                                        events: ManyToManyRelation,
                                        label_map: dict[PlayerStateDetailType, str]) -> dict[str, int]:
    """Creates a distribution of how much time an entity spent in each state.

    Returns a dict with a display name for the state (as defined in label_map) and the time spent in that
    state in milliseconds.

    States for which there is no entry in label_map will be ignored.

     Args:
        entity_start: EntityStarts object for this entity.
        entity_end: EntityEnds object for this entity.
        player_states: The player_states object from the game model.
        events: The events object from the game model.
        label_map: Mapping from a state to a string. If the same string is used for multiple states, all times
            will be merged into the same string.
    """
    timeline = await get_player_state_timeline(entity_start, entity_end, player_states, events)

    result = {}

    last_state = None
    last_timestamp = 0

    def _add_player_state(state: PlayerStateDetailType, duration_millis: int):
        # Ignore states that are not in the label map.
        if state not in label_map:
            return
        label = label_map[state]
        result[label] = result.get(label, 0) + duration_millis

    for state in timeline:
        if last_state is not None:
            _add_player_state(last_state, state.timestamp_millis - last_timestamp)

        last_state = state.state
        last_timestamp = state.timestamp_millis

    return result


def get_player_state_distribution_pie_chart(distribution: dict[str, int],
                                            state_color_map: dict[str, str]) -> PieChartData:
    """Takes state distribution data from get_player_state_distribution() and turns it into pie chart data."""
    return PieChartData(
        labels=list(distribution.keys()),
        colors=[state_color_map[state] for state in distribution.keys()],
        data=list(distribution.values())
    )


def sort_notable_events(events: list[NotableEvent]):
    """Sorts a list of notable events in place."""
    events.sort(key=lambda event: event.seconds)

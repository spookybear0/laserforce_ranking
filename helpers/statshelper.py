from typing import List, Tuple, Optional, Callable, Any
from sentry_sdk import Hub, start_transaction
from tortoise.expressions import Q
from tortoise.fields import ManyToManyRelation


from db.sm5 import SM5Game, SM5Stats
from db.laserball import LaserballGame, LaserballStats
from db.types import IntRole, EventType, PlayerStateDetailType, PlayerStateType, PlayerStateEvent
from db.game import EntityEnds, EntityStarts
from tortoise.functions import Sum

# stats helpers

"""

General helpers

"""

"""Max duration between an event and its resulting changes (like state change) in related tables.

For example, this is the lost duration for which we would consider a state change to "DOWN"
to be the effect of a preceding "missiled" event.
This is typically less than 20ms. We're using 50 here just in case there is a bit of lag.
"""
_EVENT_LATENCY_THRESHOLD_MILLIS = 50

def _millis_to_time(milliseconds: Optional[int]) -> str:
    """Converts milliseconds into an MM:SS string."""
    if milliseconds is None:
        return "00:00"

    return "%02d:%02d" % (milliseconds / 60000, milliseconds % 60000 / 1000)

"""

Average score at time

"""

async def get_average_red_score_at_time_sm5(time: int) -> int:
    """
    Gets the average red score at a given time
    by going through all games and finding the
    average red score at the given time
    """

    scores = []

    for game in await SM5Game.all():
        scores.append(await game.get_red_score_at_time(time))

    return sum(scores) // len(scores)

async def get_average_green_score_at_time_sm5(time: int) -> int:
    """
    Gets the average green score at a given time
    by going through all games and finding the
    average green score at the given time
    """

    scores = []

    for game in await SM5Game.all():
        scores.append(await game.get_green_score_at_time(time))

    return sum(scores) // len(scores)

"""

More specific stats

"""

async def count_zaps(game: SM5Game, zapping_entity_id: str, zapped_entity_id: str) -> int:
    """Returns the number of times one entity zapped another."""
    return await (game.events.filter(
        arguments__filter={"0": zapping_entity_id}
    ).filter(
        arguments__filter={"1": " zaps "}
    ).filter(
        arguments__filter={"2": zapped_entity_id}
    ).count())


async def count_blocks(game: LaserballGame, zapping_entity_id: str, zapped_entity_id: str) -> int:
    """Returns the number of times one entity blocked another."""
    return await (game.events.filter(
        arguments__filter={"0": zapping_entity_id}
    ).filter(
        arguments__filter={"1": " blocks "}
    ).filter(
        arguments__filter={"2": zapped_entity_id}
    ).count())


async def count_missiles(game: SM5Game, missiling_entity_id: str, missiled_entity_id: str) -> int:
    """Returns the number of times one entity missiled another."""
    return await (game.events.filter(
        arguments__filter={"0": missiling_entity_id}
    ).filter(
        arguments__filter={"1": " missiles "}
    ).filter(
        arguments__filter={"2": missiled_entity_id}
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

    for entity in await EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines").all():
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

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("goals")).values_list("sum", flat=True))

async def get_assists() -> int:
    """
    Gets the total assists by going through
    all games and adding up the total assists

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("assists")).values_list("sum", flat=True))

async def get_passes() -> int:
    """
    Gets the total passes by going through
    all games and adding up the total passes

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("passes")).values_list("sum", flat=True))

async def get_steals() -> int:
    """
    Gets the total steals by going through
    all games and adding up the total steals

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("steals")).values_list("sum", flat=True))

async def get_clears() -> int:
    """
    Gets the total clears by going through
    all games and adding up the total clears

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("clears")).values_list("sum", flat=True))

async def get_blocks() -> int:
    """
    Gets the total blocks by going through
    all games and adding up the total blocks

    (Laserball)
    """

    return sum(await LaserballStats.filter(laserballgames__ranked=True).annotate(sum=Sum("blocks")).values_list("sum", flat=True))

# top roles
# could be improved by accounting for the amount of games played
# could be combined into one function

async def get_top_commanders(amount=5) -> List[Tuple[str, int]]:
    """
    Gets the top commanders by going through
    all games and getting the average score
    for each player
    """

    data = {}

    async for entity_end in EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines", entity__role=IntRole.COMMANDER).prefetch_related("entity"):
        codename = entity_end.entity.name
        if data.get(codename):
            data[codename] = (data[codename][0]+entity_end.score, data[codename][1]+1)
        else:
            data[codename] = (entity_end.score, 1)

    # get the average score for each player

    commanders = []

    for key, value in data.items():
        commanders.append((key, value[0]//value[1], value[1]))
    
    # sort the list by score

    commanders.sort(key=lambda x: x[1], reverse=True)

    return commanders[:amount]
    

async def get_top_heavies(amount=5) -> List[Tuple[str, int]]:
    """
    Gets the top heavies by going through
    all games and getting the average score
    for each player
    """

    data = {}

    async for entity_end in EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines", entity__role=IntRole.HEAVY).prefetch_related("entity"):
        codename = entity_end.entity.name
        if data.get(codename):
            data[codename] = (data[codename][0]+entity_end.score, data[codename][1]+1)
        else:
            data[codename] = (entity_end.score, 1)

    # get the average score for each player

    heavies = []

    for key, value in data.items():
        heavies.append((key, value[0]//value[1], value[1]))
    
    # sort the list by score

    heavies.sort(key=lambda x: x[1], reverse=True)

    return heavies[:amount]

async def get_top_scouts(amount=5) -> List[Tuple[str, int]]:
    """
    Gets the top scouts by going through
    all games and getting the average score
    for each player
    """

    data = {}

    async for entity_end in EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines", entity__role=IntRole.SCOUT).prefetch_related("entity"):
        codename = entity_end.entity.name
        if data.get(codename):
            data[codename] = (data[codename][0]+entity_end.score, data[codename][1]+1)
        else:
            data[codename] = (entity_end.score, 1)

    # get the average score for each player

    scouts = []

    for key, value in data.items():
        scouts.append((key, value[0]//value[1], value[1]))
    
    # sort the list by score

    scouts.sort(key=lambda x: x[1], reverse=True)

    return scouts[:amount]

async def get_top_ammos(amount=5) -> List[Tuple[str, int]]:
    """
    Gets the top ammos by going through
    all games and getting the average score
    for each player
    """

    data = {}

    async for entity_end in EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines", entity__role=IntRole.AMMO).prefetch_related("entity"):
        codename = entity_end.entity.name
        if data.get(codename):
            data[codename] = (data[codename][0]+entity_end.score, data[codename][1]+1)
        else:
            data[codename] = (entity_end.score, 1)

    # get the average score for each player

    ammos = []

    for key, value in data.items():
        ammos.append((key, value[0]//value[1], value[1]))
    
    # sort the list by score

    ammos.sort(key=lambda x: x[1], reverse=True)

    return ammos[:amount]

async def get_top_medics(amount=5) -> List[Tuple[str, int]]:
    """
    Gets the top medics by going through
    all games and getting the average score
    for each player
    """

    data = {}

    async for entity_end in EntityEnds.filter(sm5games__ranked=True, sm5games__mission_name__icontains="space marines", entity__role=IntRole.MEDIC).prefetch_related("entity"):
        codename = entity_end.entity.name
        
        if data.get(codename):
            data[codename] = (data[codename][0]+entity_end.score, data[codename][1]+1)
        else:
            data[codename] = (entity_end.score, 1)

    # get the average score for each player

    medics = []

    for key, value in data.items():
        medics.append((key, value[0]//value[1], value[1]))
    
    # sort the list by score

    medics.sort(key=lambda x: x[1], reverse=True)

    return medics[:amount]

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
        red_score, green_score = await game.get_red_score(), await game.get_green_score()

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

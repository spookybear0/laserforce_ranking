from typing import List, Tuple
from sentry_sdk import Hub, start_transaction
from db.models import SM5Game

# stats helpers

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
    

# performance helpers

def sentry_trace(func):
    """
    Async sentry tracing decorator
    """
    async def wrapper(*args, **kwargs):
        transaction = Hub.current.scope.transaction
        if transaction:
            with transaction.start_child(op=func.__name__):
                return await func(*args, **kwargs)
        else:
            with start_transaction(op=func.__name__, name=func.__name__):
                return await func(*args, **kwargs)

    return wrapper
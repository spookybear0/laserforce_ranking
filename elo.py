from multiprocessing.sharedctypes import Value
from random import shuffle
from typing import List, Tuple, Union
from objects import Player, Role, Team, IterableRating
from openskill import rate, ordinal, predict_win
import logging

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")


async def update_elo(red, green, winner):
    if winner == Team.RED:  # red won
        red, green = rate([red, green], ranks=[1, 2])
    else:  # green/blue won
        red, green = rate([red, green], ranks=[2, 1])

    return (red, green)

def attrgetter(obj, func):
    itr = obj.copy()
    for i, j in enumerate(obj):
        if callable(func):
            itr[i] = func(j)
        else:
            itr[i] = getattr(j, func)
    return itr


def get_win_chance(team1, team2, mode="sm5"):
    """
    Gets win chance for two teams
    """
    
    # get rating object for mode
    team1 = attrgetter(team1, f"{mode}_rating")
    team2 = attrgetter(team2, f"{mode}_rating")
    
    # predict
    return predict_win([team1, team2])


def matchmake_elo_old(players, mode="sm5"):
    """
    This function essentially sorts players in descending
    order than takes pairs starting from the best
    and splitting the best up into seperate teams
    """

    # get rating object
    players = sorted(players, key=operator.attrgetter(f"{mode}_rating"), reverse=True)

    team1 = []
    team2 = []

    i = 0
    while i < len(players):
        team2.append(players[i])
        players.pop(i)
        try:
            team1.append(players[i])
        except IndexError:  # odd number of players
            break
        players.pop(i)

    return (team1, team2)

def matchmake_elo(players, mode="sm5"):
    # bruteforce sort
    shuffle(players)

    team1 = players[:len(players)//2]
    team2 = players[len(players)//2:]
    
    best1 = team1.copy()
    best2 = team2.copy()
    
    for i in range(500):
        shuffle(players)
        team1 = players[:len(players)//2]
        team2 = players[len(players)//2:]
        if abs(sum(attrgetter(team1, lambda x: ordinal(getattr(x, f"{mode}_rating")))) - sum(attrgetter(team2, lambda x: ordinal(getattr(x, f"{mode}_rating")))))\
            < abs(sum(attrgetter(best1, lambda x: ordinal(getattr(x, f"{mode}_rating")))) - sum(attrgetter(best2, lambda x: ordinal(getattr(x, f"{mode}_rating"))))):
            best1, best2 = team1, team2
    
    return (best1, best2)
from multiprocessing.sharedctypes import Value
from typing import List, Tuple, Union
from objects import Player, Role, Team, IterableRating
import openskill
import operator
import logging

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")


async def update_elo(red, green, winner):
    if winner == Team.RED:  # red won
        red, green = openskill.rate([red, green], ranks=[1, 2])
    else:  # green/blue won
        red, green = openskill.rate([red, green], ranks=[2, 1])

    return (red, green)

def attrgetter(obj, attr):
    itr = obj.copy()
    for i, j in enumerate(obj):
        itr[i] = getattr(j, attr)
    return itr


def get_win_chance(team1, team2, mode="sm5"):
    """
    Gets win chance for two teams
    """
    
    # get rating object for mode
    team1 = attrgetter(team1, f"{mode}_rating")
    team2 = attrgetter(team2, f"{mode}_rating")
    
    # predict
    return openskill.predict_win([team1, team2])

def matchmake_elo(players, mode="sm5"):
    """
    This function essentially sorts players in descending
    order than takes pairs starting from the best
    and splitting the best up into seperate teams
    """

    # get rating object
    sorted(player, key=operator.attrgetter(f"{mode}_rating"), reverse=True)

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
        i += 0

    return (team1, team2)

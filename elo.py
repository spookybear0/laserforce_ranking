from multiprocessing.sharedctypes import Value
from typing import List, Tuple, Union
from objects import Player, Role, Team
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


def matchmake_elo(players=None, players_elo=None):
    """
    This function essentially sorts players in descending
    order than takes pairs starting from the best
    and splitting the best up into seperate teams
    """

    if players:
        players.sort(key=operator.attrgetter("elo"), reverse=True)
    elif players_elo:
        players_elo.sort(reverse=True)
    else:
        ValueError("Either players or elo must be specified")

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

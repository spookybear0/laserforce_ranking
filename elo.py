from typing import List, Tuple, Union
import operator
from objects import Player, Role
import logging

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

async def update_elo(team1, team2, winner: int):
    
    
    return (team1, team2)

def matchmake_elo(players):
    """
    This function essentially sorts players in descending
    order than takes pairs starting from the best
    and splitting the best up into seperate teams
    """
    
    players.sort(key=operator.attrgetter("elo"), reverse=True)
    
    team1 = []
    team2 = []
    
    i = 0
    while i < len(players):
        team2.append(players[i])
        players.pop(i)
        try:
            team1.append(players[i])
        except IndexError: # odd number of players
            break
        players.pop(i)
        i += 0
    
    return (team1, team2)

def matchmake_elo_from_elo(players_elo):
    """
    This function essentially sorts players in descending
    order than takes pairs starting from the best
    and splitting the best up into seperate teams
    (uses elo instead of player object)
    """
    
    players_elo.sort(reverse=True)
    
    team1 = []
    team2 = []
    
    i = 0
    while i < len(players_elo):
        team2.append(players_elo[i])
        players_elo.pop(i)
        try:
            team1.append(players_elo[i])
        except IndexError: # odd number of players
            break
        players_elo.pop(i)
        i += 0
    
    return (team1, team2)
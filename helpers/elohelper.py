from objects import Game, GameType
from random import shuffle
import openskill

def attrgetter(obj, func):
    itr = obj.copy()
    for i, j in enumerate(obj):
        if callable(func):
            itr[i] = func(j)
        else:
            itr[i] = getattr(j, func)
    return itr

async def update_elo(red, green, winner, mode: GameType=GameType.SM5):
    red = attrgetter(red, f"{mode}_rating")
    green = attrgetter(green, f"{mode}_rating")
    
    if winner == Team.RED:  # red won
        red, green = openskill.rate([red, green], ranks=[1, 2])
    else:  # green/blue won
        red, green = openskill.rate([red, green], ranks=[2, 1])

    return (red, green)

def get_win_chance(team1, team2, mode: GameType=GameType.SM5):
    """
    Gets win chance for two teams
    """
    mode = mode.value
    # get rating object for mode
    team1 = attrgetter(team1, f"{mode}_rating")
    team2 = attrgetter(team2, f"{mode}_rating")
    
    # predict
    return openskill.predict_win([team1, team2])

def matchmake_elo(players, mode: GameType=GameType.SM5):
    mode = mode.value
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
        # woah
        if abs(sum(attrgetter(team1, lambda x: getattr(x, f"{mode}_ordinal"))) - sum(attrgetter(team2, lambda x: getattr(x, f"{mode}_ordinal"))))\
            < abs(sum(attrgetter(best1, lambda x: getattr(x, f"{mode}_ordinal"))) - sum(attrgetter(best2, lambda x: getattr(x, f"{mode}_ordinal")))):
            best1, best2 = team1, team2
    
    return (best1, best2)
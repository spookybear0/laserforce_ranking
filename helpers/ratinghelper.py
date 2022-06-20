from objects import GameType, Team, LaserballGamePlayer, Player
from random import shuffle
import openskill

def calculate_laserball_mvp_points(player: LaserballGamePlayer):
    mvp_points = 0

    mvp_points += player.goals   * 1
    mvp_points += player.assists * 0.75
    mvp_points += player.steals  * 0.5
    mvp_points += player.clears  * 0.25 # clear implies a steal so the total gained is 0.75
    mvp_points += player.blocks  * 0.3

    return mvp_points

# different than operator.attrgetter (legacy code)
def attrgetter(obj, func):
    itr = obj.copy()
    for i, j in enumerate(obj):
        if callable(func):
            itr[i] = func(j)
        else:
            itr[i] = getattr(j, func)
    return itr

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

# team1 is red, team2 is green/blue
async def update_elo(team1, team2, winner, mode: GameType):
    mode = mode.value.lower()
    
    team1_mu = attrgetter(team1, f"{mode}_mu")
    team1_sigma = attrgetter(team1, f"{mode}_sigma")
    
    team2_mu = attrgetter(team2, f"{mode}_mu")
    team2_sigma = attrgetter(team2, f"{mode}_sigma")
    
    # convert to Rating
    team1_rating = []
    for i in range(len(team1)):
        team1_rating.append(openskill.Rating(team1_mu[i], team1_sigma[i]))
    
    team2_rating = []
    for i in range(len(team2)):
        team2_rating.append(openskill.Rating(team2_mu[i], team2_sigma[i]))
        
    
    if winner == Team.RED:  # red won
        team1_rating, team2_rating = openskill.rate([team1_rating, team2_rating], ranks=[1, 2])
    else:  # green/blue won
        team1_rating, team2_rating = openskill.rate([team1_rating, team2_rating], ranks=[2, 1])
        
    # convert back to Player 
    for i, p in enumerate(team1):
        setattr(p, f"{mode}_mu", team1_rating[i])
        
    for i, p in enumerate(team2):
        setattr(p, f"{mode}_mu", team2_rating[i])

    return (team1, team2)
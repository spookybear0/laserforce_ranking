from objects import GameType, Team
import openskill

# different than operator.attrgetter (legacy code)
def attrgetter(obj, func):
    itr = obj.copy()
    for i, j in enumerate(obj):
        if callable(func):
            itr[i] = func(j)
        else:
            itr[i] = getattr(j, func)
    return itr

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
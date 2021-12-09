from typing import List, Tuple, Union
import operator

def get_team_elo(team):
    elo_sum = 0
    for p in team:
        try:
            elo_sum += p.elo
        except:
            elo_sum += p
    
    return elo_sum / len(team)

def get_win_chance(team1, team2):
    elo1 = get_team_elo(team1)
    elo2 = get_team_elo(team2)

    expected1 = round(elo1 / (elo1 + elo2), 3)
    expected2 = round(elo2 / (elo1 + elo2), 3)
    return (expected1, expected2)

# elo split
#
# scout: 30%
# heavy: 20%
# commander: 30%
# ammo: 10%
# medic: 10%

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

def update_elo(team1, team2, winner: int, k: int=512):
    # k value = intensity on elo on each game higher = more elo won/lost each game
    
    # get average elo of team
    
    elo1 = get_team_elo(team1)
    elo2 = get_team_elo(team2)

    expected1 = elo1 / (elo1 + elo2)
    expected2 = elo2 / (elo1 + elo2)
    
    # get which team won
    if winner == 0:
        score1 = 1
        score2 = 0
    elif winner == 1:
        score1 = 0
        score2 = 1
    
    final1 = elo1 + k * (score1 - expected1)
    final2 = elo1 + k * (score2 - expected2)
    
    # split elo along each player
    
    for p in team1:
        p.elo = round((final1 - elo1) / len(team1) + p.elo)
        
    for p in team2:
        p.elo = round((final2 - elo2) / len(team2) + p.elo)
    
    return (team1, team2)

#team1 = [1100, 1200, 1200, 1200, 1200, 1200]
#team2 = [1200, 1200, 1200, 1200, 1200, 1200]
#a = update_elo(team1, team2, 0)
#b = get_win_chance(team1, team2)
#print(a)
#print(b)
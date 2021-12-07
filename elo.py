from typing import List, Tuple, Union
    

def get_team_elo(team):
    elo_sum = 0
    for p in team:
        elo_sum += p.elo
    
    return elo_sum / len(team)

def get_win_chance(team1, team2):
    elo1 = get_team_elo(team1)
    elo2 = get_team_elo(team2)

    expected1 = round(elo1 / (elo1 + elo2), 3)
    expected2 = round(elo2 / (elo1 + elo2), 3)
    return (expected1, expected2)

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
    newlist1 = []
    newlist2 = []
    
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
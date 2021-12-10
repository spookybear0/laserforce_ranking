from typing import List, Tuple, Union
import operator
from objects import Player, Role

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

    expected1 = round(elo1 / (elo1 + elo2))
    expected2 = round(elo2 / (elo1 + elo2))
    return (expected1, expected2)

# elo split
# (remember to convert to int after)
#
# scout: expected: 4500, *2.2
# heavy: 7000, *1.42
# commander: expected: 10000, *1
# ammo: expected: 2500, *4
# medic: expected: 1500, *6.66

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
    
    # change in elo
    change1 = k * (score1 - expected1)
    change2 = k * (score2 - expected2)
    
    # split elo along each player depending on role and performance
    
    def update_team_elo(team, change, team_value: int):
        total_adj_score = 0
        for p in team: # first loop to get total score
            # get nessacary variables
            score = p.game_player.score
            role = p.game_player.role
            
            # prepare to even out score
            multiplier = 1
            
            # keep score values similar and buff worse roles to commanders level
            if role == Role.SCOUT:
                multiplier = 2.2
            elif role == Role.HEAVY:
                multiplier = 1.42
            elif role == Role.COMMANDER:
                multiplier = 1
            elif role == Role.AMMO:
                multiplier = 4
            elif role == Role.MEDIC:
                multiplier = 6.66
            
            if score < 0: # negatives will mess with the multiplier so just set score to 0 if its an negative value
                score = 0
            adj_score = score*multiplier
            p.game_player.adj_score = adj_score
            
            total_adj_score += adj_score # even out score, used for dividend/divisor
        
        for p in team: # second loop to update elo
            
            # use adj score to determine how much elo each player gets by seeing how much they contributed (adjusted)
            adj_score = p.game_player.adj_score

            if team_value == winner: # team won
                p.elo += change * (adj_score / total_adj_score)
            else: # team lost
                p.elo += change * ((total_adj_score / adj_score)/25) # /25 is something that works good for better players losing less on the losing team
            p.elo = round(p.elo)

    update_team_elo(team1, change1, 0)
    update_team_elo(team2, change2, 1)
    
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

#team1 = [1100, 1200, 1200, 1200, 1200, 1200]
#team2 = [1200, 1200, 1200, 1200, 1200, 1200]
#a = update_elo(team1, team2, 0)
#b = get_win_chance(team1, team2)
#print(a)
#print(b)
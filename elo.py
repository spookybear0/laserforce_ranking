from typing import List, Tuple, Union
import operator
from objects import Player, Role
import logging

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

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

async def update_elo(team1, team2, winner: int, k: int=512):
    from helpers import get_average_score
    # k value = intensity on elo on each game higher = more elo won/lost each game
    
    # get average elo of team
    elo_logger.debug("Getting average elo of team")
    elo1 = get_team_elo(team1)
    elo2 = get_team_elo(team2)

    elo_logger.debug("Getting expected win chance of teams")
    expected1 = elo1 / (elo1 + elo2)
    expected2 = elo2 / (elo1 + elo2)
    
    # get which team won
    if winner == 0:
        score1 = 1
        score2 = 0
    elif winner == 1:
        score1 = 0
        score2 = 1
    
    elo_logger.debug("Using elo formula to see the change in elo for both teams")
    # change in elo
    change1 = k * (score1 - expected1)
    change2 = k * (score2 - expected2)
    elo_logger.debug(f"Team 1: {change1} Team 2: {change2}")
    
    # split elo along each player depending on role and performance
    
    elo_logger.debug("Splitting elo between players based on performance and role")
    async def update_team_elo(team, change, team_value: int):
        total_adj_score = 0
        team_elo = 0
        for p in team: # first loop to get total score
            # get nessacary variables
            score = p.game_player.score
            role = p.game_player.role
            
            # keep score values similar and buff worse roles to commanders level (aka mvp points)
            commander_avg = await get_average_score(Role.COMMANDER)
            my_role_avg = await get_average_score(role)
            multiplier = commander_avg / my_role_avg
            
            if score < 0: # negatives will mess with the multiplier so just set score to 0 if its an negative value
                score = 20 # to avoid division by zero
                
            adj_score = score*multiplier
            p.game_player.adj_score = adj_score
            
            total_adj_score += adj_score # even out score, used for dividend/divisor
            
            team_elo += p.elo # get team total elo for elo performance calculations
        
        for p in team: # second loop to update elo
            
            # use adj score to determine how much elo each player gets by seeing how much they contributed (adjusted)
            adj_score = p.game_player.adj_score

            if team_value == winner: # team won
                # how much contributed to team
                # and adjust change with how good the player actually is compared to team
                elo = change * (adj_score / total_adj_score) + (change * (1-(p.elo / (team_elo / len(team)))))
                p.elo += elo
                elo_logger.debug(f"{p.codename} won and elo was changed by {elo}")
            else: # team lost
                # 1-% contributed to team = adjusted for loss instead of win
                # and adjust change with how good the player actually is compared to team
                elo = change * (1-(adj_score / total_adj_score)) + (change * (p.elo / (team_elo / len(team))))
                if elo < change:
                    elo = change
                p.elo += elo
                elo_logger.debug(f"{p.codename} lost and elo was changed by {elo}")
            p.elo = round(p.elo)

    elo_logger.debug(f"Updating team 1's elo")
    await update_team_elo(team1, change1, 0)
    elo_logger.debug(f"Updating team 2's elo")
    await update_team_elo(team2, change2, 1)
    
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
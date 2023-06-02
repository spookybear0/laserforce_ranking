from objects import GameType, Team, LaserballGamePlayer, Player, Game
from random import shuffle
import openskill
import math
from scipy.stats import norm

### TS 2

cdf = norm.cdf

beta = 25 / 6
tau = 1 / 300

def win_probability(team1, team2, mode: str="sm5"):
    delta_mu = sum(getattr(player, f"{mode}_mu") for player in team1) - sum(getattr(player, f"{mode}_mu") for player in team2)
    sum_sigma = sum(getattr(player, f"{mode}_sigma") ** 2 for player in team1) + sum(getattr(player, f"{mode}_sigma") ** 2 for player in team2)
    size = len(team1) + len(team2)
    denominator = math.sqrt(size * (beta ** 2) + sum_sigma)
    return cdf(delta_mu / denominator)

def update_team_ratings(team1, team2, winner, mode: str, K):
    ranks = [1, 0] if team1 == winner else [0, 1]
    delta_mu = sum(getattr(player, f"{mode}_mu") for player in team1) - sum(getattr(player, f"{mode}_mu") for player in team2)
    sum_sigma = sum(getattr(player, f"{mode}_sigma") ** 2 for player in team1) + sum(getattr(player, f"{mode}_sigma") ** 2 for player in team2)
    size = len(team1) + len(team2)
    denominator = math.sqrt(size * (beta ** 2) + sum_sigma)
    team1_perf = sum(player.performance for player in team1)
    team2_perf = sum(player.performance for player in team2)
    team1_quality = (team1_perf / (team1_perf + team2_perf)) if (team1_perf + team2_perf) != 0 else 0.5
    team2_quality = (team2_perf / (team1_perf + team2_perf)) if (team1_perf + team2_perf) != 0 else 0.5
    player_updates = []
    for player in team1 + team2:
        if player in team1:
            rank = ranks[0]
            quality = team1_quality
        else:
            rank = ranks[1]
            quality = team2_quality

        # performance multiplier
        # example: a player has 0.75 performance, so they get 75% of the performance of the team
        # this will change depending on the team won
        # for example if their team won, the multiplier will be 
        if player.game_player.team == winner:
            perf_mult = player.performance + 1
        else:
            perf_mult = -player.performance + 1
        
        new_mu = getattr(player, f"{mode}_mu") + K * quality * 50 * (rank - win_probability(team1, team2, mode)) * perf_mult

        new_sigma = math.sqrt((1 - K * quality) * getattr(player, f"{mode}_sigma") ** 2 + K * quality * (1 - quality) * delta_mu ** 2 / denominator)

        player_updates.append((player, new_mu, new_sigma))
    return player_updates

def update_game_ratings(team1, team2, winner_team: Team, mode: str="sm5"):
    if winner_team == Team.RED:
        winner = 0
    else:
        winner = 1
    
    teams = [team1, team2]

    K = 0.1

    player_updates = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            team1 = teams[i]
            team2 = teams[j]

            player_updates += update_team_ratings(team1, team2, winner, mode, K)
    for player, new_mu, new_sigma in player_updates:
        setattr(player, f"{mode}_mu", float(new_mu))
        setattr(player, f"{mode}_sigma", float(new_sigma))

### END TS 2

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
    ret = []
    for i in obj:
        if callable(func):
            ret.append(func(i))
        elif isinstance(func, int):
            ret.append(i[func])
        else:
            ret.append(getattr(i, func))
    return ret

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

def get_draw_chance(team1, team2, mode: GameType=GameType.SM5):
    """
    Gets draw chance for two teams
    """
    mode = mode.value
    # get rating object for mode
    team1 = attrgetter(team1, f"{mode}_rating")
    team2 = attrgetter(team2, f"{mode}_rating")
    
    # predict
    return openskill.predict_draw([team1, team2])

def matchmake_elo(players, mode: GameType=GameType.SM5):
    mode = mode.value
    # bruteforce sort

    team1 = players[:len(players)//2]
    team2 = players[len(players)//2:]
    
    best1 = team1.copy()
    best2 = team2.copy()
    
    # gets most fair teams
    for i in range(500):
        shuffle(players)
        team1 = players[:len(players)//2]
        team2 = players[len(players)//2:]
        # checks if teams are more fair then previous best
        if abs(sum(attrgetter(team1, lambda x: getattr(x, f"{mode}_ordinal"))) - sum(attrgetter(team2, lambda x: getattr(x, f"{mode}_ordinal"))))\
            < abs(sum(attrgetter(best1, lambda x: getattr(x, f"{mode}_ordinal"))) - sum(attrgetter(best2, lambda x: getattr(x, f"{mode}_ordinal")))):
            best1, best2 = team1, team2
    
    return (best1, best2)

# team1 is red, team2 is green/blue
async def update_elo(game: Game, mode: GameType):
    mode = mode.value.lower()
    
    winner = game.winner
    
    team1 = game.red
    
    if mode == "sm5":
        team2 = game.green
    else: # laserball
        team2 = game.blue

    for player in team1:
        player.performance = player.game_player.score / game.get_team_score(player.game_player.team)

    for player in team2:
        player.performance = player.game_player.score / game.get_team_score(player.game_player.team)

    update_game_ratings(team1, team2, winner, mode)

    return (team1, team2)
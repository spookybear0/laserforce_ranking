from trueskill import Rating, TrueSkill, BETA, rate
import itertools
import math

ts = TrueSkill(backend="mpmath")

def get_ts_win_chance(team1, team2):
    delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma = sum(r.sigma ** 2 for r in itertools.chain(team1, team2))
    size = len(team1) + len(team2)
    denom = math.sqrt(size * (BETA * BETA) + sum_sigma)
    return ts.cdf(delta_mu / denom)

def update_ts(team1, team2, winner: int):
    if winner:
        won1 = 1
        won2 = 0
    else:
        won1 = 0
        won2 = 1
    
    return rate([team1, team2], [won1, won2])

a = [Rating()]
b = [Rating()]

print(update_ts(a, b, 0))
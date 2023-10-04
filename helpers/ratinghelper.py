from objects import Team, LaserballGamePlayer
from random import shuffle
from openskill import Rating, rate, ordinal, predict_draw, predict_win
import math
from scipy.stats import norm
from sanic.log import logger
from typing import List, Tuple
from db.models import SM5Game, Events, EntityStarts, EventType, Player, EntityEnds, LaserballGame
from objects import GameType
from helpers import userhelper
import time

def calculate_laserball_mvp_points(player: LaserballGamePlayer):
    mvp_points = 0

    mvp_points += player.goals   * 1
    mvp_points += player.assists * 0.75
    mvp_points += player.steals  * 0.5
    mvp_points += player.clears  * 0.25 # clear implies a steal so the total gained is 0.75
    mvp_points += player.blocks  * 0.3

    return mvp_points

async def rate_encounter(player1, player2, weight: float, rank=None):
    if rank is None:
        rank = [0, 1]

    player1_new, player2_new = rate([[player1], [player2]], rank=rank)

    player1_new = player1_new[0]
    player2_new = player2_new[0]

    player1_change = player1_new.mu - player1.mu
    player2_change = player2_new.mu - player2.mu

    player1_new.mu = player1_change * weight + player1.mu
    player2_new.mu = player2_change * weight + player2.mu

    return player1_new, player2_new


# sm5 elo helper functions

async def rate_sm5_game(game: SM5Game, team1_rating: List[Tuple[Rating, Rating]], team2_rating: List[Tuple[Rating, Rating]], rank=None):
    if rank is None:
        rank = [0, 1]
    
    
    team1 = list(map(lambda x: x[3], team1_rating))
    team2 = list(map(lambda x: x[3], team2_rating))

    team1_new, team2_new = rate([team1, team2], rank=rank)

    # get the change in mu for each player then apply weights

    team1_change = list(map(lambda x: x[0].mu - x[1].mu, zip(team1_new, team1)))
    team2_change = list(map(lambda x: x[0].mu - x[1].mu, zip(team2_new, team2)))

    # apply weights

    team1_final = []
    team2_final = []

    # update this to add the rating_chance to entity_ends

    if rank == [0, 1]:
        for i in range(len(team1_change)):
            # winning team
            team1_change[i] *= team1_rating[i][0].mu/team1_rating[i][1].mu + 1
            team1_final.append(Rating(team1_new[i].mu + team1_change[i], team1_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team1_rating[i][2].entity_id).update(current_rating_mu=team1_new[i].mu + team1_change[i], current_rating_sigma=team1_new[i].sigma)
        for i in range(len(team2_change)):
            # losing team
            team2_change[i] *= team2_rating[i][1].mu/team2_rating[i][0].mu
            team2_final.append(Rating(team2_new[i].mu + team2_change[i], team2_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team2_rating[i][2].entity_id).update(current_rating_mu=team2_new[i].mu + team2_change[i], current_rating_sigma=team2_new[i].sigma)
    else:
        for i in range(len(team1_change)):
            # losing team
            team1_change[i] *= team1_rating[i][0].mu/team1_rating[i][0].mu
            team1_final.append(Rating(team1_new[i].mu + team1_change[i], team1_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team1_rating[i][2].entity_id).update(current_rating_mu=team1_new[i].mu + team1_change[i], current_rating_sigma=team1_new[i].sigma)
        for i in range(len(team2_change)):
            # winning team
            team2_change[i] *= team2_rating[i][0].mu/team2_rating[i][1].mu + 1
            team2_final.append(Rating(team2_new[i].mu + team2_change[i], team2_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team2_rating[i][2].entity_id).update(current_rating_mu=team2_new[i].mu + team2_change[i], current_rating_sigma=team2_new[i].sigma)

    return team1_final, team2_final

async def update_sm5_ratings(game: SM5Game) -> bool:
    """
    Updates the sm5 ratings for a game
    it first calculates the individual player ratings
    then it calculates the team ratings
    then it updates the player ratings through openskill

    returns: True if successful, False if not
    it could return False if the game is not ranked
    """

    if not game.ranked:
        return False

    # calculate player encounter performance

    # get all players

    players = await game.entity_starts.filter(type="player")

    events: List[Events] = await game.events.filter(type__in=
        [EventType.DAMAGED_OPPONENT, EventType.DOWNED_OPPONENT, EventType.MISSILE_DAMAGE_OPPONENT,
        EventType.MISSILE_DOWN_OPPONENT, EventType.RESUPPLY_LIVES, EventType.RESUPPLY_AMMO]
    ).order_by("time").all() # only get the events that we need

    players_elo = {x.entity_id: Rating() for x in players}

    doubles = {}
    total_double_boost = {}

    for event in events:
        match event.type:
            case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_elo = players_elo[shooter.entity_id]
                target = await userhelper.player_from_token(game, event.arguments[2])
                target_elo = players_elo[target.entity_id]

                shooter_elo, target_elo = await rate_encounter(shooter_elo, target_elo, 1, [0, 1])

                players_elo[shooter.entity_id] = shooter_elo
                players_elo[target.entity_id] = target_elo
            case EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_elo =  players_elo[shooter.entity_id]
                target = await userhelper.player_from_token(game, event.arguments[2])
                target_elo = players_elo[target.entity_id]

                shooter_elo, target_elo = await rate_encounter(shooter_elo, target_elo, 1.2, [0, 1])

                players_elo[shooter.entity_id] = shooter_elo
                players_elo[target.entity_id] = target_elo
            case EventType.RESUPPLY_AMMO | EventType.RESUPPLY_LIVES:
                # check if player got doubles

                resubber = await userhelper.player_from_token(game, event.arguments[0])

                double = doubles.get((await resubber.team).index)

                if total_double_boost.get(event.arguments[0]) is None:
                    total_double_boost[event.arguments[0]] = 0

                if not double:
                    doubles[(await resubber.team).index] = {resubber.entity_id: [event.time, event.arguments[2]]}
                elif len(double) == 1:
                    # check if it's close enough to be a double
                    other_time = double[list(double.keys())[0]][0]
                    other_resubbe = double[list(double.keys())[0]][1]

                    if abs(other_time - event.time) > 2000 or event.arguments[2] != other_resubbe: # 2 seconds
                        # not a double
                        doubles[(await resubber.team).index] = {}
                        continue

                    boost = (-0.1*total_double_boost[event.arguments[0]]) + 0.5

                    players_elo[resubber.entity_id].mu += boost
                    players_elo[list(double.keys())[0]].mu += boost

                    total_double_boost[event.arguments[0]] += boost
                    
                    doubles[(await resubber.team).index] = {}

    players_t1 = []
    players_t2 = []
    players_rating_t1 = [] # (rating, best_player_rating)
    players_rating_t2 = []

    for player in players:
        # get the next best player that isn't this player


        best_player = None
        
        for other_player in players:
            if (await other_player.team).index != (await player.team).index:
                continue

            if best_player is None:
                best_player = other_player
                continue

            other_player_rating = ordinal((players_elo[other_player.entity_id].mu, players_elo[other_player.entity_id].sigma))
            best_player_rating = ordinal((players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma))

            if other_player_rating > best_player_rating:
                best_player = other_player

        real_player = await Player.get(ipl_id=player.entity_id)

        if (await player.team).color_name == "Fire":
            players_t1.append(await Player.get(ipl_id=player.entity_id))
            players_rating_t1.append((
                Rating(players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma),
                Rating(players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma),
                player,
                Rating(real_player.sm5_mu, real_player.sm5_sigma)
            ))
        else:
            players_t2.append(await Player.get(ipl_id=player.entity_id))
            players_rating_t2.append((
                Rating(players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma),
                Rating(players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma),
                player,
                Rating(real_player.sm5_mu, real_player.sm5_sigma)
            ))

    # update player elo

    ranks = [0, 1] if game.winner == Team.RED else [1, 0]

    team1, team2 = await rate_sm5_game(game, players_rating_t1, players_rating_t2, ranks)

    for team1_p, team1_rating in zip(players_t1, team1):
        team1_p.sm5_mu = team1_rating.mu
        team1_p.sm5_sigma = team1_rating.sigma
        await team1_p.save()

    for team2_p, team2_rating in zip(players_t2, team2):
        team2_p.sm5_mu = team2_rating.mu
        team2_p.sm5_sigma = team2_rating.sigma
        await team2_p.save()

    return True

def matchmake(players, mode: GameType=GameType.SM5):
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

        func = lambda x: getattr(x, f"{mode}_ordinal")

        # checks if teams are more fair then previous best
        if abs(sum(map(func, team1)) - sum(map(func, team2)))\
            < abs(sum(map(func, best1)) - sum(map(func, best2))):
            best1, best2 = team1, team2
    
    return (best1, best2)

def get_win_chance(team1, team2, mode: GameType=GameType.SM5):
    """
    Gets win chance for two teams
    """

    logger.debug(f"Getting win chance for {team1} vs {team2}")

    mode = mode.value
    # get rating object for mode
    team1 = list(map(lambda x: getattr(x, f"{mode}_rating"), team1))
    team2 = list(map(lambda x: getattr(x, f"{mode}_rating"), team2))
    
    # predict
    return predict_win([team1, team2])

def get_draw_chance(team1, team2, mode: GameType=GameType.SM5):
    """
    Gets draw chance for two teams
    """

    logger.debug(f"Getting draw chance for {team1} vs {team2}")

    mode = mode.value
    # get rating object for mode
    team1 = list(map(lambda x: getattr(x, f"{mode}_rating"), team1))
    team2 = list(map(lambda x: getattr(x, f"{mode}_rating"), team2))
    
    # predict
    return predict_draw([team1, team2])

# laserball elo helper functions

async def rate_laserball_game(game: LaserballGame, team1_rating: List[Tuple[Rating, Rating]], team2_rating: List[Tuple[Rating, Rating]], rank=None):
    if rank is None:
        rank = [0, 1]
    
    
    team1 = list(map(lambda x: x[3], team1_rating))
    team2 = list(map(lambda x: x[3], team2_rating))

    team1_new, team2_new = rate([team1, team2], rank=rank)

    # get the change in mu for each player then apply weights

    team1_change = list(map(lambda x: x[0].mu - x[1].mu, zip(team1_new, team1)))
    team2_change = list(map(lambda x: x[0].mu - x[1].mu, zip(team2_new, team2)))

    # apply weights

    team1_final = []
    team2_final = []

    # update this to add the rating_chance to entity_ends

    if rank == [0, 1]:
        for i in range(len(team1_change)):
            # winning team
            team1_change[i] *= team1_rating[i][0].mu/team1_rating[i][1].mu + 1
            team1_final.append(Rating(team1_new[i].mu + team1_change[i], team1_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team1_rating[i][2].entity_id).update(current_rating_mu=team1_new[i].mu + team1_change[i], current_rating_sigma=team1_new[i].sigma)
        for i in range(len(team2_change)):
            # losing team
            team2_change[i] *= team2_rating[i][1].mu/team2_rating[i][0].mu
            team2_final.append(Rating(team2_new[i].mu + team2_change[i], team2_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team2_rating[i][2].entity_id).update(current_rating_mu=team2_new[i].mu + team2_change[i], current_rating_sigma=team2_new[i].sigma)
    else:
        for i in range(len(team1_change)):
            # losing team
            team1_change[i] *= team1_rating[i][0].mu/team1_rating[i][0].mu
            team1_final.append(Rating(team1_new[i].mu + team1_change[i], team1_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team1_rating[i][2].entity_id).update(current_rating_mu=team1_new[i].mu + team1_change[i], current_rating_sigma=team1_new[i].sigma)
        for i in range(len(team2_change)):
            # winning team
            team2_change[i] *= team2_rating[i][0].mu/team2_rating[i][1].mu + 1
            team2_final.append(Rating(team2_new[i].mu + team2_change[i], team2_new[i].sigma))
            await game.entity_ends.filter(entity__entity_id=team2_rating[i][2].entity_id).update(current_rating_mu=team2_new[i].mu + team2_change[i], current_rating_sigma=team2_new[i].sigma)

    return team1_final, team2_final

async def update_laserball_ratings(game: LaserballGame) -> bool:
    """
    Updates the laserball ratings for a game
    it first calculates the individual player ratings
    then it calculates the team ratings
    then it updates the player ratings through openskill

    returns: True if successful, False if not
    it could return False if the game is not ranked
    """

    if not game.ranked:
        return False

    # calculate player encounter performance

    # get all players

    players = await game.entity_starts.filter(type="player")

    events: List[Events] = await game.events.filter(type__in=
        [EventType.GOAL, EventType.STEAL,
        EventType.CLEAR, EventType.BLOCK]
    ).order_by("time").all() # only get the events that we need

    players_elo = {x.entity_id: Rating() for x in players}

    for event in events:
        match event.type:
            case EventType.GOAL:
                scorer = await userhelper.player_from_token(game, event.arguments[0])
                scorer_elo = players_elo[scorer.entity_id]

                scorer_elo.mu += 1
            #case EventType.ASSIST:
            #    assister = await userhelper.player_from_token(game, event.arguments[0])
            #    assister_elo = players_elo[assister.entity_id]
            #
            #    assister_elo.mu += 0.75
            case EventType.STEAL:
                stealer = await userhelper.player_from_token(game, event.arguments[0])
                stealer_elo = players_elo[stealer.entity_id]

                stealer_elo.mu += 0.5
            case EventType.CLEAR:
                clearer = await userhelper.player_from_token(game, event.arguments[0])
                clearer_elo = players_elo[clearer.entity_id]

                clearer_elo.mu += 0.25
            case EventType.BLOCK:
                blocker = await userhelper.player_from_token(game, event.arguments[0])
                blocker_elo = players_elo[blocker.entity_id]

                blocker_elo.mu += 0.3

    players_t1 = []
    players_t2 = []
    players_rating_t1 = [] # (rating, best_player_rating)
    players_rating_t2 = []

    for player in players:
        # get the next best player that isn't this player


        best_player = None
        
        for other_player in players:
            if (await other_player.team).index != (await player.team).index:
                continue

            if best_player is None:
                best_player = other_player
                continue

            other_player_rating = ordinal((players_elo[other_player.entity_id].mu, players_elo[other_player.entity_id].sigma))
            best_player_rating = ordinal((players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma))

            if other_player_rating > best_player_rating:
                best_player = other_player

        real_player = await Player.get(ipl_id=player.entity_id)

        if (await player.team).color_name == "Fire":
            players_t1.append(await Player.get(ipl_id=player.entity_id))
            players_rating_t1.append((
                Rating(players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma),
                Rating(players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma),
                player,
                Rating(real_player.sm5_mu, real_player.sm5_sigma)
            ))
        else:
            players_t2.append(await Player.get(ipl_id=player.entity_id))
            players_rating_t2.append((
                Rating(players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma),
                Rating(players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma),
                player,
                Rating(real_player.sm5_mu, real_player.sm5_sigma)
            ))

    # update player elo

    ranks = [0, 1] if game.winner == Team.RED else [1, 0]

    team1, team2 = await rate_sm5_game(game, players_rating_t1, players_rating_t2, ranks)

    for team1_p, team1_rating in zip(players_t1, team1):
        team1_p.sm5_mu = team1_rating.mu
        team1_p.sm5_sigma = team1_rating.sigma
        await team1_p.save()

    for team2_p, team2_rating in zip(players_t2, team2):
        team2_p.sm5_mu = team2_rating.mu
        team2_p.sm5_sigma = team2_rating.sigma
        await team2_p.save()

    return True

import elommr

# async def update_sm5_ratings(game: SM5Game) -> bool:
#     """
#     Modified version of the other update_sm5_ratings function

#     uses elommr instead of openskill
#     """

#     mmr = elommr.EloMMR()

#     if not game.ranked:
#         return False
    
#     # create elo objects for each player

#     players = await game.entity_starts.filter(type="player")

#     players_elo = {x.entity_id: elommr.Player() for x in players}
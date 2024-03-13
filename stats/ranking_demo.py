import sys
import os

file_path = os.path.dirname(os.path.realpath(__file__))

dir_path = file_path + "\\..\\"

if dir_path not in sys.path:
    sys.path.append(dir_path)

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "\\..\\")

os.chdir(os.path.dirname(os.path.realpath(__file__)) + "\\..\\")

from db.models import Player, SM5Game, EventType, Events, EntityStarts
from db.types import Team
import openskill
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import asyncio
from tortoise import Tortoise
from config import config
from typing import List, Tuple
import time

async def player_from_token(game: SM5Game, token: str) -> EntityStarts:
    return await game.entity_starts.filter(entity_id=token).first()

async def rate_encounter(player1, player2, weight: float, rank=None):
    if rank is None:
        rank = [0, 1]

    player1_new, player2_new = openskill.rate([[player1], [player2]], rank=rank)

    player1_new = player1_new[0]
    player2_new = player2_new[0]

    player1_change = player1_new.mu - player1.mu
    player2_change = player2_new.mu - player2.mu

    #print(player1_change, player2_change)

    player1_new.mu = player1_change * weight + player1.mu
    player2_new.mu = player2_change * weight + player2.mu

    #print(player1_new.mu, player2_new.mu)

    return player1_new, player2_new

# rate the game with weights
async def rate_game(team1_rating: List[Tuple[openskill.Rating, openskill.Rating]], team2_rating: List[Tuple[openskill.Rating, openskill.Rating]], rank=None):
    if rank is None:
        rank = [0, 1]

    # players_rating: (rating, best_player_rating)
    
    team1 = list(map(lambda x: x[0], team1_rating))
    team2 = list(map(lambda x: x[0], team2_rating))

    team1_new, team2_new = openskill.rate([team1, team2], rank=rank)

    # get the change in mu for each player then apply weights

    team1_change = list(map(lambda x: x[0].mu - x[1].mu, zip(team1_new, team1)))
    team2_change = list(map(lambda x: x[0].mu - x[1].mu, zip(team2_new, team2)))

    # apply weights

    team1_final = []
    team2_final = []

    if rank == [0, 1]:
        for i in range(len(team1_change)):
            print(team1_rating[i])
            team1_change[i] *= team1_rating[i][0].mu/team1_rating[i][1].mu
            team1_final.append(openskill.Rating(team1_rating[i][0].mu + team1_change[i], team1_rating[i][0].sigma))
        for i in range(len(team2_change)):
            team2_change[i] *= team2_rating[i][1].mu/team2_rating[i][0].mu
            team2_final.append(openskill.Rating(team2_rating[i][0].mu + team2_change[i], team2_rating[i][0].sigma))
    else:
        for i in range(len(team1_change)):
            team1_change[i] *= team1_rating[i][1].mu/team1_rating[i][0].mu
            team1_final.append(openskill.Rating(team1_rating[i][0].mu + team1_change[i], team1_rating[i][0].sigma))
        for i in range(len(team2_change)):
            team2_change[i] *= team2_rating[i][0].mu/team2_rating[i][1].mu
            team2_final.append(openskill.Rating(team2_rating[i][0].mu + team2_change[i], team2_rating[i][0].sigma))
            

    return team1_final, team2_final
    


async def main():
    await Tortoise.init(
        db_url=f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/laserforce",
        modules={"models": ["db.models"]}
    )

    # reset mu and sigma for all players
    await Player.all().update(sm5_mu=25, sm5_sigma=25/3)

    t1 = time.time()

    for game in await SM5Game.all():
        if not game.ranked:
            continue

        # calculate player encounter performance

        # get all players

        players = await game.entity_starts.filter(type="player")

        events: List[Events] = await game.events.all()

        players_elo = {x.entity_id: openskill.Rating() for x in players}

        doubles = {}
        total_double_boost = {}

        for event in events:
            print(event.type)
            match event.type:
                case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                    shooter = await player_from_token(game, event.arguments[0])
                    shooter_elo = players_elo[shooter.entity_id]
                    target = await player_from_token(game, event.arguments[2])
                    target_elo = players_elo[target.entity_id]

                    shooter_elo, target_elo = await rate_encounter(shooter_elo, target_elo, 1, [0, 1])

                    players_elo[shooter.entity_id] = shooter_elo
                    players_elo[target.entity_id] = target_elo
                case EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_OPPONENT:
                    shooter = await player_from_token(game, event.arguments[0])
                    shooter_elo =  players_elo[shooter.entity_id]
                    target = await player_from_token(game, event.arguments[2])
                    target_elo = players_elo[target.entity_id]

                    shooter_elo, target_elo = await rate_encounter(shooter_elo, target_elo, 1.2, [0, 1])

                    players_elo[shooter.entity_id] = shooter_elo
                    players_elo[target.entity_id] = target_elo
                case EventType.RESUPPLY_AMMO | EventType.RESUPPLY_LIVES:
                    # check if player got doubles

                    resubber = await player_from_token(game, event.arguments[0])

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


        # display each player's elo

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

                other_player_rating = openskill.ordinal((players_elo[other_player.entity_id].mu, players_elo[other_player.entity_id].sigma))
                best_player_rating = openskill.ordinal((players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma))

                if other_player_rating > best_player_rating:
                    best_player = other_player

            player_rating = openskill.ordinal((players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma))
            best_player_rating = openskill.ordinal((players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma))

            if (await player.team).color_name == "Fire":
                players_t1.append(await Player.get(entity_id=player.entity_id))
                players_rating_t1.append((
                    openskill.Rating(players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma),
                    openskill.Rating(players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma)
                ))
            else:
                players_t2.append(await Player.get(entity_id=player.entity_id))
                players_rating_t2.append((
                    openskill.Rating(players_elo[player.entity_id].mu, players_elo[player.entity_id].sigma),
                    openskill.Rating(players_elo[best_player.entity_id].mu, players_elo[best_player.entity_id].sigma)
                ))

            print(
                player.name,
                player_rating,
                "weight if win: " + str(player_rating/best_player_rating + 0.25),
                "weight if lose: " + str(best_player_rating/player_rating - 0.25),
            )

        # update player elo

        ranks = [0, 1] if game.winner == Team.RED else [1, 0]

        team1, team2 = await rate_game(players_rating_t1, players_rating_t2, ranks)

        for team1_p, team1_rating in zip(players_t1, team1):
            team1_p.sm5_mu = team1_rating.mu
            team1_p.sm5_sigma = team1_rating.sigma
            await team1_p.save()

        for team2_p, team2_rating in zip(players_t2, team2):
            team1_p.sm5_mu = team2_rating.mu
            team1_p.sm5_sigma = team2_rating.sigma
            await team2_p.save()

    print("FINAL RATING\n\n\n")

    # print out all players' elo with mu that isn't 25 in order of elo
    for player in await Player.filter(sm5_mu__not=25).order_by("-sm5_mu"):
        print(player.codename, openskill.ordinal((player.sm5_mu, player.sm5_sigma)))

    print(time.time() - t1)

    exit()


if __name__ == "__main__":
    asyncio.run(main())
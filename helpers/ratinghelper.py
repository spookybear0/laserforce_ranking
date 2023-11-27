from objects import Team, LaserballGamePlayer
from random import shuffle
from openskill.models import PlackettLuceRating as Rating, PlackettLuce
import math
from scipy.stats import norm
from sanic.log import logger
from typing import List, Tuple
from db.models import SM5Game, Events, EntityStarts, EventType, Player, EntityEnds, LaserballGame
from objects import GameType
from helpers import userhelper


# CONSTANTS

MU = 25
SIGMA = MU / 3

model = PlackettLuce()

# sm5 elo helper functions

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
    
    # need to update previous rating and for each entity end object

    for entity_end in await game.entity_ends.filter(entity__type="player", entity__entity_id__startswith="#"):
        player = await Player.filter(ipl_id=(await entity_end.entity).entity_id).first()
        entity_end.previous_rating_mu = player.sm5_mu
        entity_end.previous_rating_sigma = player.sm5_sigma
        await entity_end.save()

    # go through all events for each game

    events: List[Events] = await game.events.filter(type__in=
        [EventType.DAMAGED_OPPONENT, EventType.DOWNED_OPPONENT, EventType.MISSILE_DAMAGE_OPPONENT,
        EventType.MISSILE_DOWN_OPPONENT, EventType.RESUPPLY_LIVES, EventType.RESUPPLY_AMMO]
    ).order_by("time").all() # only get the events that we need

    for event in events:
        if "@" in event.arguments[0] or "@" in event.arguments[2]:
            continue
        match event.type:
            case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_player = await Player.filter(ipl_id=shooter.entity_id).first()
                shooter_elo = Rating(shooter_player.sm5_mu, shooter_player.sm5_sigma)

                target = await userhelper.player_from_token(game, event.arguments[2])
                target_player = await Player.filter(ipl_id=target.entity_id).first()
                target_elo = Rating(target_player.sm5_mu, target_player.sm5_sigma)
                out = model.rate([[shooter_elo], [target_elo]], ranks=[0, 1])

                shooter_player.sm5_mu = out[0][0].mu
                shooter_player.sm5_sigma += (out[0][0].sigma - shooter_player.sm5_sigma) * 0.1

                target_player.sm5_mu = out[1][0].mu
                target_player.sm5_sigma += (out[1][0].sigma - target_player.sm5_sigma) * 0.1

                await shooter_player.save()
                await target_player.save()

            case EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_player = await Player.filter(ipl_id=shooter.entity_id).first()
                shooter_elo = Rating(shooter_player.sm5_mu, shooter_player.sm5_sigma)
                target = await userhelper.player_from_token(game, event.arguments[2])
                target_player = await Player.filter(ipl_id=target.entity_id).first()
                target_elo = Rating(target_player.sm5_mu, target_player.sm5_sigma)

                out = model.rate([[shooter_elo], [target_elo]], ranks=[0, 1])

                shooter_player.sm5_mu = out[0][0].mu
                shooter_player.sm5_sigma += (out[0][0].sigma - shooter_player.sm5_sigma) * 0.1

                target_player.sm5_mu = out[1][0].mu
                target_player.sm5_sigma += (out[1][0].sigma - target_player.sm5_sigma) * 0.1

                await shooter_player.save()
                await target_player.save()
    
    # rate game

    team1 = []
    team2 = []

    for player in await game.entity_starts.filter(type="player"):
        if (await player.team).color_name == "Fire":
            team1.append(await Player.filter(ipl_id=player.entity_id).first())
        else:
            team2.append(await Player.filter(ipl_id=player.entity_id).first())

    team1_elo = list(map(lambda x: Rating(x.sm5_mu, x.sm5_sigma), team1))
    team2_elo = list(map(lambda x: Rating(x.sm5_mu, x.sm5_sigma), team2))

    if game.winner == Team.RED:
        team1_new, team2_new = model.rate([team1_elo, team2_elo], ranks=[0, 1])
    else:
        team1_new, team2_new = model.rate([team1_elo, team2_elo], ranks=[1, 0])

    for player, rating in zip(team1, team1_new):
        player.sm5_mu = rating.mu
        player.sm5_sigma = rating.sigma
        await player.save()
    
    for player, rating in zip(team2, team2_new):
        player.sm5_mu = rating.mu
        player.sm5_sigma = rating.sigma
        await player.save()

    # need to update current rating and for each entity end object

    for entity_end in await game.entity_ends.filter(entity__type="player"):
        player = await Player.filter(ipl_id=(await entity_end.entity).entity_id).first()
        entity_end.current_rating_mu = player.sm5_mu
        entity_end.current_rating_sigma = player.sm5_sigma
        await entity_end.save()

    return True


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
    
    # need to update current rating and for each entity end object

    for entity_end in await game.entity_ends.filter(entity__type="player"):
        player = await Player.filter(ipl_id=(await entity_end.entity).entity_id).first()
        entity_end.previous_rating_mu = player.laserball_mu
        entity_end.previous_rating_sigma = player.laserball_sigma
        await entity_end.save()
    
    # TODO: benefits for scoring
    
    # go through all events for each game

    events: List[Events] = await game.events.filter(type__in=
        [EventType.STEAL, EventType.BLOCK]
    ).order_by("time").all() # only get the events that we need

    for event in events:
        if "@" in event.arguments[0] or "@" in event.arguments[2]:
            continue
        match event.type:
            # laserball events
            case EventType.BLOCK:
                blocker = await userhelper.player_from_token(game, event.arguments[0])
                blocker_player = await Player.filter(ipl_id=blocker.entity_id).first()
                blocker_elo = Rating(blocker_player.laserball_mu, blocker_player.laserball_sigma)

                blocked = await userhelper.player_from_token(game, event.arguments[2])
                blocked_player = await Player.filter(ipl_id=blocked.entity_id).first()
                blocked_elo = Rating(blocked_player.laserball_mu, blocked_player.laserball_sigma)

                out = model.rate([[blocker_elo], [blocked_elo]], ranks=[0, 1])

                blocker_player.laserball_mu = out[0][0].mu
                blocker_player.laserball_sigma = out[0][0].sigma

                blocked_player.laserball_mu = out[1][0].mu
                blocked_player.laserball_sigma = out[1][0].sigma

                await blocker_player.save()
                await blocked_player.save()
            case EventType.STEAL:
                stealer = await userhelper.player_from_token(game, event.arguments[0])
                stealer_player = await Player.filter(ipl_id=stealer.entity_id).first()
                stealer_elo = Rating(stealer_player.laserball_mu, stealer_player.laserball_sigma)

                stolen = await userhelper.player_from_token(game, event.arguments[2])
                stolen_player = await Player.filter(ipl_id=stolen.entity_id).first()
                stolen_elo = Rating(stolen_player.laserball_mu, stolen_player.laserball_sigma)

                out = model.rate([[stealer_elo], [stolen_elo]], ranks=[0, 1])

                # steal has a bigger impact so we need to multiply the difference by 1.5

                stealer_player.laserball_mu += (out[0][0].mu - stealer_player.laserball_mu) * 1.5
                stealer_player.laserball_sigma += (out[0][0].sigma - stealer_player.laserball_sigma) * 1.5

                stolen_player.laserball_mu += (out[1][0].mu - stolen_player.laserball_mu) * 1.5
                stolen_player.laserball_sigma += (out[1][0].sigma - stolen_player.laserball_sigma) * 1.5


                await stealer_player.save()
                await stolen_player.save()
    
    # rate game

    team1 = []
    team2 = []

    for player in await game.entity_starts.filter(type="player"):
        if (await player.team).color_name == "Fire":
            team1.append(await Player.filter(ipl_id=player.entity_id).first())
        else:
            team2.append(await Player.filter(ipl_id=player.entity_id).first())


    team1_elo = list(map(lambda x: Rating(x.laserball_mu, x.laserball_sigma), team1))
    team2_elo = list(map(lambda x: Rating(x.laserball_mu, x.laserball_sigma), team2))

    if game.winner == Team.RED:
        team1_new, team2_new = model.rate([team1_elo, team2_elo], ranks=[0, 1])
    else:
        team1_new, team2_new = model.rate([team1_elo, team2_elo], ranks=[1, 0])

    for player, rating in zip(team1, team1_new):
        player.laserball_mu = rating.mu
        player.laserball_sigma = rating.sigma
        await player.save()
    
    for player, rating in zip(team2, team2_new):
        player.laserball_mu = rating.mu
        player.laserball_sigma = rating.sigma
        await player.save()

    # need to update current rating and for each entity end object

    for entity_end in await game.entity_ends.filter(entity__type="player"):
        player = await Player.filter(ipl_id=(await entity_end.entity).entity_id).first()
        entity_end.current_rating_mu = player.laserball_mu
        entity_end.current_rating_sigma = player.laserball_sigma
        await entity_end.save()

    return True

def matchmake(players, mode: GameType=GameType.SM5):
    # use win chance to matchmake   

    mode = mode.value

    # get rating object for mode

    # bruteforce sort

    team1 = players[:len(players)//2]
    team2 = players[len(players)//2:]

    best1 = team1.copy()
    best2 = team2.copy()

    # gets most fair teams

    for _ in range(1000):
        shuffle(players)
        team1 = players[:len(players)//2]
        team2 = players[len(players)//2:]

        func = lambda x: getattr(x, f"{mode}_rating")

        # checks if teams are more fair then previous best
        # use win chance to matchmake
        # see which is closer to 0.5

        if abs(model.predict_win([list(map(func, team1)), list(map(func, team2))])[0] - 0.5)\
            < abs(model.predict_win([list(map(func, best1)), list(map(func, best2))])[0] - 0.5):
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
    return model.predict_win([team1, team2])

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
    return model.predict_draw([team1, team2])

async def recalculate_ratings():
    """
    Recalculates all ratings
    """

    # reset all ratings

    await Player.all().update(sm5_mu=MU, sm5_sigma=SIGMA, laserball_mu=MU, laserball_sigma=SIGMA)

    # get all games and recalculate ratings

    sm5_games = await SM5Game.all().order_by("start_time").all()


    for game in sm5_games:
        if game.ranked:
            logger.info(f"Updating player ranking for game {game.id}")

            if await update_sm5_ratings(game):
                logger.info(f"Updated player rankings for game {game.id}")
            else:
                logger.error(f"Failed to update player rankings for game {game.id}")
        else: # still need to add current_rating and previous_rating
            for entity_end in await game.entity_ends.filter(entity__type="player", entity__entity_id__startswith="#"):
                entity_id = (await entity_end.entity).entity_id

                player = await Player.filter(ipl_id=entity_id).first()
                
                entity_end.previous_rating_mu = player.laserball_mu
                entity_end.previous_rating_sigma = player.laserball_sigma
                entity_end.current_rating_mu = player.laserball_mu
                entity_end.current_rating_sigma = player.laserball_sigma

                await entity_end.save()

    lb_games = await LaserballGame.all().order_by("start_time").all()

    for game in lb_games:
        if game.ranked:
            logger.info(f"Updating player ranking for game {game.id}")

            if await update_laserball_ratings(game):
                logger.info(f"Updated player rankings for game {game.id}")
            else:
                logger.error(f"Failed to update player rankings for game {game.id}")
        else:
            for entity_end in await game.entity_ends.filter(entity__type="player"):
                entity_id = (await entity_end.entity).entity_id

                player = await Player.filter(ipl_id=entity_id).first()
                
                entity_end.previous_rating_mu = player.laserball_mu
                entity_end.previous_rating_sigma = player.laserball_sigma
                entity_end.current_rating_mu = player.laserball_mu
                entity_end.current_rating_sigma = player.laserball_sigma

                await entity_end.save()
    
    logger.info("Finished recalculating ratings")
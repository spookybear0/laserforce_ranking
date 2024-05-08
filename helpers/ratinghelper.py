import itertools
import math
from random import shuffle
from typing import List, Tuple, Union

from openskill.models import PlackettLuceRating, PlackettLuce
from openskill.models.weng_lin.common import phi_major
from sanic.log import logger

from db.game import Events
from db.laserball import LaserballGame
from db.player import Player
from db.sm5 import SM5Game
from db.types import EventType, GameType, Team
from helpers import userhelper

# CONSTANTS

MU = 25
SIGMA = 25 / 3
BETA = 25 / 6
KAPPA = 0.0001
TAU = 25 / 200  # default: 25/300 (for rating volatility)
ZETA = 0.09  # default: 0 (custom addition for uneven team rating adjustment), higher value = more adjustment for uneven teams


class CustomPlackettLuce(PlackettLuce):
    def predict_win(self, teams: List[List[PlackettLuceRating]]) -> List[Union[int, float]]:
        # Check Arguments
        self._check_teams(teams)

        n = len(teams)

        # uneven team adjustment is only implemented for 2 teams

        # 2 Player Case
        if n == 2:
            # CUSTOM ADDITION
            if len(teams[0]) > len(teams[1]):
                logger.debug("Adjusting team ratings for uneven team count (team 1 has more players)")
                # team 1 has more players than team 2
                for player in teams[1]:
                    # multiply by 1 + 0.1 * the difference in player count
                    player.mu *= 1 + ZETA * abs(len(teams[0]) - len(teams[1]))
            elif len(teams[0]) < len(teams[1]):
                logger.debug("Adjusting team ratings for uneven team count (team 2 has more players)")
                # team 2 has more players than team 1
                for player in teams[0]:
                    # multiply by 1 + 0.1 * the difference in player count
                    player.mu *= 1 + ZETA * abs(len(teams[0]) - len(teams[1]))

            total_player_count = len(teams[0]) + len(teams[1])
            teams_ratings = self._calculate_team_ratings(teams)
            a = teams_ratings[0]
            b = teams_ratings[1]

            result = phi_major(
                (a.mu - b.mu)
                / math.sqrt(
                    total_player_count * self.beta ** 2
                    + a.sigma_squared
                    + b.sigma_squared
                )
            )

            return [result, 1 - result]

        return PlackettLuce.predict_win(self, teams)


model = CustomPlackettLuce(MU, SIGMA, BETA, KAPPA, tau=TAU)
Rating = PlackettLuceRating


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
        player = await Player.filter(entity_id=(await entity_end.entity).entity_id).first()
        entity_end.previous_rating_mu = player.sm5_mu
        entity_end.previous_rating_sigma = player.sm5_sigma
        await entity_end.save()

    # go through all events for each game

    events: List[Events] = await game.events.filter(type__in=
                                                    [EventType.DAMAGED_OPPONENT, EventType.DOWNED_OPPONENT,
                                                     EventType.MISSILE_DAMAGE_OPPONENT,
                                                     EventType.MISSILE_DOWN_OPPONENT, EventType.RESUPPLY_LIVES,
                                                     EventType.RESUPPLY_AMMO]
                                                    ).order_by("time").all()  # only get the events that we need

    for event in events:
        if "@" in event.arguments[0] or "@" in event.arguments[2]:
            continue
        match event.type:
            case EventType.DAMAGED_OPPONENT | EventType.DOWNED_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_player = await Player.filter(entity_id=shooter.entity_id).first()
                shooter_elo = Rating(shooter_player.sm5_mu, shooter_player.sm5_sigma)

                target = await userhelper.player_from_token(game, event.arguments[2])
                target_player = await Player.filter(entity_id=target.entity_id).first()
                target_elo = Rating(target_player.sm5_mu, target_player.sm5_sigma)
                out = model.rate([[shooter_elo], [target_elo]], ranks=[0, 1])

                shooter_player.sm5_mu += (out[0][0].mu - shooter_player.sm5_mu) * 0.1
                shooter_player.sm5_sigma += (out[0][0].sigma - shooter_player.sm5_sigma) * 0.1

                target_player.sm5_mu += (out[1][0].mu - target_player.sm5_mu) * 0.1
                target_player.sm5_sigma += (out[1][0].sigma - target_player.sm5_sigma) * 0.1

                await shooter_player.save()
                await target_player.save()

            case EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_player = await Player.filter(entity_id=shooter.entity_id).first()
                shooter_elo = Rating(shooter_player.sm5_mu, shooter_player.sm5_sigma)
                target = await userhelper.player_from_token(game, event.arguments[2])
                target_player = await Player.filter(entity_id=target.entity_id).first()
                target_elo = Rating(target_player.sm5_mu, target_player.sm5_sigma)

                out = model.rate([[shooter_elo], [target_elo]], ranks=[0, 1])

                shooter_player.sm5_mu += (out[0][0].mu - shooter_player.sm5_mu) * 0.15
                shooter_player.sm5_sigma += (out[0][0].sigma - shooter_player.sm5_sigma) * 0.1

                target_player.sm5_mu += (out[1][0].mu - target_player.sm5_mu) * 0.15
                target_player.sm5_sigma += (out[1][0].sigma - target_player.sm5_sigma) * 0.1

                await shooter_player.save()
                await target_player.save()

    # rate game

    team1 = []
    team2 = []

    for player in await game.entity_starts.filter(type="player"):
        if (await player.team).color_name == "Fire":
            team1.append(await Player.filter(entity_id=player.entity_id).first())
        else:
            team2.append(await Player.filter(entity_id=player.entity_id).first())

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
        player = await Player.filter(entity_id=(await entity_end.entity).entity_id).first()
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
        player = await Player.filter(entity_id=(await entity_end.entity).entity_id).first()
        entity_end.previous_rating_mu = player.laserball_mu
        entity_end.previous_rating_sigma = player.laserball_sigma
        await entity_end.save()

    # go through all events for each game

    events: List[Events] = await game.events.filter(type__in=
                                                    [EventType.STEAL, EventType.GOAL, EventType.ASSIST, EventType.CLEAR]
                                                    ).order_by("time").all()  # only get the events that we need

    for event in events:
        if "@" in event.arguments[0] or (len(event.arguments) > 3) and "@" in event.arguments[2]:
            continue
        match event.type:
            # laserball events (steals, goals, assists, clears)
            # NOTE: assist event was not implemented until 2/26/24 (the tdf does not include a ASSIST event, so i have to make it myself)
            case EventType.STEAL:
                stealer = await userhelper.player_from_token(game, event.arguments[0])
                stealer_player = await Player.filter(entity_id=stealer.entity_id).first()
                stealer_elo = Rating(stealer_player.laserball_mu, stealer_player.laserball_sigma)

                stolen = await userhelper.player_from_token(game, event.arguments[2])
                stolen_player = await Player.filter(entity_id=stolen.entity_id).first()
                stolen_elo = Rating(stolen_player.laserball_mu, stolen_player.laserball_sigma)

                out = model.rate([[stealer_elo], [stolen_elo]], ranks=[0, 1])

                stealer_player.laserball_mu += (out[0][0].mu - stealer_player.laserball_mu) * 0.2
                stealer_player.laserball_sigma += (out[0][0].sigma - stealer_player.laserball_sigma) * 0.2

                stolen_player.laserball_mu += (out[1][0].mu - stolen_player.laserball_mu) * 0.2
                stolen_player.laserball_sigma += (out[1][0].sigma - stolen_player.laserball_sigma) * 0.2

                await stealer_player.save()
                await stolen_player.save()
            case EventType.GOAL:
                scorer = await userhelper.player_from_token(game, event.arguments[0])
                scorer_player = await Player.filter(entity_id=scorer.entity_id).first()
                scorer_elo = Rating(scorer_player.laserball_mu, scorer_player.laserball_sigma)

                out = model.rate([[scorer_elo], [scorer_elo]], ranks=[0, 1])

                scorer_player.laserball_mu += (out[0][0].mu - scorer_player.laserball_mu) * 1.5
                scorer_player.laserball_sigma += (out[0][0].sigma - scorer_player.laserball_sigma) * 1.5

                await scorer_player.save()
            case EventType.ASSIST:
                assister = await userhelper.player_from_token(game, event.arguments[0])
                assister_player = await Player.filter(entity_id=assister.entity_id).first()
                assister_elo = Rating(assister_player.laserball_mu, assister_player.laserball_sigma)

                scorer = await userhelper.player_from_token(game, event.arguments[2])
                scorer_player = await Player.filter(entity_id=scorer.entity_id).first()
                scorer_elo = Rating(scorer_player.laserball_mu, scorer_player.laserball_sigma)

                out = model.rate([[assister_elo], [scorer_elo]], ranks=[0, 1])

                assister_player.laserball_mu += (out[0][0].mu - assister_player.laserball_mu) * 0.75
                assister_player.laserball_sigma += (out[0][0].sigma - assister_player.laserball_sigma) * 0.75
            case EventType.CLEAR:
                clearer = await userhelper.player_from_token(game, event.arguments[0])
                clearer_player = await Player.filter(entity_id=clearer.entity_id).first()
                clearer_elo = Rating(clearer_player.laserball_mu, clearer_player.laserball_sigma)

                out = model.rate([[clearer_elo], [clearer_elo]], ranks=[0, 1])

                clearer_player.laserball_mu += (out[0][0].mu - clearer_player.laserball_mu) * 0.75
                clearer_player.laserball_sigma += (out[0][0].sigma - clearer_player.laserball_sigma) * 0.75

                await clearer_player.save()

    # rate game

    team1 = []
    team2 = []

    for player in await game.entity_starts.filter(type="player"):
        if (await player.team).color_name == "Fire":
            team1.append(await Player.filter(entity_id=player.entity_id).first())
        else:
            team2.append(await Player.filter(entity_id=player.entity_id).first())

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
        player = await Player.filter(entity_id=(await entity_end.entity).entity_id).first()
        entity_end.current_rating_mu = player.laserball_mu
        entity_end.current_rating_sigma = player.laserball_sigma
        await entity_end.save()

    return True


# deprecated
def matchmake(players, mode: GameType = GameType.SM5) -> Tuple[List[Player], List[Player]]:
    return matchmake_teams(players, 2, mode)


def matchmake_teams(players, num_teams: int, mode: GameType = GameType.SM5) -> List[List[Player]]:
    """
    Matchmakes 2-4 teams
    """

    mode = mode.value

    # get rating object for mode

    # bruteforce sort

    best_teams = [players[i::num_teams] for i in range(num_teams)]

    # gets most fair teams

    for _ in range(1000):
        shuffle(players)
        teams = [players[i::num_teams] for i in range(num_teams)]

        func = lambda x: getattr(x, f"{mode}_rating")

        # checks if teams are more fair then previous best
        # use win chance to matchmake
        # see which is closer to 0.5, 0.33, 0.25

        ideal_win_chance = 1 / num_teams

        for team in itertools.combinations(teams, 2):
            if abs(model.predict_win([list(map(func, team[0])), list(map(func, team[1]))])[0] - ideal_win_chance) \
                    < abs(model.predict_win([list(map(func, best_teams[0])), list(map(func, best_teams[1]))])[
                              0] - ideal_win_chance):
                best_teams = teams
    return best_teams


def get_win_chance(team1, team2, mode: GameType = GameType.SM5) -> float:
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


def get_win_chances(team1, team2, team3=None, team4=None, mode: GameType = GameType.SM5) -> List[float]:
    """
    Gets win chances for 2-4 teams
    """

    logger.debug(f"Getting win chances for {team1} vs {team2} vs {team3} vs {team4}")

    mode = mode.value
    # get rating object for mode
    team1 = list(map(lambda x: getattr(x, f"{mode}_rating"), team1))
    team2 = list(map(lambda x: getattr(x, f"{mode}_rating"), team2))
    team3 = list(map(lambda x: getattr(x, f"{mode}_rating"), team3))
    team4 = list(map(lambda x: getattr(x, f"{mode}_rating"), team4))

    logger.debug("Predicting win chances")

    if not team3:
        return model.predict_win([team1, team2])
    elif not team4:
        return model.predict_win([team1, team2, team3])
    return model.predict_win([team1, team2, team3, team4])


def get_draw_chance(team1, team2, mode: GameType = GameType.SM5) -> float:
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


async def recalculate_sm5_ratings() -> None:
    """
    Recalculates sm5 ratings
    """

    # reset sm5 ratings

    await Player.all().update(sm5_mu=MU, sm5_sigma=SIGMA)

    # get all games and recalculate ratings

    sm5_games = await SM5Game.all().order_by("start_time").all()

    for game in sm5_games:
        if game.ranked:
            logger.info(f"Updating player ranking for game {game.id}")

            if await update_sm5_ratings(game):
                logger.info(f"Updated player rankings for game {game.id}")
            else:
                logger.error(f"Failed to update player rankings for game {game.id}")
        else:  # still need to add current_rating and previous_rating
            for entity_end in await game.entity_ends.filter(entity__type="player", entity__entity_id__startswith="#"):
                entity_id = (await entity_end.entity).entity_id

                player = await Player.filter(entity_id=entity_id).first()

                entity_end.previous_rating_mu = player.laserball_mu
                entity_end.previous_rating_sigma = player.laserball_sigma
                entity_end.current_rating_mu = player.laserball_mu
                entity_end.current_rating_sigma = player.laserball_sigma

                await entity_end.save()


async def recalculate_laserball_ratings() -> None:
    """
    Recalculates laserball ratings
    """

    # reset laserball ratings

    await Player.all().update(laserball_mu=MU, laserball_sigma=SIGMA)

    lb_games = await LaserballGame.all().order_by("start_time").all()

    for game in lb_games:
        if game.ranked:
            logger.info(f"Updating player ranking for game {game.id}")

            if await update_laserball_ratings(game):
                logger.info(f"Updated player rankings for game {game.id}")
            else:
                logger.error(f"Failed to update player rankings for game {game.id}")
        else:
            for entity_end in await game.entity_ends.filter(entity__type="player", entity__entity_id__startswith="#"):
                entity_id = (await entity_end.entity).entity_id

                player = await Player.filter(entity_id=entity_id).first()

                entity_end.previous_rating_mu = player.laserball_mu
                entity_end.previous_rating_sigma = player.laserball_sigma
                entity_end.current_rating_mu = player.laserball_mu
                entity_end.current_rating_sigma = player.laserball_sigma

                await entity_end.save()


async def recalculate_ratings() -> None:
    """
    Recalculates all ratings
    """

    logger.info("Recalculating sm5 ratings")
    await recalculate_sm5_ratings()
    logger.info("Recalculating laserball ratings")
    await recalculate_laserball_ratings()

    logger.info("Finished recalculating ratings")

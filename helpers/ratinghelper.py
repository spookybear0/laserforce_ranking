import itertools
import math
import random
from typing import List, Tuple, Union

from openskill.models import PlackettLuceRating, PlackettLuce
from openskill.models.weng_lin.common import phi_major
from sanic.log import logger

from db.game import Events
from db.laserball import LaserballGame
from db.player import Player
from db.sm5 import SM5Game
from db.types import EventType, GameType, Team, IntRole
from helpers import userhelper

# CONSTANTS

MU = 25
SIGMA = 25 / 3
BETA = 25 / 6
KAPPA = 0.0001
TAU = 25 / 275  # default: 25/300 (for rating volatility, higher = more volatile ratings)
ZETA = 0.09  # default: 0 (custom addition for uneven team rating adjustment), higher value = more adjustment for uneven teams

# mu is for skill, sigma is for uncertainty/confidence
# the higher the mu, the better the player is expected to perform
# the higher the sigma, the less confident we are in the player's skill

# sm5

# TODO: possibly seperate damaged and downed events, but for now they are treated the same

# overall weight for an entire game (mu_weight, sigma_weight) = (1, 1) ( rate([team1, team2]) )
# this is for the overall game outcome (win/loss) which rates all players at once
# the multipliers for mu and sigma are both 1


SM5_HIT_WEIGHT_MU = 0.01  # skill weight for hits in sm5
SM5_HIT_WEIGHT_SIGMA = 0.01  # uncertainty weight for hits in sm5

SM5_HIT_MEDIC_WEIGHT_MU = 0.02  # skill weight for medic hits in sm5
SM5_HIT_MEDIC_WEIGHT_SIGMA = 0.01  # uncertainty weight for medic hits in sm5


SM5_MISSILE_WEIGHT_MU = 0.025  # skill weight for missile hits in sm5
SM5_MISSILE_WEIGHT_SIGMA = 0.01  # uncertainty weight for missile hits in sm5

SM5_MISSILE_MEDIC_WEIGHT_MU = 0.05  # skill weight for medic missiles in sm5
SM5_MISSILE_MEDIC_WEIGHT_SIGMA = 0.01  # uncertainty weight for medic missiles in sm5

# sm5 role specific multipliers (multiply the above weights by these for role specific ratings)

SM5_COMMANDER_WEIGHT_MU = 1
SM5_COMMANDER_WEIGHT_SIGMA = 1

SM5_HEAVY_WEIGHT_MU = 1
SM5_HEAVY_WEIGHT_SIGMA = 1

SM5_SCOUT_WEIGHT_MU = 1
SM5_SCOUT_WEIGHT_SIGMA = 1

SM5_AMMO_WEIGHT_MU = 1
SM5_AMMO_WEIGHT_SIGMA = 1.25 # give more uncertainty weight to ammo players since their role is less combat focused

SM5_MEDIC_WEIGHT_MU = 1
SM5_MEDIC_WEIGHT_SIGMA = 2 # give more uncertainty weight to medic players since their role is less combat focused

SM5_ROLE_WEIGHT_MULTIPLIERS = {
    IntRole.COMMANDER: (SM5_COMMANDER_WEIGHT_MU, SM5_COMMANDER_WEIGHT_SIGMA),
    IntRole.HEAVY: (SM5_HEAVY_WEIGHT_MU, SM5_HEAVY_WEIGHT_SIGMA),
    IntRole.SCOUT: (SM5_SCOUT_WEIGHT_MU, SM5_SCOUT_WEIGHT_SIGMA),
    IntRole.AMMO: (SM5_AMMO_WEIGHT_MU, SM5_AMMO_WEIGHT_SIGMA),
    IntRole.MEDIC: (SM5_MEDIC_WEIGHT_MU, SM5_MEDIC_WEIGHT_SIGMA),
}

# laserball

# TODO: check if weight_sigma should be the same for all events like in sm5
# TODO: possibily only use overall game ratings for laserball to make ratings
# fully depend on the game outcome, not individual events

LB_STEAL_WEIGHT_MU = 0.2  # skill weight for steals in laserball
LB_STEAL_WEIGHT_SIGMA = 0.2  # uncertainty weight for steals in laserball

LB_GOAL_WEIGHT_MU = 1.5  # skill weight for goals in laserball
LB_GOAL_WEIGHT_SIGMA = 1.5  # uncertainty weight for goals in laserball

LB_ASSIST_WEIGHT_MU = 0.75  # skill weight for assists in laserball
LB_ASSIST_WEIGHT_SIGMA = 0.75  # uncertainty weight for assists in laserball


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
            elif len(teams[0]) < len(teams[1]): # TODO: do testing to see if this actually predicts uneven matches well
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

        # TODO: Implement uneven team adjustment for 3 and 4 teams
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
                shooter_elo = shooter_player.sm5_rating
                shooter_elo_role = shooter_player.get_role_rating(shooter.role)

                target = await userhelper.player_from_token(game, event.arguments[2])
                target_player = await Player.filter(entity_id=target.entity_id).first()
                target_elo = target_player.sm5_rating
                target_elo_role = target_player.get_role_rating(target.role)

                general_out = model.rate([[shooter_elo], [target_elo]], ranks=[0, 1])
                role_out = model.rate([[shooter_elo_role], [target_elo_role]], ranks=[0, 1])

                weight_mu = SM5_HIT_WEIGHT_MU # default for damage and downed events
                weight_sigma = SM5_HIT_WEIGHT_SIGMA # default for damage and downed events
                if target.role == IntRole.MEDIC:
                    weight_mu = SM5_HIT_MEDIC_WEIGHT_MU # give more weight to medic hits
                    weight_sigma = SM5_HIT_MEDIC_WEIGHT_SIGMA

                # update general ratings with weights
                shooter_player.sm5_mu += (general_out[0][0].mu - shooter_player.sm5_mu) * weight_mu
                shooter_player.sm5_sigma += (general_out[0][0].sigma - shooter_player.sm5_sigma) * weight_sigma

                # update role ratings with weights

                shooter_role_weight_mu, shooter_role_weight_sigma = SM5_ROLE_WEIGHT_MULTIPLIERS[shooter.role]

                setattr(shooter_player, f"{str(shooter.role).lower()}_mu", getattr(shooter_player, f"{str(shooter.role).lower()}_mu") + (role_out[0][0].mu - getattr(shooter_player, f"{str(shooter.role).lower()}_mu")) * weight_mu * shooter_role_weight_mu)
                setattr(shooter_player, f"{str(shooter.role).lower()}_sigma", getattr(shooter_player, f"{str(shooter.role).lower()}_sigma") + (role_out[0][0].sigma - getattr(shooter_player, f"{str(shooter.role).lower()}_sigma")) * weight_sigma * shooter_role_weight_sigma)

                if target.role == IntRole.MEDIC:
                    # don't penalize medics extra just for being medic
                    # (give people hitting medics more ranking, but don't give medics less ranking because it's a medic hit)
                    weight_mu = SM5_HIT_WEIGHT_MU
                    weight_sigma = SM5_HIT_WEIGHT_SIGMA

                # update general ratings with weights
                target_player.sm5_mu += (general_out[1][0].mu - target_player.sm5_mu) * weight_mu
                target_player.sm5_sigma += (general_out[1][0].sigma - target_player.sm5_sigma) * weight_sigma

                # update role ratings with weights

                target_role_weight_mu, target_role_weight_sigma = SM5_ROLE_WEIGHT_MULTIPLIERS[target.role]

                setattr(target_player, f"{str(target.role).lower()}_mu", getattr(target_player, f"{str(target.role).lower()}_mu") + (role_out[1][0].mu - getattr(target_player, f"{str(target.role).lower()}_mu")) * weight_mu * target_role_weight_mu)
                setattr(target_player, f"{str(target.role).lower()}_sigma", getattr(target_player, f"{str(target.role).lower()}_sigma") + (role_out[1][0].sigma - getattr(target_player, f"{str(target.role).lower()}_sigma")) * weight_sigma * target_role_weight_sigma)

                await shooter_player.save()
                await target_player.save()

            case EventType.MISSILE_DAMAGE_OPPONENT | EventType.MISSILE_DOWN_OPPONENT:
                shooter = await userhelper.player_from_token(game, event.arguments[0])
                shooter_player = await Player.filter(entity_id=shooter.entity_id).first()
                shooter_elo = shooter_player.sm5_rating
                shooter_elo_role = shooter_player.get_role_rating(shooter.role)

                target = await userhelper.player_from_token(game, event.arguments[2])
                target_player = await Player.filter(entity_id=target.entity_id).first()
                target_elo = target_player.sm5_rating
                target_elo_role = target_player.get_role_rating(target.role)

                general_out = model.rate([[shooter_elo], [target_elo]], ranks=[0, 1])
                role_out = model.rate([[shooter_elo_role], [target_elo_role]], ranks=[0, 1])

                weight_mu = SM5_MISSILE_WEIGHT_MU # default for missiles
                weight_sigma = SM5_MISSILE_WEIGHT_SIGMA
                if target.role == IntRole.MEDIC:
                    weight_mu = SM5_MISSILE_MEDIC_WEIGHT_MU # give more weight to medic missiles
                    weight_sigma = SM5_MISSILE_MEDIC_WEIGHT_SIGMA

                # update general ratings with weights
                shooter_player.sm5_mu += (general_out[0][0].mu - shooter_player.sm5_mu) * weight_mu
                shooter_player.sm5_sigma += (general_out[0][0].sigma - shooter_player.sm5_sigma) * weight_sigma

                # update role ratings with weights

                shooter_role_weight_mu, shooter_role_weight_sigma = SM5_ROLE_WEIGHT_MULTIPLIERS[shooter.role]

                setattr(shooter_player, f"{str(shooter.role).lower()}_mu", getattr(shooter_player, f"{str(shooter.role).lower()}_mu") + (role_out[0][0].mu - getattr(shooter_player, f"{str(shooter.role).lower()}_mu")) * weight_mu * shooter_role_weight_mu)
                setattr(shooter_player, f"{str(shooter.role).lower()}_sigma", getattr(shooter_player, f"{str(shooter.role).lower()}_sigma") + (role_out[0][0].sigma - getattr(shooter_player, f"{str(shooter.role).lower()}_sigma")) * weight_sigma * shooter_role_weight_sigma)

                if target.role == IntRole.MEDIC:
                    # don't penalize medics extra just for being medic
                    weight_mu = SM5_MISSILE_WEIGHT_MU
                    weight_sigma = SM5_MISSILE_WEIGHT_SIGMA

                # update general ratings with weights
                target_player.sm5_mu += (general_out[1][0].mu - target_player.sm5_mu) * weight_mu
                target_player.sm5_sigma += (general_out[1][0].sigma - target_player.sm5_sigma) * weight_sigma

                # update role ratings with weights

                target_role_weight_mu, target_role_weight_sigma = SM5_ROLE_WEIGHT_MULTIPLIERS[target.role]

                setattr(target_player, f"{str(target.role).lower()}_mu", getattr(target_player, f"{str(target.role).lower()}_mu") + (role_out[1][0].mu - getattr(target_player, f"{str(target.role).lower()}_mu")) * weight_mu * target_role_weight_mu)
                setattr(target_player, f"{str(target.role).lower()}_sigma", getattr(target_player, f"{str(target.role).lower()}_sigma") + (role_out[1][0].sigma - getattr(target_player, f"{str(target.role).lower()}_sigma")) * weight_sigma * target_role_weight_sigma)

                await shooter_player.save()
                await target_player.save()

    # rate game

    team1 = []
    team2 = []

    teams = await game.get_teams()

    for player in await game.entity_starts.filter(type="player"):
        team_color = (await player.team).color_name
        if team_color == (teams[0].color_name):
            team1.append(await Player.filter(entity_id=player.entity_id).first())
        else:
            team2.append(await Player.filter(entity_id=player.entity_id).first())

    team1_elo = list(map(lambda x: Rating(x.sm5_mu, x.sm5_sigma), team1))
    team2_elo = list(map(lambda x: Rating(x.sm5_mu, x.sm5_sigma), team2))

    if game.winner == teams[0].enum:
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
                                                    [EventType.STEAL, EventType.GOAL, EventType.ASSIST]
                                                    ).order_by("time").all()  # only get the events that we need

    for event in events:
        if "@" in event.arguments[0] or (len(event.arguments) > 3) and "@" in event.arguments[2]:
            continue
        match event.type:
            # laserball events (steals, goals, assists)
            # NOTE: assist event was not implemented until 2/26/24 (the tdf does not include a ASSIST event, so i have to make it myself)
            case EventType.STEAL:
                stealer = await userhelper.player_from_token(game, event.arguments[0])
                stealer_player = await Player.filter(entity_id=stealer.entity_id).first()
                stealer_elo = Rating(stealer_player.laserball_mu, stealer_player.laserball_sigma)

                stolen = await userhelper.player_from_token(game, event.arguments[2])
                stolen_player = await Player.filter(entity_id=stolen.entity_id).first()
                stolen_elo = Rating(stolen_player.laserball_mu, stolen_player.laserball_sigma)

                out = model.rate([[stealer_elo], [stolen_elo]], ranks=[0, 1])

                stealer_player.laserball_mu += (out[0][0].mu - stealer_player.laserball_mu) * LB_STEAL_WEIGHT_MU
                stealer_player.laserball_sigma += (out[0][0].sigma - stealer_player.laserball_sigma) * LB_STEAL_WEIGHT_SIGMA

                stolen_player.laserball_mu += (out[1][0].mu - stolen_player.laserball_mu) * LB_STEAL_WEIGHT_MU
                stolen_player.laserball_sigma += (out[1][0].sigma - stolen_player.laserball_sigma) * LB_STEAL_WEIGHT_SIGMA

                await stealer_player.save()
                await stolen_player.save()
            case EventType.GOAL:
                scorer = await userhelper.player_from_token(game, event.arguments[0])
                scorer_player = await Player.filter(entity_id=scorer.entity_id).first()
                scorer_elo = Rating(scorer_player.laserball_mu, scorer_player.laserball_sigma)

                out = model.rate([[scorer_elo], [scorer_elo]], ranks=[0, 1])

                scorer_player.laserball_mu += (out[0][0].mu - scorer_player.laserball_mu) * LB_GOAL_WEIGHT_MU
                scorer_player.laserball_sigma += (out[0][0].sigma - scorer_player.laserball_sigma) * LB_GOAL_WEIGHT_SIGMA

                await scorer_player.save()
            case EventType.ASSIST:
                assister = await userhelper.player_from_token(game, event.arguments[0])
                assister_player = await Player.filter(entity_id=assister.entity_id).first()
                assister_elo = Rating(assister_player.laserball_mu, assister_player.laserball_sigma)

                scorer = await userhelper.player_from_token(game, event.arguments[2])
                scorer_player = await Player.filter(entity_id=scorer.entity_id).first()
                scorer_elo = Rating(scorer_player.laserball_mu, scorer_player.laserball_sigma)

                out = model.rate([[assister_elo], [scorer_elo]], ranks=[0, 1])

                assister_player.laserball_mu += (out[0][0].mu - assister_player.laserball_mu) * LB_ASSIST_WEIGHT_MU
                assister_player.laserball_sigma += (out[0][0].sigma - assister_player.laserball_sigma) * LB_ASSIST_WEIGHT_SIGMA

    # rate game

    team1 = []
    team2 = []

    teams = await game.get_teams()

    for player in await game.entity_starts.filter(type="player"):
        if (await player.team).color_name == (teams[0].color_name):
            team1.append(await Player.filter(entity_id=player.entity_id).first())
        else:
            team2.append(await Player.filter(entity_id=player.entity_id).first())

    team1_elo = list(map(lambda x: Rating(x.laserball_mu, x.laserball_sigma), team1))
    team2_elo = list(map(lambda x: Rating(x.laserball_mu, x.laserball_sigma), team2))

    if game.winner == teams[0].enum:
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


def matchmake_teams(players: List[Player], num_teams: int=2, mode: str = GameType.SM5) -> List[List[Player]]:
    mode = mode.value.lower()

    if not 2 <= num_teams <= 4:
        raise ValueError("num_teams must be between 2 and 4")

    def get_team_rating(team):
        return [getattr(player, f"{mode}_rating") for player in team]
    
    def evaluate_teams(teams):
        ideal_win_chance = 0.5
        win_chances = []
        for team1, team2 in itertools.combinations(teams, 2):
            team1_rating = get_team_rating(team1)
            team2_rating = get_team_rating(team2)
            win_chance = model.predict_win([team1_rating, team2_rating])[0]
            win_chances.append(abs(win_chance - ideal_win_chance))
        return sum(win_chances)

    best_teams = [players[i::num_teams] for i in range(num_teams)]
    best_fairness = evaluate_teams(best_teams)

    for _ in range(1000):
        random.shuffle(players)
        current_teams = [players[i::num_teams] for i in range(num_teams)]

        # make sure all teams have the same number of players

        # 2 teams
        if num_teams == 2 and len(current_teams[0]) != len(current_teams[1]) and len(players) % 2 == 0:
            continue

        # 3 teams
        if num_teams == 3 and len(current_teams[0]) != len(current_teams[1]) and len(current_teams[1]) != len(current_teams[2]) and len(players) % 3 == 0:
            continue

        # 4 teams
        if num_teams == 4 and any(len(team) != len(players) // num_teams for team in current_teams) and len(players) % 4 == 0:
            continue

        current_fairness = evaluate_teams(current_teams)
        if current_fairness < best_fairness:
            best_teams = current_teams
            best_fairness = current_fairness

    return best_teams

def get_best_roles_for_teams(teams: List[List[Player]]) -> List[List[IntRole]]:
    """
    Gets the best roles for a list of teams

    Algorithm:

    1. Assign unique roles (commander, heavy, ammo, medic) to the players with the highest rating for that role
    2. Assign the remaining players as scouts
    3. (if using the matchmaker) shuffle the players and repeat the process until the best combination is found


    Possible improvements:
    - Consider how well resupply combos work together
    - Consider giving players their preferred roles
    - Consider giving players roles that they haven't played often for variety
    """

    best_roles = []
    roles = [IntRole.COMMANDER, IntRole.HEAVY, IntRole.AMMO, IntRole.MEDIC, IntRole.SCOUT]

    for team in teams:
        team_roles = [None] * len(team)
        assigned_roles = {role: False for role in roles if role != IntRole.SCOUT}
        remaining_players = list(range(len(team)))
        random.shuffle(remaining_players)

        # first, assign unique roles (commander, heavy, ammo, medic)
        for role in assigned_roles:
            # check if there's enough players left to assign any more roles
            if not remaining_players:
                break

            best_rating = None
            best_player_idx = None
            for i in remaining_players:
                player = team[i]
                rating = player.get_role_rating(role)
                if not best_rating or rating > best_rating:
                    best_rating = rating
                    best_player_idx = i
            team_roles[best_player_idx] = role
            assigned_roles[role] = True
            if best_player_idx is not None:
                remaining_players.remove(best_player_idx)

        # assign remaining players as scouts
        for i in remaining_players:
            team_roles[i] = IntRole.SCOUT

        best_roles.append(team_roles)
    
    return best_roles

def matchmake_teams_with_roles(players: List[Player], num_teams: int, mode: str = GameType.SM5) -> List[List[Player]]:
    mode = mode.value.lower()

    if not 2 <= num_teams <= 4:
        raise ValueError("num_teams must be between 2 and 4")

    def get_team_rating(team, roles):
        return [player.get_role_rating(role) for player, role in zip(team, roles)]
    
    def evaluate_teams(teams, roles):
        ideal_win_chance = 0.5
        win_chances = []
        for team1, team2 in itertools.combinations(teams, 2):
            if len(team1) != len(team2):
                logger.warning("Teams have different player counts!") # this should never happen
                continue

            if len(team1) == 0 or len(team2) == 0: # every team must have at least one player
                continue

            team1_rating = get_team_rating(team1, roles[teams.index(team1)])
            team2_rating = get_team_rating(team2, roles[teams.index(team2)])
            win_chance = model.predict_win([team1_rating, team2_rating])[0]
            win_chances.append(abs(win_chance - ideal_win_chance))
        return sum(win_chances)
    
    best_teams = [players[i::num_teams] for i in range(num_teams)]
    best_roles = get_best_roles_for_teams(best_teams)
    best_fairness = evaluate_teams(best_teams, best_roles)

    for _ in range(5000):
        random.shuffle(players)
        current_teams = [players[i::num_teams] for i in range(num_teams)]
        current_roles = get_best_roles_for_teams(current_teams)
        current_fairness = evaluate_teams(current_teams, current_roles)
        if current_fairness < best_fairness:
            best_teams = current_teams
            best_roles = current_roles
            best_fairness = current_fairness


    return best_teams, best_roles

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


def get_win_chances(all_teams: List[List[Player]], mode: GameType = GameType.SM5) -> List[float]:
    win_chances = []

    for i in range(len(all_teams)):
        for j in range(i + 1, len(all_teams)):
            first_team = all_teams[i]
            second_team = all_teams[j]

            logger.info(f"Calculating win chance for teams {i + 1} and {j + 1}")

            win_chances.append(get_win_chance(first_team, second_team, mode))

    if len(all_teams) <= 3:
        win_chances.append(0)
    if len(all_teams) == 2:
        win_chances.append(0)

    return win_chances


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


async def recalculate_sm5_ratings(*, _sample_size: int=99999) -> None:
    """
    Recalculates sm5 ratings

    _sample_size is for testing purposes only, it limits the number of games to recalculate
    """

    # reset sm5 ratings

    logger.info("Resetting sm5 general ratings")

    await Player.all().update(sm5_mu=MU, sm5_sigma=SIGMA)

    # reset per-role ratings

    for role in IntRole:
        if role == IntRole.OTHER:
            continue
        logger.info(f"Resetting {str(role).lower()} ratings")
        await Player.all().update(**{f"{str(role).lower()}_mu": MU, f"{str(role).lower()}_sigma": SIGMA})

    # get all games and recalculate ratings

    sm5_games = await SM5Game.all().order_by("start_time").limit(_sample_size)

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

                if not player:
                    continue

                entity_end.previous_rating_mu = player.sm5_mu
                entity_end.previous_rating_sigma = player.sm5_sigma
                entity_end.current_rating_mu = player.sm5_mu
                entity_end.current_rating_sigma = player.sm5_sigma

                await entity_end.save()


async def recalculate_laserball_ratings(*, _sample_size: int=99999) -> None:
    """
    Recalculates laserball ratings
    """

    # reset laserball ratings

    await Player.all().update(laserball_mu=MU, laserball_sigma=SIGMA)

    lb_games = await LaserballGame.all().order_by("start_time").limit(_sample_size)

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

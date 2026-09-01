import math
from typing import List, Tuple, Union, Optional, TYPE_CHECKING
from copy import deepcopy
from .models.sm5 import SM5Game
from .models.types import EntityType, IntRole, GameType
if TYPE_CHECKING:
    from .models import Player, Game

from openskill.models import PlackettLuceRating, PlackettLuce
from openskill.models.weng_lin.common import phi_major

from django.db.models import Q
SM5_RANK_VERSION = 1
LASERBALL_RANK_VERSION = 1

# CONSTANTS

MU = 25
SIGMA = 25 / 3
BETA = 25 / 6
KAPPA = 0.0001
TAU = 25 / 275  # default: 25/300 (for rating volatility, higher = more volatile ratings)
FEED = 0.8
# How much of an average body's value is handed straight back to the enemy by
# being farmable. 0 = stock openskill behaviour (an extra body is worth its
# full rating just for existing); 1 = an average body is net-zero and a
# below-average one is a liability. Estimated from the two shared tdf logs by
# counting each score swing once at full value (zap 120, missile 600, friendly
# fire -120 against the shooter; base destroys and nukes have no victim):
# points fed / points contributed = 0.73 and 0.76, weakest players break even
# at 0.75-0.90, so the data brackets FEED at roughly 0.7-0.85. The estimation
# method recovers the true value on synthetic ground-truth ladders. When
# enough real uneven-roster games exist, re-fit by sweeping FEED in [0, 1]
# against actual outcomes and keep the best-predicting value.

# mu is for skill, sigma is for uncertainty/confidence
# the higher the mu, the better the player is expected to perform
# the higher the sigma, the less confident we are in the player's skill

# sm5

# TODO: possibly seperate damaged and downed events, but for now they are treated the same

# overall weight for an entire game (mu_weight, sigma_weight) = (1, 1) ( rate([team1, team2]) )
# this is for the overall game outcome (win/loss) which rates all players at once
# the multipliers for mu and sigma are both 1


SM5_HIT_WEIGHT_MU = 0.02  # skill weight for hits in sm5
SM5_HIT_WEIGHT_SIGMA = 0.01  # uncertainty weight for hits in sm5

SM5_HIT_MEDIC_WEIGHT_MU = 0.04  # skill weight for medic hits in sm5
SM5_HIT_MEDIC_WEIGHT_SIGMA = 0.01  # uncertainty weight for medic hits in sm5


SM5_MISSILE_WEIGHT_MU = 0.05  # skill weight for missile hits in sm5
SM5_MISSILE_WEIGHT_SIGMA = 0.01  # uncertainty weight for missile hits in sm5

SM5_MISSILE_MEDIC_WEIGHT_MU = 0.1  # skill weight for medic missiles in sm5
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
            teams_ratings = self._calculate_team_ratings(teams)
            a = teams_ratings[0]
            b = teams_ratings[1]

            # CUSTOM ADDITION: per-body feed cost.
            # In SM5 a player both scores points and concedes ("feeds") them,
            # so a body's worth is measured against an ABSENT player, not a
            # zero-skill floor. Subtracting zeta per body cancels exactly when
            # team sizes are equal (even matchups are unchanged) and removes
            # the +mu "existence bonus" an extra body otherwise gets.
            # Unlike the previous mu-inflation approach this does NOT mutate
            # the rating objects passed in.
            zeta = FEED * self.mu
            mu_a = a.mu - len(teams[0]) * zeta
            mu_b = b.mu - len(teams[1]) * zeta

            total_player_count = len(teams[0]) + len(teams[1])

            result = phi_major(
                (mu_a - mu_b)
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

def introle_to_name(role: int):
    from .models.types import IntRole
    return IntRole(role).to_role().value

BLANK_RATING_PER_SITE = {
    "sm5": {
        "mu": MU,
        "sigma": SIGMA
    },
    "commander": {
        "mu": MU,
        "sigma": SIGMA
    },
    "heavy": {
        "mu": MU,
        "sigma": SIGMA
    },
    "scout": {
        "mu": MU,
        "sigma": SIGMA
    },
    "ammo": {
        "mu": MU,
        "sigma": SIGMA
    },
    "medic": {
        "mu": MU,
        "sigma": SIGMA
    },
    "laserball": {
        "mu": MU,
        "sigma": SIGMA
    }
}

BLANK_ENTITY_RATING = {
    "previous": {
        "global": {
            "mu": MU,
            "sigma": SIGMA
        },
        "global_role": {
            "mu": MU,
            "sigma": SIGMA
        },
        "site": {
            "mu": MU,
            "sigma": SIGMA
        },
        "site_role": {
            "mu": MU,
            "sigma": SIGMA
        }
    },
    "current": {
        "global": {
            "mu": MU,
            "sigma": SIGMA
        },
        "global_role": {
            "mu": MU,
            "sigma": SIGMA
        },
        "site": {
            "mu": MU,
            "sigma": SIGMA
        },
        "site_role": {
            "mu": MU,
            "sigma": SIGMA
        }
    }
}

# Player object that we use when a player isn't logged in.
# we just assume the default rating for that player, and we don't save the rating back to the database
# (the rating has high uncertainty)
# TODO: possibly allow this rating to change throughout the game to improve the accuracy as the game goes on
class FakeDefaultPlayer:
    def __init__(self, site_id: int):
        self.ratings = {"global": deepcopy(BLANK_RATING_PER_SITE), site_id: deepcopy(BLANK_RATING_PER_SITE)}

    async def asave(self):
        pass

async def update_sm5_rankings(game: SM5Game) -> bool:
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
    
    print(f"Updating SM5 rankings for game {game.id}...")
    
    from .models import Event, Player, EventType, IntRole, EntityStart

    # need to update previous rating and for each entity end object

    async for entity_end in game.entity_ends.filter(entity__type=EntityType.PLAYER).select_related("entity").all():
        player = await Player.objects.filter(entity_id=entity_end.entity.entity_id).afirst()

        if player:
            ratings = player.ratings
        else:
            ratings = {"global": deepcopy(BLANK_RATING_PER_SITE), game.site_id: deepcopy(BLANK_RATING_PER_SITE)}


        entity_end.ratings = {
            "previous": {
                "global": {
                    "mu": ratings["global"]["sm5"]["mu"],
                    "sigma": ratings["global"]["sm5"]["sigma"]
                },
                "global_role": {
                    "mu": ratings["global"][introle_to_name(entity_end.entity.role)]["mu"],
                    "sigma": ratings["global"][introle_to_name(entity_end.entity.role)]["sigma"]
                },
                "site": {
                    "mu": ratings[game.site_id]["sm5"]["mu"],
                    "sigma": ratings[game.site_id]["sm5"]["sigma"]
                },
                "site_role": {
                    "mu": ratings[game.site_id][introle_to_name(entity_end.entity.role)]["mu"],
                    "sigma": ratings[game.site_id][introle_to_name(entity_end.entity.role)]["sigma"]
                }
            }
        }

        await entity_end.asave()

    # go through all events for each game
    
    async def process_event(event: Event):
        if event.type in [EventType.DAMAGED_OPPONENT, EventType.DOWNED_OPPONENT]:
            hit_mu = SM5_HIT_WEIGHT_MU
            hit_sigma = SM5_HIT_WEIGHT_SIGMA
            medic_hit_mu = SM5_HIT_MEDIC_WEIGHT_MU
            medic_hit_sigma = SM5_HIT_MEDIC_WEIGHT_SIGMA
        elif event.type in [EventType.MISSILE_DAMAGE_OPPONENT, EventType.MISSILE_DOWN_OPPONENT]:
            hit_mu = SM5_MISSILE_WEIGHT_MU
            hit_sigma = SM5_MISSILE_WEIGHT_SIGMA
            medic_hit_mu = SM5_MISSILE_MEDIC_WEIGHT_MU
            medic_hit_sigma = SM5_MISSILE_MEDIC_WEIGHT_SIGMA
        else:
            return

        shooter = await EntityStart.objects.filter(entity_id=event.entity1).afirst()
        shooter_player = await Player.objects.filter(entity_id=shooter.entity_id).afirst()
        if shooter_player:
            shooter_rating = shooter_player.ratings
        else:
            shooter_rating = {"global": deepcopy(BLANK_RATING_PER_SITE), game.site_id: deepcopy(BLANK_RATING_PER_SITE)}

        target = await EntityStart.objects.filter(entity_id=event.entity2).afirst()
        target_player = await Player.objects.filter(entity_id=target.entity_id).afirst()
        if target_player:
            target_rating = target_player.ratings
        else:
            target_rating = {"global": deepcopy(BLANK_RATING_PER_SITE), game.site_id: deepcopy(BLANK_RATING_PER_SITE)}

        # global

        global_out = model.rate(
            [
                [Rating(shooter_rating["global"]["sm5"]["mu"], shooter_rating["global"]["sm5"]["sigma"])],
                [Rating(target_rating["global"]["sm5"]["mu"], target_rating["global"]["sm5"]["sigma"])]
            ],
            ranks=[0, 1]
        )

        # role specific global

        global_role_out = model.rate(
            [
                [Rating(shooter_rating["global"][introle_to_name(shooter.role)]["mu"], shooter_rating["global"][introle_to_name(shooter.role)]["sigma"])],
                [Rating(target_rating["global"][introle_to_name(target.role)]["mu"], target_rating["global"][introle_to_name(target.role)]["sigma"])]
            ],
            ranks=[0, 1]
        )

        # site specific

        site_out = model.rate(
            [
                [Rating(shooter_rating[game.site_id]["sm5"]["mu"], shooter_rating[game.site_id]["sm5"]["sigma"])],
                [Rating(target_rating[game.site_id]["sm5"]["mu"], target_rating[game.site_id]["sm5"]["sigma"])]
            ],
            ranks=[0, 1]
        )

        # site specific role

        site_role_out = model.rate(
            [
                [Rating(shooter_rating[game.site_id][introle_to_name(shooter.role)]["mu"], shooter_rating[game.site_id][introle_to_name(shooter.role)]["sigma"])],
                [Rating(target_rating[game.site_id][introle_to_name(target.role)]["mu"], target_rating[game.site_id][introle_to_name(target.role)]["sigma"])]
            ],
            ranks=[0, 1]
        )

        # update shooter ratings

        # weights

        weight_mu = hit_mu
        weight_sigma = hit_sigma
        # medic hits are important, so give them more weight
        if IntRole(target.role) == IntRole.MEDIC:
            weight_mu = medic_hit_mu
            weight_sigma = medic_hit_sigma

        role_weight = SM5_ROLE_WEIGHT_MULTIPLIERS.get(shooter.role, (1, 1))
        role_weight_mu = role_weight[0]
        role_weight_sigma = role_weight[1]

        shooter_rating["global"]["sm5"].update({
            "mu": (global_out[0][0].mu - shooter_rating["global"]["sm5"]["mu"]) * weight_mu + shooter_rating["global"]["sm5"]["mu"],
            "sigma": (global_out[0][0].sigma - shooter_rating["global"]["sm5"]["sigma"]) * weight_sigma + shooter_rating["global"]["sm5"]["sigma"]
        })
        shooter_rating["global"][introle_to_name(shooter.role)].update({
            "mu": (global_role_out[0][0].mu - shooter_rating["global"][introle_to_name(shooter.role)]["mu"]) * weight_mu * role_weight_mu + shooter_rating["global"][introle_to_name(shooter.role)]["mu"],
            "sigma": (global_role_out[0][0].sigma - shooter_rating["global"][introle_to_name(shooter.role)]["sigma"]) * weight_sigma * role_weight_sigma + shooter_rating["global"][introle_to_name(shooter.role)]["sigma"]
        })
        shooter_rating[game.site_id]["sm5"].update({
            "mu": (site_out[0][0].mu - shooter_rating[game.site_id]["sm5"]["mu"]) * weight_mu + shooter_rating[game.site_id]["sm5"]["mu"],
            "sigma": (site_out[0][0].sigma - shooter_rating[game.site_id]["sm5"]["sigma"]) * weight_sigma + shooter_rating[game.site_id]["sm5"]["sigma"]
        })
        shooter_rating[game.site_id][introle_to_name(shooter.role)].update({
            "mu": (site_role_out[0][0].mu - shooter_rating[game.site_id][introle_to_name(shooter.role)]["mu"]) * weight_mu * role_weight_mu + shooter_rating[game.site_id][introle_to_name(shooter.role)]["mu"],
            "sigma": (site_role_out[0][0].sigma - shooter_rating[game.site_id][introle_to_name(shooter.role)]["sigma"]) * weight_sigma * role_weight_sigma + shooter_rating[game.site_id][introle_to_name(shooter.role)]["sigma"]
        })

        # update target ratings

        # weights

        # don't penalize medics extra just for being medic
        if IntRole(target.role) == IntRole.MEDIC:
            weight_mu = hit_mu
            weight_sigma = hit_sigma

        role_weight = SM5_ROLE_WEIGHT_MULTIPLIERS.get(introle_to_name(target.role), (1, 1))
        role_weight_mu = role_weight[0]
        role_weight_sigma = role_weight[1]

        target_rating["global"]["sm5"].update({
            "mu": (global_out[1][0].mu - target_rating["global"]["sm5"]["mu"]) * weight_mu + target_rating["global"]["sm5"]["mu"],
            "sigma": (global_out[1][0].sigma - target_rating["global"]["sm5"]["sigma"]) * weight_sigma + target_rating["global"]["sm5"]["sigma"]
        })
        target_rating["global"][introle_to_name(target.role)].update({
            "mu": (global_role_out[1][0].mu - target_rating["global"][introle_to_name(target.role)]["mu"]) * weight_mu * role_weight_mu + target_rating["global"][introle_to_name(target.role)]["mu"],
            "sigma": (global_role_out[1][0].sigma - target_rating["global"][introle_to_name(target.role)]["sigma"]) * weight_sigma * role_weight_sigma + target_rating["global"][introle_to_name(target.role)]["sigma"]
        })
        target_rating[game.site_id]["sm5"].update({
            "mu": (site_out[1][0].mu - target_rating[game.site_id]["sm5"]["mu"]) * weight_mu + target_rating[game.site_id]["sm5"]["mu"],
            "sigma": (site_out[1][0].sigma - target_rating[game.site_id]["sm5"]["sigma"]) * weight_sigma + target_rating[game.site_id]["sm5"]["sigma"]
        })
        target_rating[game.site_id][introle_to_name(target.role)].update({
            "mu": (site_role_out[1][0].mu - target_rating[game.site_id][introle_to_name(target.role)]["mu"]) * weight_mu * role_weight_mu + target_rating[game.site_id][introle_to_name(target.role)]["mu"],
            "sigma": (site_role_out[1][0].sigma - target_rating[game.site_id][introle_to_name(target.role)]["sigma"]) * weight_sigma * role_weight_sigma + target_rating[game.site_id][introle_to_name(target.role)]["sigma"]
        })
        
        # save ratings

        if shooter_player:
            shooter_player.ratings = shooter_rating
            await shooter_player.asave()

        if target_player:
            target_player.ratings = target_rating
            await target_player.asave()
    
    async for event in game.events.filter(
        type__in=[EventType.DAMAGED_OPPONENT, EventType.DOWNED_OPPONENT,
            EventType.MISSILE_DAMAGE_OPPONENT,
            EventType.MISSILE_DOWN_OPPONENT, EventType.RESUPPLY_LIVES,
            EventType.RESUPPLY_AMMO]
    ).order_by("time").all():  # only get the events that we need
        await process_event(event)

    # rate game

    team1 = []
    team2 = []

    teams = await game.get_teams()

    async for entity_start in game.entity_starts.filter(type=EntityType.PLAYER).select_related("team").all():
        team_color = entity_start.team.color_name
        if team_color == (teams[0].color_name):
            player = await Player.objects.filter(entity_id=entity_start.entity_id).afirst()
            team1.append((player if player else FakeDefaultPlayer(game.site_id), entity_start))
        else:
            player = await Player.objects.filter(entity_id=entity_start.entity_id).afirst()
            team2.append((player if player else FakeDefaultPlayer(game.site_id), entity_start))

    # general ratings
    team1_general = list(map(lambda pair: Rating(pair[0].ratings["global"]["sm5"]["mu"], pair[0].ratings["global"]["sm5"]["sigma"]), team1))
    team2_general = list(map(lambda pair: Rating(pair[0].ratings["global"]["sm5"]["mu"], pair[0].ratings["global"]["sm5"]["sigma"]), team2))

    if game.winner == teams[0].enum:
        team1_general_new, team2_general_new = model.rate([team1_general, team2_general], ranks=[0, 1])
    else:
        team1_general_new, team2_general_new = model.rate([team1_general, team2_general], ranks=[1, 0])

    for (player, es), rating in zip(team1, team1_general_new):
        player.ratings["global"]["sm5"]["mu"] = rating.mu
        player.ratings["global"]["sm5"]["sigma"] = rating.sigma
        await player.asave()

    for (player, es), rating in zip(team2, team2_general_new):
        player.ratings["global"]["sm5"]["mu"] = rating.mu
        player.ratings["global"]["sm5"]["sigma"] = rating.sigma
        await player.asave()

    # general role-specific ratings
    team1_general_role = list(map(lambda pair: Rating(pair[0].ratings["global"][introle_to_name(pair[1].role)]["mu"], pair[0].ratings["global"][introle_to_name(pair[1].role)]["sigma"]), team1))
    team2_general_role = list(map(lambda pair: Rating(pair[0].ratings["global"][introle_to_name(pair[1].role)]["mu"], pair[0].ratings["global"][introle_to_name(pair[1].role)]["sigma"]), team2))

    if game.winner == teams[0].enum:
        team1_general_role_new, team2_general_role_new = model.rate([team1_general_role, team2_general_role], ranks=[0, 1])
    else:
        team1_general_role_new, team2_general_role_new = model.rate([team1_general_role, team2_general_role], ranks=[1, 0])
    
    for (player, es), rating in zip(team1, team1_general_role_new):
        player.ratings["global"][introle_to_name(es.role)]["mu"] = rating.mu
        player.ratings["global"][introle_to_name(es.role)]["sigma"] = rating.sigma
        await player.asave()
    
    for (player, es), rating in zip(team2, team2_general_role_new):
        player.ratings["global"][introle_to_name(es.role)]["mu"] = rating.mu
        player.ratings["global"][introle_to_name(es.role)]["sigma"] = rating.sigma
        await player.asave()

    # site-specific ratings
    team1_site = list(map(lambda pair: Rating(pair[0].ratings[game.site_id]["sm5"]["mu"], pair[0].ratings[game.site_id]["sm5"]["sigma"]), team1))
    team2_site = list(map(lambda pair: Rating(pair[0].ratings[game.site_id]["sm5"]["mu"], pair[0].ratings[game.site_id]["sm5"]["sigma"]), team2))

    if game.winner == teams[0].enum:
        team1_site_new, team2_site_new = model.rate([team1_site, team2_site], ranks=[0, 1])
    else:
        team1_site_new, team2_site_new = model.rate([team1_site, team2_site], ranks=[1, 0])

    for (player, es), rating in zip(team1, team1_site_new):
        player.ratings[game.site_id]["sm5"]["mu"] = rating.mu
        player.ratings[game.site_id]["sm5"]["sigma"] = rating.sigma
        await player.asave()

    for (player, es), rating in zip(team2, team2_site_new):
        player.ratings[game.site_id]["sm5"]["mu"] = rating.mu
        player.ratings[game.site_id]["sm5"]["sigma"] = rating.sigma
        await player.asave()

    # site-specific role ratings

    team1_site_role = list(map(lambda pair: Rating(pair[0].ratings[game.site_id][introle_to_name(pair[1].role)]["mu"], pair[0].ratings[game.site_id][introle_to_name(pair[1].role)]["sigma"]), team1))
    team2_site_role = list(map(lambda pair: Rating(pair[0].ratings[game.site_id][introle_to_name(pair[1].role)]["mu"], pair[0].ratings[game.site_id][introle_to_name(pair[1].role)]["sigma"]), team2))
    
    if game.winner == teams[0].enum:
        team1_site_role_new, team2_site_role_new = model.rate([team1_site_role, team2_site_role], ranks=[0, 1])
    else:
        team1_site_role_new, team2_site_role_new = model.rate([team1_site_role, team2_site_role], ranks=[1, 0])

    for (player, es), rating in zip(team1, team1_site_role_new):
        player.ratings[game.site_id][introle_to_name(es.role)]["mu"] = rating.mu
        player.ratings[game.site_id][introle_to_name(es.role)]["sigma"] = rating.sigma
        await player.asave()

    for (player, es), rating in zip(team2, team2_site_role_new):
        player.ratings[game.site_id][introle_to_name(es.role)]["mu"] = rating.mu
        player.ratings[game.site_id][introle_to_name(es.role)]["sigma"] = rating.sigma
        await player.asave()

    # need to update current rating and for each entity end object

    async for entity_end in game.entity_ends.filter(entity__type=EntityType.PLAYER).select_related("entity").all():
        player = await Player.objects.filter(entity_id=entity_end.entity.entity_id).afirst()

        if player:
            ratings = player.ratings
        else:
            ratings = {"global": deepcopy(BLANK_RATING_PER_SITE), game.site_id: deepcopy(BLANK_RATING_PER_SITE)}

        entity_end.ratings.update({
            "current": {
                "global": {
                    "mu": ratings["global"]["sm5"]["mu"],
                    "sigma": ratings["global"]["sm5"]["sigma"]
                },
                "global_role": {
                    "mu": ratings["global"][introle_to_name(entity_end.entity.role)]["mu"],
                    "sigma": ratings["global"][introle_to_name(entity_end.entity.role)]["sigma"]
                },
                "site": {
                    "mu": ratings[game.site_id]["sm5"]["mu"],
                    "sigma": ratings[game.site_id]["sm5"]["sigma"]
                },
                "site_role": {
                    "mu": ratings[game.site_id][introle_to_name(entity_end.entity.role)]["mu"],
                    "sigma": ratings[game.site_id][introle_to_name(entity_end.entity.role)]["sigma"]
                }
            }
        })

        await entity_end.asave()

    return True

async def update_laserball_rankings(game: "Game"):
    pass # TODO: rankings for laserball games
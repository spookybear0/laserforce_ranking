from typing import List, Optional, Tuple, TYPE_CHECKING, Dict
from laserforce_ranking.rating import model, GameType, IntRole
from laserforce_ranking.models import RoleLock
import itertools
import math
import random
import statistics
import logging
if TYPE_CHECKING:
    from .models import Player, Game

logger = logging.getLogger(__name__)

async def matchmake_teams(players: List["Player"], num_teams: int=2, mode: GameType = GameType.SM5, site: str="global") -> List[List["Player"]]:
    """
    Algorithm: Basic Matchmaker

    1. Shuffle the teams
    2. Check the fairness of the teams (how close the win chance is to 50%)
    3. If the fairness is better than the previous best, save the teams

    Returns the best teams found after 1000 iterations

    """

    if not 2 <= num_teams <= 4:
        raise ValueError("num_teams must be between 2 and 4")

    async def get_team_rating(team):
        return [await player.get_rating(mode, site) for player in team]
    
    async def evaluate_teams(teams):
        ideal_win_chance = 0.5
        win_chances = []
        for team1, team2 in itertools.combinations(teams, 2):
            team1_rating = await get_team_rating(team1)
            team2_rating = await get_team_rating(team2)
            win_chance = model.predict_win([team1_rating, team2_rating])[0]
            win_chances.append(abs(win_chance - ideal_win_chance))
        return sum(win_chances)

    best_teams = [players[i::num_teams] for i in range(num_teams)]
    best_fairness = await evaluate_teams(best_teams)

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

        current_fairness = await evaluate_teams(current_teams)
        if current_fairness < best_fairness:
            best_teams = current_teams
            best_fairness = current_fairness

    return best_teams

def get_random_roles_for_teams(
    teams: List[List["Player"]],
    role_locks: Optional[Dict[str, RoleLock]] = None,
) -> List[List[IntRole]]:
    """
    Randomly assigns roles while respecting role locks.

    Locked roles are treated as preferences, so conflicting locks are
    allowed. Scout is unlimited and can be randomly selected whenever
    it is included in a player's allowed roles.
    """

    unique_roles = [
        IntRole.COMMANDER,
        IntRole.HEAVY,
        IntRole.AMMO,
        IntRole.MEDIC,
    ]
    result = []

    for team in teams:
        roles = [IntRole.SCOUT] * len(team)
        available = set(unique_roles)
        players = list(range(len(team)))

        # assign scout locks first
        for i, player in enumerate(team):
            lock = role_locks.get(player.entity_id) if role_locks else None

            if lock == RoleLock.SCOUT:
                players.remove(i)

        # collect other locks
        locked = []
        for i in players:
            player = team[i]
            lock = role_locks.get(player.entity_id) if role_locks else None

            if lock and lock != RoleLock.NONE:
                locked.append((i, lock.allowed_roles))

        # prioritize players with fewer choices
        locked.sort(key=lambda x: len(x[1]))

        for i, allowed in locked:
            choices = [
                role for role in allowed
                if role == IntRole.SCOUT or role in available
            ]

            if not choices:
                continue

            role = random.choice(choices)
            roles[i] = role

            if role in available:
                available.remove(role)

            players.remove(i)

        # assign remaining unique roles
        random.shuffle(players)

        for role in available:
            if not players:
                break

            roles[players.pop()] = role

        result.append(roles)

    return result

def get_best_roles_for_teams(teams: List[List["Player"]]) -> List[List[IntRole]]:
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

async def matchmake_teams_with_roles_best_players(players: List["Player"], num_teams: int, mode: GameType = GameType.SM5, site: str="global") -> List[List["Player"]]:
    """
    Algorithm: Best Players for Roles Matchmaker

    1. Assign unique roles (commander, heavy, ammo, medic) to the players with the highest rating for that role
    2. Assign the remaining players as scouts
    3. Shuffle the players and repeat the process until the best combination is found (if using the matchmaker)

    Pros:

    - This algorithm ensures that the best players for each role are assigned to that role, which can lead to more balanced teams

    Cons:

    - This algorithm may not always lead to the most balanced teams overall, as it focuses on individual role ratings rather than overall team ratings
    - This algorithm may lead to less variety in team compositions, as the same players may be assigned to the same roles in every match
    """

    if not 2 <= num_teams <= 4:
        raise ValueError("num_teams must be between 2 and 4")

    async def get_team_rating(team, roles):
        return [await player.get_rating(mode, site, role) for player, role in zip(team, roles)]
    
    async def evaluate_teams(teams, roles):
        ideal_win_chance = 0.5
        win_chances = []
        for team1, team2 in itertools.combinations(teams, 2):
            if len(team1) != len(team2):
                logger.warning("Teams have different player counts!") # this should never happen
                continue

            if len(team1) == 0 or len(team2) == 0: # every team must have at least one player
                continue

            team1_rating = await get_team_rating(team1, roles[teams.index(team1)])
            team2_rating = await get_team_rating(team2, roles[teams.index(team2)])
            win_chance = model.predict_win([team1_rating, team2_rating])[0]
            win_chances.append(abs(win_chance - ideal_win_chance))
        return sum(win_chances)
    
    best_teams = [players[i::num_teams] for i in range(num_teams)]
    best_roles = get_best_roles_for_teams(best_teams)
    best_fairness = await evaluate_teams(best_teams, best_roles)

    for _ in range(5000):
        random.shuffle(players)
        current_teams = [players[i::num_teams] for i in range(num_teams)]
        current_roles = get_best_roles_for_teams(current_teams)
        current_fairness = await evaluate_teams(current_teams, current_roles)
        if current_fairness < best_fairness:
            best_teams = current_teams
            best_roles = current_roles
            best_fairness = current_fairness


    return best_teams, best_roles

async def matchmake_advanced(
        players: List["Player"],
        num_teams: int,
        mode: GameType = GameType.SM5,
        site: str="global",
        role_locks: Optional[Dict[str, RoleLock]]=None,
        *, _attempts: int=0
    ) -> Tuple[List[List["Player"]], List[List[IntRole]]]:
    """
    Algorithm: Advanced Matchmaker

    1. Assign unique roles (commander, heavy, ammo, medic) to the players with the highest rating for that role
    2. Assign the remaining players as scouts
    3. Shuffle the players and repeat the process until the best combination is found (if using the matchmaker)
    4. Evaluate the teams based on win balance, role matchups, role strength, and synergy (if enabled)
    5. If the teams are imbalanced (win chance difference > 5%), redo matchmaking up to 10 times
    6. Return the best teams found after 2000 iterations

    """

    logger.info(f"Starting advanced matchmaking for {len(players)} players into {num_teams} teams in mode {mode} with {role_locks} (attempt {_attempts})")

    if not 2 <= num_teams <= 4:
        raise ValueError("num_teams must be between 2 and 4")

    # feature toggles

    USE_WIN_BALANCE = True
    USE_ROLE_MATCHUPS = True
    USE_ROLE_STRENGTH = True

    # these weights determine how much each factor contributes to the overall score
    # lower is better

    WIN_WEIGHT = 4
    MATCHUP_WEIGHT = 2
    ROLE_BALANCE_WEIGHT = 7

    IMBALANCE_PENALTY_WEIGHT = 0.25

    # search settings

    ITERATIONS = 2000
    INITIAL_TEMP = 1.0
    COOLING_RATE = 0.999

    if not any([USE_WIN_BALANCE, USE_ROLE_MATCHUPS, USE_ROLE_STRENGTH]):
        ITERATIONS = 0

    # how important is it for this role to be balanced in matchups?
    ROLE_WEIGHTS = {
        IntRole.COMMANDER: 0.9,
        IntRole.HEAVY: 1.0,
        IntRole.SCOUT: 0.8,
        IntRole.AMMO: 0.7,
        IntRole.MEDIC: 0.7,
    }
    

    # helpers

    async def get_team_rating(team, roles):
        return [await player.get_rating(mode, site, role) for player, role in zip(team, roles)]

    def role_map(team, roles):
        return {r: p for p, r in zip(team, roles)}

    # role matchups

    async def role_matchup_diff(team1, roles1, team2, roles2):

        map1 = role_map(team1, roles1)
        map2 = role_map(team2, roles2)

        diff = 0

        for role, weight in ROLE_WEIGHTS.items():

            if role in map1 and role in map2:

                r1 = (await map1[role].get_rating(mode, site, role)).ordinal()
                r2 = (await map2[role].get_rating(mode, site, role)).ordinal()

                diff += weight * abs(r1 - r2)

        return diff

    # role strength

    async def team_role_strength(team, roles):

        strength = 0

        for p, r in zip(team, roles):
            strength += (await p.get_rating(mode, site, r)).ordinal()

        return strength

    # check how even teams are and give them a score (lower is better balance, higher is worse balance)

    async def evaluate(teams, roles):
        ideal = 0.5

        win_balance = 0
        matchup_score = 0
        role_balance = 0

        for t1, t2 in itertools.combinations(teams, 2):
            r1 = await get_team_rating(t1, roles[teams.index(t1)])
            r2 = await get_team_rating(t2, roles[teams.index(t2)])

            if USE_WIN_BALANCE:
                win = model.predict_win([r1, r2])[0]
                win_balance += abs(win - ideal) ** 2

            if USE_ROLE_MATCHUPS:
                matchup_score += await role_matchup_diff(
                    t1,
                    roles[teams.index(t1)],
                    t2,
                    roles[teams.index(t2)],
                )

            if USE_ROLE_STRENGTH:
                role_balance += abs(
                    await team_role_strength(t1, roles[teams.index(t1)])
                    - await team_role_strength(t2, roles[teams.index(t2)])
                )

        score_components = []

        if USE_WIN_BALANCE:
            score_components.append(WIN_WEIGHT * win_balance)

        if USE_ROLE_MATCHUPS:
            score_components.append(MATCHUP_WEIGHT * matchup_score)

        if USE_ROLE_STRENGTH:
            score_components.append(ROLE_BALANCE_WEIGHT * role_balance)
        
        imbalance_penalty = statistics.pvariance(score_components) * IMBALANCE_PENALTY_WEIGHT

        score = sum(score_components) + imbalance_penalty

        logger.debug(f"Win Balance: {win_balance*WIN_WEIGHT:.4f}, Role Matchups: {matchup_score*MATCHUP_WEIGHT:.4f}, Role Strength: {role_balance*ROLE_BALANCE_WEIGHT:.4f} | Imbalance Penalty: {imbalance_penalty:.4f} | Total Score: {score:.4f}")
        return score

    # initial solution

    random.shuffle(players)

    teams = [players[i::num_teams] for i in range(num_teams)]
    roles = get_random_roles_for_teams(teams, role_locks)

    best_score = await evaluate(teams, roles)

    temperature = INITIAL_TEMP
    prob = 1.0

    # swap search

    for _ in range(ITERATIONS):
        # pick two teams
        t1, t2 = random.sample(range(num_teams), 2)
        logger.debug(f"Iteration {_ + 1}/{ITERATIONS}, swapping between team {t1 + 1} and team {t2 + 1} with current best score {best_score:.4f} and temperature {temperature:.4f}")

        if not teams[t1] or not teams[t2]:
            continue

        # pick players
        i1 = random.randrange(len(teams[t1]))
        i2 = random.randrange(len(teams[t2]))

        # swap
        teams[t1][i1], teams[t2][i2] = teams[t2][i2], teams[t1][i1]

        new_roles = get_random_roles_for_teams(teams, role_locks)

        new_score = await evaluate(teams, new_roles)

        delta = new_score - best_score

        accept = False

        if delta < 0:
            accept = True
        else:
            prob = math.exp(-delta / max(temperature, 1e-6))
            if random.random() < prob:
                accept = True

        if accept:
            logger.debug(f"Accepted new solution with score {new_score:.4f} (delta: {delta:.4f}, prob: {prob:.4f})")
            roles = new_roles
            best_score = new_score
        else:
            logger.debug(f"Rejected new solution with score {new_score:.4f} (delta: {delta:.4f}, prob: {prob:.4f}) keep current score {best_score:.4f}")
            # revert swap
            teams[t1][i1], teams[t2][i2] = teams[t2][i2], teams[t1][i1]

        temperature *= COOLING_RATE

    logger.info(f"Finished advanced matchmaking with score {best_score:.4f}")

    _attempts += 1

    # check win chances for the final teams, if >5% difference, redo matchmaking up to 3 times
    if _attempts >= 10:
        logger.warning("Advanced matchmaking reached maximum attempts, returning best found solution")
        return teams, roles
    
    win_chances = await get_win_chances(teams, mode=mode, roles=roles)

    if any(abs(win - 0.5) > 0.05 for row in win_chances for win in row if win is not None):
        logger.info(f"Win chances for teams are imbalanced: {win_chances}, redoing matchmaking (attempt {_attempts}/3)")
        return await matchmake_advanced(players, num_teams, mode=mode, site=site, role_locks=role_locks, _attempts=_attempts)

    return teams, roles


async def get_win_chance(team1: List["Player"], team2: List["Player"], mode: GameType = GameType.SM5, site: str="global", roles: Optional[List[List[IntRole]]]=None) -> List[float]:
    """
    Gets win chance for two teams
    """

    logger.debug(f"Getting win chance for {team1} vs {team2}")

    if roles:
        team1 = [await p.get_rating(mode, site, r) for p, r in zip(team1, roles[0])]
        team2 = [await p.get_rating(mode, site, r) for p, r in zip(team2, roles[1])]
    else:
        # get rating object for mode
        team1 = [await p.get_rating(mode, site) for p in team1]
        team2 = [await p.get_rating(mode, site) for p in team2]

    # predict
    return model.predict_win([team1, team2])


async def get_win_chances(
    all_teams: List[List["Player"]],
    mode: GameType = GameType.SM5,
    site: str = "global",
    roles: Optional[List[List[IntRole]]] = None,
) -> List[List[Optional[float]]]:

    n = len(all_teams)
    win_chances = [[None] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            match_roles = [roles[i], roles[j]] if roles else None

            team1_chance, team2_chance = await get_win_chance(
                all_teams[i],
                all_teams[j],
                mode,
                site,
                match_roles,
            )

            win_chances[i][j] = team1_chance
            win_chances[j][i] = team2_chance
    return win_chances
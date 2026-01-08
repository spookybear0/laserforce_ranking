from sanic import Request
from sanic.log import logger

from db.sm5 import SM5Game
from db.laserball import LaserballGame
from helpers import ratinghelper
from db.types import IntRole
from shared import app
from utils import admin_only

@app.post("/admin/audit_ranked_status/<type:str>")
@admin_only
async def audit_ranked_status(request: Request, type: str) -> str:
    response = await request.respond(content_type="text/html")

    logger.info(f"Starting ranked status audit for type: {type}")

    # type is either "sm5" or "laserball" or "all"

    if type not in ["sm5", "laserball", "all"]:
        return response.json({"status": "error", "message": "Invalid type"})
    
    # go through each game and check ranked eligibility
    if type in ["sm5", "all"]:
        sm5_games = await SM5Game.all().order_by("start_time")
        for game in sm5_games:
            # maybe eventually make elgibility criteria in a helper function

            ranked = True

            teams = await game.teams.all()
            entity_starts = await game.entity_starts.all()

            team1 = None
            team2 = None

            index = 1

            for t in teams:
                if not t.color_name or not t.color_enum or t.name == "Neutral":
                    continue

                if index == 1:
                    team1 = t
                else:  # 2
                    team2 = t

                index += 1

            team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
            team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()

            if team1_len > 7 or team2_len > 7 or team1_len < 5 or team2_len < 5 or team1_len != team2_len:
                ranked = False

            
            for t in teams:
                total_count = 0
                commander_count = 0
                heavy_count = 0
                scout_count = 0
                ammo_count = 0
                medic_count = 0

                for e in entity_starts:
                    if e.type == "player" and e.team == t:
                        total_count += 1
                        if e.role == IntRole.COMMANDER:
                            commander_count += 1
                        elif e.role == IntRole.HEAVY:
                            heavy_count += 1
                        elif e.role == IntRole.SCOUT:
                            scout_count += 1
                        elif e.role == IntRole.AMMO:  # sometimes we have 2 ammos, but for ranking purposes we only want games with 1
                            ammo_count += 1
                        elif e.role == IntRole.MEDIC:
                            medic_count += 1

                if total_count == 0:  # probably a neutral team
                    continue

                if commander_count != 1 or heavy_count != 1 or ammo_count != 1 or medic_count != 1 or scout_count < 1 or scout_count > 3:
                    ranked = False
            

            for e in entity_starts:
                if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
                    ranked = False
                    break

            if ranked != game.ranked:
                logger.info(f"SM5 Game ID {game.id} ranked status changed from {game.ranked} to {ranked}")
                game.ranked = ranked
                await game.save()

                # unranked -> ranked

                if ranked:
                    await ratinghelper.update_sm5_ratings(game)

    if type in ["laserball", "all"]:
        laserball_games = await LaserballGame.all().order_by("start_time")
        for game in laserball_games:
            ranked = True

            teams = await game.teams.all()
            entity_starts = await game.entity_starts.all()

            team1 = None
            team2 = None

            index = 1

            for t in teams:
                if not t.color_name or not t.color_enum or t.name == "Neutral":
                    continue

                if index == 1:
                    team1 = t
                else:  # 2
                    team2 = t

                index += 1
            
            team1_len = await game.entity_ends.filter(entity__team=team1, entity__type="player").count()
            team2_len = await game.entity_ends.filter(entity__team=team2, entity__type="player").count()
            
            if team1_len < 2 or team2_len < 2:
                ranked = False

            for e in entity_starts:
                if e.type == "player" and e.entity_id.startswith("@") and e.name == e.battlesuit:
                    logger.debug(f"Found non-member player {e.name}, unranking game")
                    ranked = False
                    break

            if ranked != game.ranked:
                logger.info(f"Laserball Game ID {game.id} ranked status changed from {game.ranked} to {ranked}")
                game.ranked = ranked
                await game.save()

                # unranked -> ranked

                if ranked:
                    await ratinghelper.update_laserball_ratings(game)

    return response.json({"status": "ok"})
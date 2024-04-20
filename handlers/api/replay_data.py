from db.sm5 import SM5Game
from helpers.replay_sm5 import create_sm5_replay
from shared import app
from helpers.statshelper import sentry_trace
from sanic import Request, response, HTTPResponse


@app.get("/api/game/<type:str>/<id:int>/replay_data")
@sentry_trace
async def api_game_tdf(request: Request, type: str, id: int) -> HTTPResponse:
    if type.lower() == "sm5":
        game = await SM5Game.filter(id=id).first()
        replay = await create_sm5_replay(game)
    else:
        raise ValueError("Invalid game type")

    return response.html(replay.export_to_js(), headers={"Content-Type": "text/javascript"})

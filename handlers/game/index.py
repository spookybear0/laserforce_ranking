from sanic import Request
from shared import app
from utils import render_template
from parse_tdf import parse_sm5_game as parse_sm5_game_
from helpers.tdfhelper import parse_sm5_game
from db.models import SM5Game

@app.get("/game/<id:int>/")
async def game_index(request: Request, id: int):
    game = await SM5Game.filter(id=id).first()

    
    return await render_template(request, "game/index.html",
                                game_id=id, game_date=game.start_time)
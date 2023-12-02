from sanic import Request, exceptions, response
from shared import app
from utils import get_post
from helpers.tdfhelper import parse_sm5_game, parse_laserball_game
from helpers.statshelper import sentry_trace
from sanic.log import logger

@app.get("/util/auto_upload_dl")
async def auto_upload_dl(request: Request) -> str:
    return response.file("./upload_scripts/upload.bat")

@app.post("/util/upload_tdf")
@sentry_trace
async def auto_upload(request: Request) -> str:
    logger.info("Uploading TDF")

    data = get_post(request)
    type = data.get("type")
    file = request.files.get("upload_file")

    logger.debug(f"Type: {type}")
    logger.debug(f"File: {file}")
    
    if file is None:
        raise exceptions.BadRequest()

    if type == "sm5":
        open("./sm5_tdf/" + file.name, "wb").write(file.body)
        await parse_sm5_game("./sm5_tdf/" + file.name)
    elif type == "laserball":
        open("./laserball_tdf/" + file.name, "wb").write(file.body)
        await parse_laserball_game("./laserball_tdf/" + file.name)
    else:
        raise exceptions.BadRequest()
    
    logger.info("Uploaded TDF successfully!")

    return response.text("Uploaded!")
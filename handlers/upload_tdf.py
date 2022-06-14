from aiohttp import web
from shared import routes
from helpers import userhelper

@routes.get("/util/auto_upload_dl")
async def auto_upload_dl(request: web.Request):
    return web.FileResponse("./upload_scripts/upload.bat")

@routes.post("/util/upload_tdf")
async def auto_upload(request: web.Request):
    return web.HTTPNotImplemented()
    
    data = await request.post()
    type = data.get("type")
    file = data["upload_file"]
    
    if not file:
        return web.HTTPBadRequest("No file uploaded")

    if type == "sm5":
        open("./sm5_tdf/" + file.filename, "wb").write(file.file.read())
        #game = parse_sm5_game("./sm5_tdf/" + file.filename)
    elif type == "laserball":
        open("./laserball_tdf/" + file.filename, "wb").write(file.file.read())
        #game = parse_laserball_game("./laserball_tdf/" + file.filename)
    else:
        return web.HTTPBadRequest("Unknown type")

    return web.HTTPOk()
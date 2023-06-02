from sanic import Request, exceptions, response
from shared import app
from utils import get_post

@app.get("/util/auto_upload_dl")
async def auto_upload_dl(request: Request):
    return response.file("./upload_scripts/upload.bat")

@app.post("/util/upload_tdf")
async def auto_upload(request: Request):
    data = get_post(request)
    type = data.get("type")
    file = data["upload_file"]
    
    if not file:
        raise exceptions.BadRequest()

    if type == "sm5":
        open("./sm5_tdf/" + file.filename, "wb").write(file.file.read())
        #game = parse_sm5_game("./sm5_tdf/" + file.filename)
    elif type == "laserball":
        open("./laserball_tdf/" + file.filename, "wb").write(file.file.read())
        #game = parse_laserball_game("./laserball_tdf/" + file.filename)
    else:
        raise exceptions.BadRequest()

    return response.text("Uploaded!")
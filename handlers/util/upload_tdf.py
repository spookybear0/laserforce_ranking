from pathlib import Path

from sanic import Request, exceptions, response
from sanic.log import logger

from helpers.statshelper import sentry_trace
from helpers.tdfhelper import parse_sm5_game, parse_laserball_game
from shared import app
from utils import get_post


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
        target_path = "./sm5_tdf/" + file.name
        _create_file_from_request(file, target_path)
        await parse_sm5_game(target_path)
    elif type == "laserball":
        target_path = "./laserball_tdf/" + file.name
        _create_file_from_request(file, target_path)
        await parse_laserball_game(target_path)
    else:
        raise exceptions.BadRequest()

    logger.info("Uploaded TDF successfully!")

    return response.text("Uploaded!")


def _create_file_from_request(request_file, target_path: str):
    """Reads the data from a request's file and stores it a local file.

    Creates the path structure leading up to the target path if it doesn't
    exist already.

    Args:
        request_file: The file from the HTTP request.
        target_path: The path to store this file in. Can be relative.
    """
    filepath = Path(target_path)

    # Create the directory if it doesn't exist already.
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Copy the entire contents of the request file into the target file.
    open(target_path, "wb").write(request_file.body)

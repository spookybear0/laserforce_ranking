from pathlib import Path

from sanic import Request, exceptions, response
from sanic.log import logger
from typing import Union

from helpers.statshelper import sentry_trace
from helpers.tdfhelper import parse_sm5_game, parse_laserball_game
from shared import app
import sentry_sdk
from config import config
import aiohttp
import json

"""
@app.get("/util/auto_upload_dl")
async def auto_upload_dl(request: Request) -> str:
    return await response.file("./upload_scripts/upload.bat")
"""


@app.post("/util/upload_tdf")
@sentry_trace
async def auto_upload(request: Request) -> str:
    logger.info("Uploading TDF")

    type = request.form.get("type")
    file = request.files.get("upload_file")

    logger.debug(f"Type: {type}")
    logger.debug(f"File: {file}")

    sentry_sdk.set_context("upload_tdf", {"type": type, "file": file})

    if file is None:
        logger.error("No file provided in the request.")
        raise exceptions.BadRequest("No file provided in the request.")

    if type == "sm5":
        target_path = "./sm5_tdf/" + file.name
        _create_file_from_request(file, target_path)
        await parse_sm5_game(target_path)
    elif type == "sm5_3team":
        target_path = "./sm5_3team_tdf/" + file.name
        _create_file_from_request(file, target_path)
        # don't parse 3 team games, since they are not supported yet
    elif type == "laserball":
        target_path = "./laserball_tdf/" + file.name
        _create_file_from_request(file, target_path)
        await parse_laserball_game(target_path)
    elif type == "dnd":
        target_path = "./dnd_tdf/" + file.name
        _create_file_from_request(file, target_path)
        # don't parse DnD games, since they are not supported yet
    else:
        logger.error(f"Unsupported type: {type}")
        raise exceptions.BadRequest(f"Unsupported type: {type}")

    logger.info("Uploaded TDF successfully!")

    if config["lfstats_session_token"] and config["lfstats_csrf_token"]:
        try:
            await upload_to_lfstats(target_path)
        except Exception as e:
            logger.error(f"Failed to upload to lfstats: {e}")
            sentry_sdk.capture_exception(e)

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

async def upload_to_lfstats(file_path: Union[Path, str]):
    path = Path(file_path)

    cookies = {
        "__Secure-authjs.callback-url": "https%3A%2F%2Flfstats.com%2Fupload",
        "__Secure-authjs.session-token": config["lfstats_session_token"],
        "__Host-authjs.csrf-token": config["lfstats_csrf_token"],
    }

    async with aiohttp.ClientSession(cookies=cookies) as session:

        # go to /upload to find presigned url

        body = json.dumps(
            [[path.name], None],
            separators=(",", ":"),
        )

        ROUTER_STATE = (
            '["",{"children":["upload",{"children":["__PAGE__",{},null,null,4096]},'
            'null,null,4096]},null,null,4112]'
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) "
                "Gecko/20100101 Firefox/155.0"
            ),
            "Accept": "text/x-component",
            "Referer": "https://lfstats.com/upload",
            "next-action": "6017cf7a3ca428c82dc065fd19656a709ea0ce1fc8",
            "next-router-state-tree": ROUTER_STATE,
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": "https://lfstats.com",
        }

        logger.info(f"Uploading {path.name} to lfstats.com")

        async with session.post(
            "https://lfstats.com/upload",
            data=body,
            headers=headers,
        ) as response:

            response.raise_for_status()
            result = await response.text()

        # get presigned url

        result = json.loads(result.split("1:", 1)[1])
        presigned_url = result["uploads"][0]["url"]

        # PUT to S3

        with path.open("rb") as f:
            async with session.put(
                presigned_url,
                data=f,
                headers={
                    "Content-Type": "application/octet-stream",
                },
            ) as response:

                response.raise_for_status()

                logger.info(f"Uploaded {path.name} to lfstats.com successfully!")
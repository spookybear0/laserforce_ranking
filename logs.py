import logging

# reset
open("general.log", "w")
open("elo_cron.log", "w")
open("player_cron.log", "w")

fmt = logging.Formatter("%(name)s :: %(asctime)s - %(levelname)s: %(message)s")

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

# default
logger.setLevel(logging.DEBUG)
elo_logger.setLevel(logging.DEBUG)
player_logger.setLevel(logging.DEBUG)

handler = logging.FileHandler("general.log", mode="a")
handler.setFormatter(fmt)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

handler = logging.FileHandler("elo_cron.log", mode="a")
handler.setFormatter(fmt)
handler.setLevel(logging.DEBUG)
elo_logger.addHandler(handler)

handler = logging.FileHandler("player_cron.log", mode="a")
handler.setFormatter(fmt)
handler.setLevel(logging.DEBUG)
player_logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(fmt)
handler.setLevel(logging.WARNING)
logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(fmt)
handler.setLevel(logging.WARNING)
elo_logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(fmt)
handler.setLevel(logging.ERROR)
player_logger.addHandler(handler)
    
def get_log(log: str):
    with open(f"{log}.log", "r") as f:
        try:
            last_line = f.readlines()[-1]
        except IndexError:
            return ""
        return last_line
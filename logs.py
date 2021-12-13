import logging

fmt = logging.Formatter("%(name)s :: %(asctime)s - %(levelname)s: %(message)s")

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

handler = logging.FileHandler("general.log", mode="w")
handler.setFormatter(fmt)
logger.addHandler(handler)

handler = logging.FileHandler("elo_cron.log", mode="w")
handler.setFormatter(fmt)
elo_logger.addHandler(handler)

handler = logging.FileHandler("player_cron.log", mode="w")
handler.setFormatter(fmt)
player_logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(fmt)
logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(fmt)
elo_logger.addHandler(handler)

handler = logging.StreamHandler()
handler.setFormatter(fmt)
player_logger.addHandler(handler)
    
def get_log(log: str):
    return open(f"{log}.log", "r").read()
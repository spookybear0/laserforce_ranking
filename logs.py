import logging

fmt = logging.Formatter("%(name)s :: %(asctime)s - %(levelname)s: %(message)s")

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

logger.setLevel(logging.DEBUG)
elo_logger.setLevel(logging.DEBUG)
player_logger.setLevel(logging.DEBUG)

logger.setFormatter(fmt)
elo_logger.setFormatter(fmt)
player_logger.setFormatter(fmt)

logger.addHandler(logging.FileHandler("general.log", mode="w"))
elo_logger.addHandler(logging.FileHandler("elo_cron.log", mode="w"))
player_logger.addHandler(logging.FileHandler("player_cron.log", mode="w"))

logger.addHandler(logging.StreamHandler())
elo_logger.addHandler(logging.StreamHandler())
player_logger.addHandler(logging.StreamHandler())
    
def get_log(log: str):
    return open(f"{log}.log", "r").read()
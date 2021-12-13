import logging

fmt = logging.Formatter("%(name)s :: %(asctime)s - %(levelname)s: %(message)s")

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

logger.setLevel(logging.DEBUG)
elo_logger.setLevel(logging.DEBUG)
player_logger.setLevel(logging.DEBUG)

logger.addHandler(logging.FileHandler("general.log", mode="w").setFormatter(fmt))
elo_logger.addHandler(logging.FileHandler("elo_cron.log", mode="w").setFormatter(fmt))
player_logger.addHandler(logging.FileHandler("player_cron.log", mode="w").setFormatter(fmt))

logger.addHandler(logging.StreamHandler().setFormatter(fmt))
elo_logger.addHandler(logging.StreamHandler().setFormatter(fmt))
player_logger.addHandler(logging.StreamHandler().setFormatter(fmt))
    
def get_log(log: str):
    return open(f"{log}.log", "r").read()
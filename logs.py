import logging

def hook(hookfunc, oldfunc):
    def hooked(*args, **kwargs):
        hookfunc()
        return oldfunc(*args, **kwargs)
    return hooked

def log_hook():
    # make it one line
    open("general.log", "w+")
    open("elo_cron.log", "w+")
    open("player_cron.log", "w+")

fmt = logging.Formatter("%(name)s :: %(asctime)s - %(levelname)s: %(message)s")

logger = logging.getLogger("general")
elo_logger = logging.getLogger("elo cron")
player_logger = logging.getLogger("player cron")

logger._log = hook(log_hook, logger._log)
elo_logger._log = hook(log_hook, elo_logger._log)
player_logger._log = hook(log_hook, player_logger._log)

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
    return open(f"{log}.log", "r").read()
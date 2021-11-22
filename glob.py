import datetime

def player_cron_log(text: str):
    open("player_cron.log", "w").write(f"{datetime.datetime.now()} - {text}")
    
def get_player_cron_log():
    return open("player_cron.log", "r").read()


def rank_cron_log(text: str):
    open("rank_cron.log", "w").write(f"{datetime.datetime.now()} - {text}")
    
def get_rank_cron_log():
    return open("rank_cron.log", "r").read()
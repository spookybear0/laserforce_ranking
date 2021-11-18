

def cron_log(text: str):
    open("cron.log", "w").write(text)
    
def get_cron_log():
    return open("cron.log", "r").read()
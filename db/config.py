def get_tortoise_orm_config(config_obj):
    return {
        "connections": {
            "default": f"mysql://{config_obj['db_user']}:{config_obj['db_password']}@{config_obj['db_host']}:{config_obj['db_port']}/{config_obj['db_name']}",
        },
        "apps": {
            "models": {
                "models": ["db.game", "db.laserball", "db.legacy", "db.player", "db.sm5", "db.tag", "aerich.models"],
                "default_connection": "default"
            }
        }
    }
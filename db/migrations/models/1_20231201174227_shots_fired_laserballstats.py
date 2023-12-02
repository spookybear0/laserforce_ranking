from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:

    return """
        ALTER TABLE `laserballstats` ADD `shots_fired` INT NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `laserballstats` DROP COLUMN `shots_fired`;"""

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` ADD `_team1_double_percent` DOUBLE;
        ALTER TABLE `sm5game` ADD `_team2_double_percent` DOUBLE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` DROP COLUMN `_team1_double_percent`;
        ALTER TABLE `sm5game` DROP COLUMN `_team2_double_percent`;"""

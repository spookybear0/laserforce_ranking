from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` ADD `team1_size` INT NOT NULL;
        ALTER TABLE `sm5game` ADD `team2_size` INT NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` DROP COLUMN `team1_size`;
        ALTER TABLE `sm5game` DROP COLUMN `team2_size`;"""

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` ADD `last_team_standing` VARCHAR(5)   COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `sm5game` ADD `laserrank_version` INT NOT NULL  DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` DROP COLUMN `last_team_standing`;
        ALTER TABLE `sm5game` DROP COLUMN `laserrank_version`;"""

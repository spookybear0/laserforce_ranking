from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `entitystarts` MODIFY COLUMN `role` SMALLINT NOT NULL  COMMENT 'OTHER: 0\nCOMMANDER: 1\nHEAVY: 2\nSCOUT: 3\nAMMO: 4\nMEDIC: 5';
        ALTER TABLE `events` ADD `entity1` VARCHAR(50) NOT NULL;
        ALTER TABLE `events` ADD `action` VARCHAR(50) NOT NULL;
        ALTER TABLE `events` ADD `entity2` VARCHAR(50) NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `events` DROP COLUMN `entity1`;
        ALTER TABLE `events` DROP COLUMN `action`;
        ALTER TABLE `events` DROP COLUMN `entity2`;
        ALTER TABLE `entitystarts` MODIFY COLUMN `role` SMALLINT NOT NULL  COMMENT 'BASE: 0\nCOMMANDER: 1\nHEAVY: 2\nSCOUT: 3\nAMMO: 4\nMEDIC: 5';"""

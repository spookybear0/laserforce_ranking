from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `events` ALTER COLUMN `action` SET DEFAULT '';
        ALTER TABLE `events` ALTER COLUMN `entity2` SET DEFAULT '';
        ALTER TABLE `events` ALTER COLUMN `entity1` SET DEFAULT '';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `events` ALTER COLUMN `action` DROP DEFAULT;
        ALTER TABLE `events` ALTER COLUMN `entity2` DROP DEFAULT;
        ALTER TABLE `events` ALTER COLUMN `entity1` DROP DEFAULT;"""

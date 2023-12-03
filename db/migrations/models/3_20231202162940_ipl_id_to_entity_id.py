from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `player` RENAME COLUMN `ipl_id` TO `entity_id`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `player` RENAME COLUMN `entity_id` TO `ipl_id`;"""

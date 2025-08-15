from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `player` DROP COLUMN `rfid_tags`;
        CREATE TABLE IF NOT EXISTS `tag` (
    `id` VARCHAR(64) NOT NULL  PRIMARY KEY,
    `type` VARCHAR(2) NOT NULL  COMMENT 'LF: LF\nHF: HF',
    `player_id` INT,
    CONSTRAINT `fk_tag_player_468b05a7` FOREIGN KEY (`player_id`) REFERENCES `player` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `player` ADD `rfid_tags` JSON NOT NULL;
        DROP TABLE IF EXISTS `tag`;"""

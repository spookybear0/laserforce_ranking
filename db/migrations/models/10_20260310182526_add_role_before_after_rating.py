from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `entityends` ADD `previous_role_rating_mu` DOUBLE;
        ALTER TABLE `entityends` ADD `current_role_rating_mu` DOUBLE;
        ALTER TABLE `entityends` ADD `current_role_rating_sigma` DOUBLE;
        ALTER TABLE `entityends` ADD `previous_role_rating_sigma` DOUBLE;
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `role` VARCHAR(9) NOT NULL  COMMENT 'COMMANDER: commander\nHEAVY: heavy\nSCOUT: scout\nAMMO: ammo\nMEDIC: medic';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `role` VARCHAR(9) NOT NULL  COMMENT 'COMMANDER: commander\nHEAVY: heavy\nSCOUT: scout\nAMMO: ammo\nMEDIC: medic';
        ALTER TABLE `tag` MODIFY COLUMN `player_id` INT NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tag` MODIFY COLUMN `player_id` INT;
        ALTER TABLE `entityends` DROP COLUMN `previous_role_rating_mu`;
        ALTER TABLE `entityends` DROP COLUMN `current_role_rating_mu`;
        ALTER TABLE `entityends` DROP COLUMN `current_role_rating_sigma`;
        ALTER TABLE `entityends` DROP COLUMN `previous_role_rating_sigma`;
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `role` VARCHAR(9) NOT NULL  COMMENT 'SCOUT: scout\nHEAVY: heavy\nCOMMANDER: commander\nMEDIC: medic\nAMMO: ammo';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `role` VARCHAR(9) NOT NULL  COMMENT 'SCOUT: scout\nHEAVY: heavy\nCOMMANDER: commander\nMEDIC: medic\nAMMO: ammo';"""

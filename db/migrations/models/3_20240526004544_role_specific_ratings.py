from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacylaserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacysm5game` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `player` ADD `ammo_mu` DOUBLE NOT NULL  DEFAULT 25;
        ALTER TABLE `player` ADD `scout_sigma` DOUBLE NOT NULL  DEFAULT 8.333;
        ALTER TABLE `player` ADD `scout_mu` DOUBLE NOT NULL  DEFAULT 25;
        ALTER TABLE `player` ADD `commander_sigma` DOUBLE NOT NULL  DEFAULT 8.333;
        ALTER TABLE `player` ADD `medic_mu` DOUBLE NOT NULL  DEFAULT 25;
        ALTER TABLE `player` ADD `ammo_sigma` DOUBLE NOT NULL  DEFAULT 8.333;
        ALTER TABLE `player` ADD `medic_sigma` DOUBLE NOT NULL  DEFAULT 8.333;
        ALTER TABLE `player` ADD `heavy_sigma` DOUBLE NOT NULL  DEFAULT 8.333;
        ALTER TABLE `player` ADD `heavy_mu` DOUBLE NOT NULL  DEFAULT 25;
        ALTER TABLE `player` ADD `commander_mu` DOUBLE NOT NULL  DEFAULT 25;
        ALTER TABLE `sm5game` MODIFY COLUMN `winner` VARCHAR(5)   COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `player` DROP COLUMN `ammo_mu`;
        ALTER TABLE `player` DROP COLUMN `scout_sigma`;
        ALTER TABLE `player` DROP COLUMN `scout_mu`;
        ALTER TABLE `player` DROP COLUMN `commander_sigma`;
        ALTER TABLE `player` DROP COLUMN `medic_mu`;
        ALTER TABLE `player` DROP COLUMN `ammo_sigma`;
        ALTER TABLE `player` DROP COLUMN `medic_sigma`;
        ALTER TABLE `player` DROP COLUMN `heavy_sigma`;
        ALTER TABLE `player` DROP COLUMN `heavy_mu`;
        ALTER TABLE `player` DROP COLUMN `commander_mu`;
        ALTER TABLE `sm5game` MODIFY COLUMN `winner` VARCHAR(5)   COMMENT 'RED: red\nGREEN: green\nBLUE: blue';
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue';
        ALTER TABLE `legacysm5game` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue';
        ALTER TABLE `legacylaserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue';"""

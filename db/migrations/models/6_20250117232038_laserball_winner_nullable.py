from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacylaserballgame` MODIFY COLUMN `winner` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacylaserballgame` MODIFY COLUMN `winner` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `team` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `team` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacysm5game` MODIFY COLUMN `winner` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacysm5game` MODIFY COLUMN `winner` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `team` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `team` VARCHAR(7) NOT NULL  COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `sm5game` MODIFY COLUMN `last_team_standing` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `sm5game` MODIFY COLUMN `last_team_standing` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `sm5game` MODIFY COLUMN `winner` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';
        ALTER TABLE `sm5game` MODIFY COLUMN `winner` VARCHAR(7)   COMMENT 'Neutral Team: neutral\nFire Team: red\nEarth Team: green\nIce Team: blue\nYellow Team: yellow\nPurple Team: purple';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `sm5game` MODIFY COLUMN `last_team_standing` VARCHAR(5)   COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `sm5game` MODIFY COLUMN `last_team_standing` VARCHAR(5)   COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `sm5game` MODIFY COLUMN `winner` VARCHAR(5)   COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `sm5game` MODIFY COLUMN `winner` VARCHAR(5)   COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `laserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacysm5game` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacysm5game` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacylaserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacylaserballgame` MODIFY COLUMN `winner` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacysm5gameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';
        ALTER TABLE `legacylaserballgameplayer` MODIFY COLUMN `team` VARCHAR(5) NOT NULL  COMMENT 'Fire Team: red\nEarth Team: green\nIce Team: blue';"""

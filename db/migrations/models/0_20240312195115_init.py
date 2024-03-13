from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `events` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time` INT NOT NULL,
    `type` VARCHAR(4) NOT NULL  COMMENT 'MISSION_START: 0100\nMISSION_END: 0101\nSHOT_EMPTY: 0200\nMISS: 0201\nMISS_BASE: 0202\nHIT_BASE: 0203\nDESTROY_BASE: 0204\nDAMAGED_OPPONENT: 0205\nDOWNED_OPPONENT: 0206\nDAMANGED_TEAM: 0207\nDOWNED_TEAM: 0208\nLOCKING: 0300\nMISSILE_BASE_MISS: 0301\nMISSILE_BASE_DAMAGE: 0302\nMISISLE_BASE_DESTROY: 0303\nMISSILE_MISS: 0304\nMISSILE_DAMAGE_OPPONENT: 0305\nMISSILE_DOWN_OPPONENT: 0306\nMISSILE_DAMAGE_TEAM: 0307\nMISSILE_DOWN_TEAM: 0308\nACTIVATE_RAPID_FIRE: 0400\nDEACTIVATE_RAPID_FIRE: 0401\nACTIVATE_NUKE: 0404\nDETONATE_NUKE: 0405\nRESUPPLY_AMMO: 0500\nRESUPPLY_LIVES: 0502\nAMMO_BOOST: 0510\nLIFE_BOOST: 0512\nPENALTY: 0600\nACHIEVEMENT: 0900\nREWARD: 0902\nBASE_AWARDED: 0B03\nPASS: 1100\nGOAL: 1101\nASSIST: 1102\nSTEAL: 1103\nBLOCK: 1104\nROUND_START: 1105\nROUND_END: 1106\nGETS_BALL: 1107\nTIME_VIOLATION: 1108\nCLEAR: 1109\nFAIL_CLEAR: 110A',
    `arguments` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `winner` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue',
    `winner_color` VARCHAR(20) NOT NULL,
    `tdf_name` VARCHAR(100) NOT NULL,
    `file_version` VARCHAR(20) NOT NULL,
    `software_version` VARCHAR(20) NOT NULL,
    `arena` VARCHAR(20) NOT NULL,
    `mission_type` INT NOT NULL,
    `mission_name` VARCHAR(100) NOT NULL,
    `ranked` BOOL NOT NULL,
    `ended_early` BOOL NOT NULL,
    `start_time` DATETIME(6) NOT NULL,
    `mission_duration` INT NOT NULL,
    `log_time` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `legacylaserballgame` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `winner` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue',
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `legacysm5game` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `winner` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue',
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `legacysm5gameplayer` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `player_dbid` INT NOT NULL,
    `game_dbid` INT NOT NULL,
    `team` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue',
    `role` VARCHAR(9) NOT NULL  COMMENT 'SCOUT: scout\nHEAVY: heavy\nCOMMANDER: commander\nMEDIC: medic\nAMMO: ammo',
    `score` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `player` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `player_id` VARCHAR(20) NOT NULL,
    `codename` VARCHAR(255) NOT NULL,
    `entity_id` VARCHAR(50) NOT NULL  DEFAULT '',
    `sm5_mu` DOUBLE NOT NULL  DEFAULT 25,
    `sm5_sigma` DOUBLE NOT NULL  DEFAULT 8.333,
    `laserball_mu` DOUBLE NOT NULL  DEFAULT 25,
    `laserball_sigma` DOUBLE NOT NULL  DEFAULT 8.333,
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `password` VARCHAR(255),
    `permissions` SMALLINT NOT NULL  COMMENT 'USER: 0\nADMIN: 1' DEFAULT 0
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `legacylaserballgameplayer` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `team` VARCHAR(5) NOT NULL  COMMENT 'RED: red\nGREEN: green\nBLUE: blue',
    `role` VARCHAR(9) NOT NULL  COMMENT 'SCOUT: scout\nHEAVY: heavy\nCOMMANDER: commander\nMEDIC: medic\nAMMO: ammo',
    `goals` INT NOT NULL,
    `assists` INT NOT NULL,
    `steals` INT NOT NULL,
    `clears` INT NOT NULL,
    `blocks` INT NOT NULL,
    `game_id` INT NOT NULL,
    `player_id` INT NOT NULL,
    CONSTRAINT `fk_legacyla_legacyla_2ee0db64` FOREIGN KEY (`game_id`) REFERENCES `legacylaserballgame` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_legacyla_player_0d354bf4` FOREIGN KEY (`player_id`) REFERENCES `player` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `winner` VARCHAR(5)   COMMENT 'RED: red\nGREEN: green\nBLUE: blue',
    `winner_color` VARCHAR(20) NOT NULL,
    `tdf_name` VARCHAR(100) NOT NULL,
    `file_version` VARCHAR(20) NOT NULL,
    `software_version` VARCHAR(20) NOT NULL,
    `arena` VARCHAR(20) NOT NULL,
    `mission_type` INT NOT NULL,
    `mission_name` VARCHAR(100) NOT NULL,
    `ranked` BOOL NOT NULL,
    `ended_early` BOOL NOT NULL,
    `start_time` DATETIME(6) NOT NULL,
    `mission_duration` INT NOT NULL,
    `log_time` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `teams` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `index` INT NOT NULL,
    `name` VARCHAR(50) NOT NULL,
    `color_enum` INT NOT NULL,
    `color_name` VARCHAR(50) NOT NULL,
    `real_color_name` VARCHAR(50) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `entitystarts` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time` INT NOT NULL,
    `entity_id` VARCHAR(50) NOT NULL,
    `type` VARCHAR(50) NOT NULL,
    `name` VARCHAR(75) NOT NULL,
    `level` INT NOT NULL,
    `role` SMALLINT NOT NULL  COMMENT 'OTHER: 0\nCOMMANDER: 1\nHEAVY: 2\nSCOUT: 3\nAMMO: 4\nMEDIC: 5',
    `battlesuit` VARCHAR(50) NOT NULL,
    `member_id` VARCHAR(50),
    `team_id` INT NOT NULL,
    CONSTRAINT `fk_entityst_teams_07c83741` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `entityends` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time` INT NOT NULL,
    `type` INT NOT NULL,
    `score` INT NOT NULL,
    `current_rating_mu` DOUBLE,
    `current_rating_sigma` DOUBLE,
    `previous_rating_mu` DOUBLE,
    `previous_rating_sigma` DOUBLE,
    `entity_id` INT NOT NULL,
    CONSTRAINT `fk_entityen_entityst_605165b1` FOREIGN KEY (`entity_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballstats` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `goals` INT NOT NULL,
    `assists` INT NOT NULL,
    `passes` INT NOT NULL,
    `steals` INT NOT NULL,
    `clears` INT NOT NULL,
    `blocks` INT NOT NULL,
    `shots_fired` INT NOT NULL,
    `shots_hit` INT NOT NULL,
    `started_with_ball` INT NOT NULL,
    `times_stolen` INT NOT NULL,
    `times_blocked` INT NOT NULL,
    `passes_received` INT NOT NULL,
    `entity_id` INT NOT NULL,
    CONSTRAINT `fk_laserbal_entityst_69c251be` FOREIGN KEY (`entity_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `playerstates` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time` INT NOT NULL,
    `state` SMALLINT NOT NULL  COMMENT 'ACTIVE: 0\nUNKNOWN: 1\nRESETTABLE: 2\nDOWN: 3',
    `entity_id` INT NOT NULL,
    CONSTRAINT `fk_playerst_entityst_ef31635a` FOREIGN KEY (`entity_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5stats` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `shots_hit` INT NOT NULL,
    `shots_fired` INT NOT NULL,
    `times_zapped` INT NOT NULL,
    `times_missiled` INT NOT NULL,
    `missile_hits` INT NOT NULL,
    `nukes_detonated` INT NOT NULL,
    `nukes_activated` INT NOT NULL,
    `nuke_cancels` INT NOT NULL,
    `medic_hits` INT NOT NULL,
    `own_medic_hits` INT NOT NULL,
    `medic_nukes` INT NOT NULL,
    `scout_rapid_fires` INT NOT NULL,
    `life_boosts` INT NOT NULL,
    `ammo_boosts` INT NOT NULL,
    `lives_left` INT NOT NULL,
    `shots_left` INT NOT NULL,
    `penalties` INT NOT NULL,
    `shot_3_hits` INT NOT NULL,
    `own_nuke_cancels` INT NOT NULL,
    `shot_opponent` INT NOT NULL,
    `shot_team` INT NOT NULL,
    `missiled_opponent` INT NOT NULL,
    `missiled_team` INT NOT NULL,
    `entity_id` INT NOT NULL,
    CONSTRAINT `fk_sm5stats_entityst_c439695d` FOREIGN KEY (`entity_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `scores` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time` INT NOT NULL,
    `old` INT NOT NULL,
    `delta` INT NOT NULL,
    `new` INT NOT NULL,
    `entity_id` INT NOT NULL,
    CONSTRAINT `fk_scores_entityst_d97eb839` FOREIGN KEY (`entity_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_entitystarts` (
    `laserballgame_id` INT NOT NULL,
    `entitystarts_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`entitystarts_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_events` (
    `laserballgame_id` INT NOT NULL,
    `events_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`events_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_playerstates` (
    `laserballgame_id` INT NOT NULL,
    `playerstates_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`playerstates_id`) REFERENCES `playerstates` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_entityends` (
    `laserballgame_id` INT NOT NULL,
    `entityends_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`entityends_id`) REFERENCES `entityends` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_scores` (
    `laserballgame_id` INT NOT NULL,
    `scores_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`scores_id`) REFERENCES `scores` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_laserballstats` (
    `laserballgame_id` INT NOT NULL,
    `laserballstats_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`laserballstats_id`) REFERENCES `laserballstats` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `laserballgame_teams` (
    `laserballgame_id` INT NOT NULL,
    `teams_id` INT NOT NULL,
    FOREIGN KEY (`laserballgame_id`) REFERENCES `laserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`teams_id`) REFERENCES `teams` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `legacylaserballgame_legacylaserballgameplayer` (
    `legacylaserballgame_id` INT NOT NULL,
    `legacylaserballgameplayer_id` INT NOT NULL,
    FOREIGN KEY (`legacylaserballgame_id`) REFERENCES `legacylaserballgame` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`legacylaserballgameplayer_id`) REFERENCES `legacylaserballgameplayer` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `legacysm5game_legacysm5gameplayer` (
    `legacysm5game_id` INT NOT NULL,
    `legacysm5gameplayer_id` INT NOT NULL,
    FOREIGN KEY (`legacysm5game_id`) REFERENCES `legacysm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`legacysm5gameplayer_id`) REFERENCES `legacysm5gameplayer` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_entitystarts` (
    `sm5game_id` INT NOT NULL,
    `entitystarts_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`entitystarts_id`) REFERENCES `entitystarts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_events` (
    `sm5game_id` INT NOT NULL,
    `events_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`events_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_sm5stats` (
    `sm5game_id` INT NOT NULL,
    `sm5stats_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`sm5stats_id`) REFERENCES `sm5stats` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_playerstates` (
    `sm5game_id` INT NOT NULL,
    `playerstates_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`playerstates_id`) REFERENCES `playerstates` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_entityends` (
    `sm5game_id` INT NOT NULL,
    `entityends_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`entityends_id`) REFERENCES `entityends` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_scores` (
    `sm5game_id` INT NOT NULL,
    `scores_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`scores_id`) REFERENCES `scores` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sm5game_teams` (
    `sm5game_id` INT NOT NULL,
    `teams_id` INT NOT NULL,
    FOREIGN KEY (`sm5game_id`) REFERENCES `sm5game` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`teams_id`) REFERENCES `teams` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """

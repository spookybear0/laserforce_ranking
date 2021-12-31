-- phpMyAdmin SQL Dump
-- version 4.6.6deb5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Apr 10, 2021 at 02:26 PM
-- Server version: 5.7.28-0ubuntu0.18.04.4
-- PHP Version: 7.1.33-9+ubuntu18.04.1+deb.sury.org+1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `laserforce`
--

-- --------------------------------------------------------

--
-- Table structure for table `sm5_games`
--

CREATE TABLE `sm5_games` (
  `id` int(11) NOT NULL,
  `date_played` int(11) NOT NULL,
  `winner` varchar(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `laserball_games`
--

CREATE TABLE `laserball_games` (
  `id` int(11) NOT NULL,
  `date_played` int(11) NOT NULL,
  `winner` varchar(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `sm5_game_players`
--

CREATE TABLE `sm5_game_players` (
  `player_id` varchar(32) NOT NULL,
  `game_id` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `team` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `role` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `score` int(11) NOT NULL

) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `laserball_game_players`
--

CREATE TABLE `laserball_game_players` (
  `player_id` varchar(32) NOT NULL,
  `game_id` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `team` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `goals` int(11) NOT NULL,
  `assists` int(11) NOT NULL,
  `steals` int(11) NOT NULL,
  `clears` int(11) NOT NULL,
  `passes` int(11) NOT NULL,
  `blocks` int(11) NOT NULL

) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `players`
--

CREATE TABLE `players` (
  `id` int(11) NOT NULL,
  `player_id` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `ipl_id` varchar(16) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `codename` varchar(32) NOT NULL UNIQUE COLLATE utf8mb4_0900_ai_ci,
  `elo` int(11) DEFAULT 1200,
  `rank` varchar(32) NOT NULL COLLATE utf8mb4_0900_ai_ci,
  `ranking_scout` float(11) NOT NULL,
  `ranking_heavy` float(11) NOT NULL,
  `ranking_commander` float(11) NOT NULL,
  `ranking_medic` float(11) NOT NULL,
  `ranking_ammo` float(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `games`
--
ALTER TABLE `sm5_games`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `laserball_games`
--
ALTER TABLE `laserball_games`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `game_players`
--
ALTER TABLE `sm5_game_players`
  ADD PRIMARY KEY (`player_id`);

--
-- Indexes for table `laserball_game_players`
--
ALTER TABLE `laserball_game_players`
  ADD PRIMARY KEY (`player_id`);

--
-- Indexes for table `players`
--
ALTER TABLE `players`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `sm5_games`
--
ALTER TABLE `sm5_games`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `laserball_games`
--
ALTER TABLE `laserball_games`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `players`
--
ALTER TABLE `players`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

import os
import sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.chdir("..")
sys.path.append(os.getcwd())
import openskill.models
import pytest
from tortoise import Tortoise
from tortoise.expressions import F
from config import config as config_obj
import asyncio
from helpers import statshelper, ratinghelper, tdfhelper
from sanic import log
import logging
from db.sm5 import SM5Game
from db.player import Player
import openskill
import matplotlib.pyplot as plt
import numpy as np
from db.sm5 import Team
import csv

TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://tools/compare_prediction_accuracy_db.sqlite3"
    },
    "apps": {
        "models": {
            "models": ["db.game", "db.laserball", "db.legacy", "db.player", "db.sm5", "db.tag", "aerich.models"],
            "default_connection": "default"
        }
    }
}

async def plot_margin_calibration():
    predicted_margin_game = []
    predicted_margin_encounter = []
    actual_margin = []

    games = await SM5Game.filter(ranked=True).all()

    encounter_data = csv.DictReader(open("sm5_win_chances_encounter.csv", "r"))
    encounter_dict = {}
    for row in encounter_data:
        encounter_dict[int(row["game_id"])] = row
    
    game_data = csv.DictReader(open("sm5_win_chances_game.csv", "r"))
    game_dict = {}
    for row in game_data:
        game_dict[int(row["game_id"])] = row


    for game in games:
        # predictions

        # game-level
        p_red_game = float(game_dict[game.id]["p_red"])
        # encounter-level
        p_red_encounter = float(encounter_dict[game.id]["p_red"])

        # scores
        red_score = await game.get_team_score(Team.RED)
        green_score = await game.get_team_score(Team.GREEN)

        if red_score + green_score == 0:
            continue

        # margins
        actual = (red_score - green_score) / (red_score + green_score)
        pred_game = 2 * p_red_game - 1
        pred_encounter = 2 * p_red_encounter - 1

        actual_margin.append(actual)
        predicted_margin_game.append(pred_game)
        predicted_margin_encounter.append(pred_encounter)

    # numpy arrays
    actual_margin = np.array(actual_margin)
    predicted_margin_game = np.array(predicted_margin_game)
    predicted_margin_encounter = np.array(predicted_margin_encounter)

    # plot

    plt.figure(figsize=(7, 7))

    plt.scatter(
        predicted_margin_game,
        actual_margin,
        alpha=0.35,
        label="Game-level",
        s=15
    )

    plt.scatter(
        predicted_margin_encounter,
        actual_margin,
        alpha=0.35,
        label="Encounter-level",
        s=15
    )

    # ideal line
    x = np.linspace(-1, 1, 200)
    plt.plot(x, x, linestyle="--", linewidth=2, label="Perfect calibration")

    plt.xlabel("Predicted margin (2p − 1)")
    plt.ylabel("Actual margin")
    plt.title("Predicted vs Actual Game Margins")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis("equal")

    plt.tight_layout()
    plt.savefig("sm5_margin_calibration.png", dpi=300)
    plt.show()

async def save_win_chance_to_csv():
    data = []

    for game in await SM5Game.filter(ranked=True).order_by("start_time"):
        p_red, p_green = await game.get_win_chance_before_game()
        data.append((game.id, p_red, p_green))

    with open("sm5_win_chances.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["game_id", "p_red", "p_green"])
        writer.writerows(data)
    

async def main():
    await Tortoise.init(
        config=TORTOISE_ORM
    )
   

    await Tortoise.generate_schemas()
    myLogger = logging.getLogger(__name__)
    myLogger.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO)

    log.logger = myLogger

    tdfhelper.logger = myLogger

    # set params

    ratinghelper.MU = 25
    ratinghelper.SIGMA = 25 / 3
    ratinghelper.BETA = 25 / 6
    ratinghelper.KAPPA = 0.0001
    ratinghelper.TAU = 25 / 275  # default: 25/300 (for rating volatility, higher = more volatile ratings)
    ratinghelper.ZETA = 0.09  # default: 0 (custom addition for uneven team rating adjustment), higher value = more adjustment for uneven teams

    # mu is for skill, sigma is for uncertainty/confidence
    # the higher the mu, the better the player is expected to perform
    # the higher the sigma, the less confident we are in the player's skill

    # sm5

    # TODO: possibly seperate damaged and downed events, but for now they are treated the same

    # overall weight for an entire game (mu_weight, sigma_weight) = (1, 1) ( rate([team1, team2]) )


    ratinghelper.SM5_HIT_WEIGHT_MU = 0.01  # skill weight for hits in sm5
    ratinghelper.SM5_HIT_WEIGHT_SIGMA = 0.01  # uncertainty weight for hits in sm5

    ratinghelper.SM5_HIT_MEDIC_WEIGHT_MU = 0.02  # skill weight for medic hits in sm5
    ratinghelper.SM5_HIT_MEDIC_WEIGHT_SIGMA = 0.01  # uncertainty weight for medic hits in sm5


    ratinghelper.SM5_MISSILE_WEIGHT_MU = 0.025  # skill weight for missile hits in sm5
    ratinghelper.SM5_MISSILE_WEIGHT_SIGMA = 0.01  # uncertainty weight for missile hits in sm5

    ratinghelper.SM5_MISSILE_MEDIC_WEIGHT_MU = 0.05  # skill weight for medic missiles in sm5
    ratinghelper.SM5_MISSILE_MEDIC_WEIGHT_SIGMA = 0.01  # uncertainty weight for medic missiles in sm5

    #ratinghelper.model = ratinghelper.CustomPlackettLuce(ratinghelper.MU, ratinghelper.SIGMA, ratinghelper.BETA, ratinghelper.KAPPA, tau=ratinghelper.TAU)

    # exclude uneven player count games

    games = await SM5Game.filter(ranked=True).all()
    for game in games:
        if game.team1_size != game.team2_size:
            game.ranked = False
            await game.save()
            print(f"Unranking game {game.id} due to uneven player count")

    print(f"Number of ranked games: {await SM5Game.filter(ranked=True).count()}")

    n = 999999

    # recalculate sm5 ratings

    await ratinghelper.recalculate_sm5_ratings(_sample_size=n)

    # print prediction accuracy

    accuracy = await statshelper.get_predictive_accuracy(_sample_size=n)
    brier = await statshelper.get_brier_score(_sample_size=n)
    msme = await statshelper.get_margin_prediction_error(_sample_size=n)

    print(f"Predictive accuracy: {accuracy*100:.2f}%")
    print(f"Brier score: {brier:.4f}")
    print(f"Mean squared margin error: {msme:.2f}")

    # top 25 players
    players = await Player.all().annotate(sm5_ord=F("sm5_mu") - 3 * F("sm5_sigma")).order_by("-sm5_ord").limit(25)

    for p in players:
        print(f"{p.codename} - {p.sm5_ordinal:.2f} (sigma: {p.sm5_sigma:.2f})")

    await save_win_chance_to_csv()
   
    await plot_margin_calibration()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(Tortoise.close_connections())
from script import setup_environment
setup_environment()
import asyncclick as click

from laserforce_ranking.rating import recalculate_rankings
import time

@click.command()
@click.option("--start-game-id", type=int, default=None, help="The game ID to start recalculation from.")
async def recalculate_ratings_command(start_game_id: int = None):
    """
    Command to recalculate ratings after mass parsing TDFs.
    """

    click.echo("Starting recalculation of ratings...")
    start_time = time.time()
    await recalculate_rankings(start_game_id=start_game_id)
    click.echo("Recalculation of ratings completed in {:.2f} seconds.".format(time.time() - start_time))



if __name__ == "__main__":
    recalculate_ratings_command(_anyio_backend="asyncio")
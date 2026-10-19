from script import setup_environment
setup_environment()
import asyncclick as click

from laserforce_ranking.rating import recalculate_rankings


@click.command()
async def recalculate_ratings_command():
    """
    Command to recalculate ratings after mass parsing TDFs.
    """

    click.echo("Starting recalculation of ratings...")
    await recalculate_rankings()
    click.echo("Recalculation of ratings completed.")



if __name__ == "__main__":
    recalculate_ratings_command(_anyio_backend="asyncio")
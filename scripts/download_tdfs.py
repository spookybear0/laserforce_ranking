from script import setup_environment
setup_environment()
import asyncclick as click

from laserforce_ranking.tdf import download_tdfs


@click.command()
@click.option('--site-id', default=None, help='Site ID to download TDFs for (e.g., "4-19")')
@click.option('--game-type', default=None, help='Game type to download TDFs for (e.g., "sm5")')
async def download_tdfs_command(site_id, game_type):
    """
    Command to download TDFs for a specific site and/or game type.
    """
    click.echo(f"Downloading TDFs for site_id: {site_id}, game_type: {game_type}")
    await download_tdfs(site_id=site_id, game_type=game_type)
    click.echo("Download completed.")

if __name__ == "__main__":
    download_tdfs_command(_anyio_backend="asyncio")
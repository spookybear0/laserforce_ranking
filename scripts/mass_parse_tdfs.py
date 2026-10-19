from script import setup_environment
setup_environment()
import asyncclick as click

from laserforce_ranking.tdf import mass_parse_tdfs


@click.command()
@click.option('--skip_rankings', is_flag=True, default=True, help='Skip ranking after parsing TDFs')
async def mass_parse_tdfs_command(skip_rankings: bool = True):
    """
    Command to mass parse TDFs.
    """
    click.echo("Starting mass parsing of TDFs...")
    await mass_parse_tdfs(skip_rankings=skip_rankings)
    click.echo("Mass parsing completed.")

if __name__ == "__main__":
    mass_parse_tdfs_command(_anyio_backend="asyncio")
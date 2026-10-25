from script import setup_environment
setup_environment()
import click
from laserforce_ranking.models import Player, SM5Game, EntityStart
import time

@click.command()
def update_codenames_command():
    # makes sure all player's codenames are the most recent
    click.echo("Starting update of player codenames...")
    start_time = time.time()

    for player in Player.objects.all():
        # Get the most recent game for the player
        entity = EntityStart.objects.filter(entity_id=player.entity_id).order_by("-game__start_time").first()

        if entity and entity.name != player.codename:
            # Update the player's codename to the most recent one
            # also manage previous codenames
            player.previous_codenames.append(player.codename)
            player.codename = entity.name
            if entity.name in player.previous_codenames:
                player.previous_codenames.remove(entity.name)
            player.save()
            click.echo(f"Updated codename for player {player.id} to {player.codename}")


if __name__ == "__main__":
    update_codenames_command()
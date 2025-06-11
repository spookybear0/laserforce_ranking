import unittest

from db.sm5 import SM5Game
from db.types import Team, IntRole, EventType
from helpers.sm5helper import get_sm5_last_team_standing, get_sm5_notable_events
from helpers.statshelper import NotableEvent
from helpers.tdfhelper import create_event
from tests.helpers.environment import setup_test_database, ENTITY_ID_1, ENTITY_ID_2, get_sm5_game_id, \
    teardown_test_database, add_entity, get_red_team, get_green_team, add_sm5_stats, ENTITY_ID_3, add_sm5_event


class TestSm5Helper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_get_sm5_last_team_standing_both_alive(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        entity_start, entity_end = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team())
        await add_sm5_stats(entity_start, lives_left=10)

        entity_start2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_green_team())
        await add_sm5_stats(entity_start2, lives_left=15)

        await game.entity_starts.add(entity_start, entity_start2)
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        winning_team = await get_sm5_last_team_standing(game)

        self.assertEqual(None, winning_team)

    async def test_get_sm5_last_team_standing_only_red_alive(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()
        entity_start, entity_end = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team())
        await add_sm5_stats(entity_start, lives_left=10)

        entity_start2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_green_team())
        await add_sm5_stats(entity_start2, lives_left=0)

        await game.entity_starts.add(entity_start, entity_start2)
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        winning_team = await get_sm5_last_team_standing(game)

        self.assertEqual(Team.RED, winning_team)

    async def test_get_sm5_notable_events(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        # Player 1 dies after 200 seconds.
        entity_start, entity_end = await add_entity(entity_id=ENTITY_ID_1, team=get_red_team(),
                                                    role=IntRole.AMMO,
                                                    name="AmmoBoi",
                                                    end_time_millis=200000)
        await add_sm5_stats(entity_start, lives_left=0)

        # Player 2 lives.
        entity_start2, entity_end2 = await add_entity(entity_id=ENTITY_ID_2, team=get_green_team())
        await add_sm5_stats(entity_start2, lives_left=15)

        # Player 4 dies after 100 seconds.
        entity_start3, entity_end3 = await add_entity(entity_id=ENTITY_ID_3, team=get_green_team(),
                                                      role=IntRole.MEDIC,
                                                      name="Dr. Medic",
                                                      end_time_millis=100000)
        await add_sm5_stats(entity_start3, lives_left=0)

        await game.entity_starts.add(entity_start, entity_start2, entity_start3)
        await game.entity_ends.add(entity_end, entity_end2, entity_end3)

        # Player 2 tries to nuke at 150 seconds and succeeds.
        # Some stuff happens in the meantime.
        await add_sm5_event(await create_event(time_ms=150000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_2
                                               ))

        await add_sm5_event(await create_event(time_ms=152000, type=EventType.DOWNED_TEAM,
                                               entity1=ENTITY_ID_2,
                                               entity2=ENTITY_ID_1,
                                               ))

        await add_sm5_event(await create_event(time_ms=153000, type=EventType.DETONATE_NUKE,
                                               entity1=ENTITY_ID_2
                                               ))

        # Player 3 tries to nuke at 400 seconds and gets downed by an enemy, player 2.
        await add_sm5_event(await create_event(time_ms=400000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_3
                                               ))

        # Ireelevant.
        await add_sm5_event(await create_event(time_ms=401000, type=EventType.DOWNED_TEAM,
                                               entity1=ENTITY_ID_3,
                                               entity2=ENTITY_ID_2,
                                               ))

        # Note we're pretending that Laserforce is wrong about TEAM vs OPPONENT.
        await add_sm5_event(await create_event(time_ms=402000, type=EventType.DOWNED_TEAM,
                                               entity1=ENTITY_ID_1,
                                               entity2=ENTITY_ID_3,
                                               ))

        # Player 2 tries to nuke at 500 seconds and gets FRIENDLY MISSILED by player 3.
        await add_sm5_event(await create_event(time_ms=500000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_2
                                               ))

        await add_sm5_event(await create_event(time_ms=506000, type=EventType.MISSILE_DOWN_OPPONENT,
                                               entity1=ENTITY_ID_3,
                                               entity2=ENTITY_ID_2,
                                               ))

        # Player 3 tries to nuke at 600 seconds and gets RUINED by their own resup.
        await add_sm5_event(await create_event(time_ms=600000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_3
                                               ))

        await add_sm5_event(await create_event(time_ms=606000, type=EventType.RESUPPLY_AMMO,
                                               entity1=ENTITY_ID_2,
                                               entity2=ENTITY_ID_3,
                                               ))

        # Player 1 tries to nuke and gets their nuke canceled by player 2 with another nuke.
        # Player 2 nukes first.
        await add_sm5_event(await create_event(time_ms=700000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_2
                                               ))

        await add_sm5_event(await create_event(time_ms=701000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_1
                                               ))

        await add_sm5_event(await create_event(time_ms=705000, type=EventType.DETONATE_NUKE,
                                               entity1=ENTITY_ID_2,
                                               ))

        # Player 1 tries to nuke and gets their nuke canceled by player 2 with another nuke.
        # Player 2 nukes after player 1 and still wins.
        await add_sm5_event(await create_event(time_ms=800000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_1
                                               ))

        await add_sm5_event(await create_event(time_ms=801000, type=EventType.ACTIVATE_NUKE,
                                               entity1=ENTITY_ID_2
                                               ))

        await add_sm5_event(await create_event(time_ms=805000, type=EventType.DETONATE_NUKE,
                                               entity1=ENTITY_ID_2,
                                               ))

        notable_events = await get_sm5_notable_events(game)

        # All events, in chronological order.
        # The base test game setup includes an ACTIVATE_NUKE event at 150 seconds for no good reason,
        # hence the event in the result.
        self.assertEqual([NotableEvent(seconds=100,
                                       event='Dr. Medic (Earth Medic) is eliminated',
                                       short_event=['Dr. Medic', 'eliminated'],
                                       team=Team.GREEN,
                                       id='event2',
                                       position='90%'),
                          NotableEvent(seconds=150,
                                       event='Some Player got their nuke canceled (NO IDEA HOW)',
                                       short_event=['Some Player', 'nuke canceled'],
                                       team=Team.GREEN,
                                       id='event3',
                                       position='80%'),
                          NotableEvent(seconds=153,
                                       event='Some Player detonates a nuke',
                                       short_event=['Some Player', 'nukes'],
                                       team=Team.GREEN,
                                       id='event4',
                                       position='70%'),
                          NotableEvent(seconds=200,
                                       event='AmmoBoi (Fire Ammo) is eliminated',
                                       short_event=['AmmoBoi', 'eliminated'],
                                       team=Team.RED,
                                       id='event1',
                                       position='60%'),
                          NotableEvent(seconds=402,
                                       event='Dr. Medic had their nuke canceled by AmmoBoi',
                                       short_event=['Dr. Medic', 'nuke canceled'],
                                       team=Team.GREEN,
                                       id='event5',
                                       position='50%'),
                          NotableEvent(seconds=506,
                                       event='Some Player had their nuke canceled by FRIENDLY FIRE (Dr. '
                                             'Medic)',
                                       short_event=['Some Player', 'friendly nuke cancel'],
                                       team=Team.GREEN,
                                       id='event6',
                                       position='40%'),
                          NotableEvent(seconds=606,
                                       event='Dr. Medic had their nuke canceled by THEIR OWN RESUP '
                                             '(Some Player)',
                                       short_event=['Dr. Medic', 'nuke canceled by RESUP'],
                                       team=Team.GREEN,
                                       id='event7',
                                       position='30%'),
                          NotableEvent(seconds=701,
                                       event="AmmoBoi had their nuke canceled by Some Player's nuke - "
                                             'they nuked first',
                                       short_event=['AmmoBoi', 'nuke canceled by nuke'],
                                       team=Team.RED,
                                       id='event9',
                                       position='20%'),
                          NotableEvent(seconds=705,
                                       event='Some Player detonates a nuke',
                                       short_event=['Some Player', 'nukes'],
                                       team=Team.GREEN,
                                       id='event8',
                                       position='10%'),
                          NotableEvent(seconds=800,
                                       event="AmmoBoi had their nuke canceled by Some Player's nuke - "
                                             'and they nuked later',
                                       short_event=['AmmoBoi', 'nuke canceled by nuke'],
                                       team=Team.RED,
                                       id='event10',
                                       position='90%'),
                          NotableEvent(seconds=805,
                                       event='Some Player detonates a nuke',
                                       short_event=['Some Player', 'nukes'],
                                       team=Team.GREEN,
                                       id='event11',
                                       position='80%')], notable_events)

        if __name__ == '__main__':
            unittest.main()

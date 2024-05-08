import unittest

from db.sm5 import SM5Game
from db.types import IntRole
from helpers.replay_sm5 import create_sm5_replay
from tests.helpers.environment import setup_test_database, get_sm5_game_id, \
    teardown_test_database, add_entity, get_red_team, get_green_team, create_zap_event, create_resupply_lives_event


class TestReplay(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database(basic_events=False)

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_create_sm5_replay(self):
        game = await SM5Game.filter(id=get_sm5_game_id()).first()

        entity1, entity_end1 = await add_entity(entity_id="@NotLoggedIn", name="Indy", team=get_red_team(),
                                                role=IntRole.COMMANDER, type="player", sm5_game=game)
        entity2, entity_end2 = await add_entity(entity_id="@NotMember", name="Miles", team=get_green_team(),
                                                role=IntRole.SCOUT, type="player", sm5_game=game)
        entity3, entity_end3 = await add_entity(entity_id="LoggedIn", name="Bumblebee", team=get_red_team(),
                                                role=IntRole.MEDIC, type="player", sm5_game=game)

        await game.events.add(await create_zap_event(2000, entity1.entity_id, entity2.entity_id))
        await game.events.add(await create_resupply_lives_event(2500, entity3.entity_id, entity1.entity_id))

        replay = await create_sm5_replay(game)

        js_replay = replay.export_to_js()

        expected = """
        """

        # self.assertEqual(expected, js_replay)


if __name__ == '__main__':
    unittest.main()

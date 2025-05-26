import datetime
import unittest

import pytz

from db.sm5 import SM5Game
from db.types import IntRole
from helpers.replay import Replay, ReplayTeam, ReplayPlayer, ReplayEvent, ReplayCellChange, ReplaySound, ReplayRowChange
from helpers.replay_sm5 import create_sm5_replay
from tests.helpers.environment import SM5_GAME_1_START_TIME, setup_test_database, get_sm5_game_id, \
    teardown_test_database, add_entity, get_red_team, get_green_team, create_zap_event, create_resupply_lives_event


class TestReplaySm5(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database(basic_events=False)

        self.game = await SM5Game.filter(id=get_sm5_game_id()).first()

        self.entity1, self.entity_end1 = await add_entity(entity_id="@NotLoggedIn", name="Indy", team=get_red_team(),
                                                          role=IntRole.COMMANDER, type="player", sm5_game=self.game)
        self.entity2, self.entity_end2 = await add_entity(entity_id="@NotMember", name="Miles", team=get_green_team(),
                                                          role=IntRole.SCOUT, type="player", sm5_game=self.game)
        self.entity3, self.entity_end3 = await add_entity(entity_id="LoggedIn", name="Bumblebee", team=get_red_team(),
                                                          role=IntRole.MEDIC, type="player", sm5_game=self.game)

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_create_sm5_replay(self):
        await self.game.events.add(await create_zap_event(2000, self.entity1.entity_id, self.entity2.entity_id))
        await self.game.events.add(
            await create_resupply_lives_event(2500, self.entity3.entity_id, self.entity1.entity_id))

        replay = await create_sm5_replay(self.game)

        expected = Replay(events=[ReplayEvent(timestamp_millis=2000, message='Indy zaps Miles', team_scores=[100, -20],
                                              cell_changes=[ReplayCellChange(row_id='r1', column=4, new_value='29'),
                                                            ReplayCellChange(row_id='r1', column=7,
                                                                             new_value='100.00%'),
                                                            ReplayCellChange(row_id='r3', column=3, new_value='14'),
                                                            ReplayCellChange(row_id='r1', column=6, new_value='1'),
                                                            ReplayCellChange(row_id='r1', column=2, new_value='100'),
                                                            ReplayCellChange(row_id='r3', column=2, new_value='-20'),
                                                            ReplayCellChange(row_id='r1', column=8, new_value=''),
                                                            ReplayCellChange(row_id='r3', column=8, new_value='0.00')],
                                              row_changes=[
                                                  ReplayRowChange(row_id='r3', new_css_class='earth-team-down')],
                                              sounds=[ReplaySound(asset_urls=['/assets/sm5/audio/Effect/Scream.0.wav',
                                                                              '/assets/sm5/audio/Effect/Scream.1.wav',
                                                                              '/assets/sm5/audio/Effect/Scream.2.wav',
                                                                              '/assets/sm5/audio/Effect/Shot.0.wav',
                                                                              '/assets/sm5/audio/Effect/Shot.1.wav'],
                                                                  id=3, priority=0, required=False)],
                                              sound_stereo_balance=0.5),
                                  ReplayEvent(timestamp_millis=2500, message='LoggedIn resupplies Indy', team_scores=[],
                                              cell_changes=[ReplayCellChange(row_id='r1', column=3, new_value='19')],
                                              row_changes=[
                                                  ReplayRowChange(row_id='r1', new_css_class='fire-team-down')],
                                              sounds=[ReplaySound(asset_urls=['/assets/sm5/audio/Effect/Resupply.0.wav',
                                                                              '/assets/sm5/audio/Effect/Resupply.1.wav',
                                                                              '/assets/sm5/audio/Effect/Resupply.2.wav',
                                                                              '/assets/sm5/audio/Effect/Resupply.3.wav',
                                                                              '/assets/sm5/audio/Effect/Resupply.4.wav'],
                                                                  id=2, priority=0, required=False)],
                                              sound_stereo_balance=-0.5)], teams=[
            ReplayTeam(name='Fire Team', css_class='fire-team', id='fire_team', players=[ReplayPlayer(
                cells=['<img src="/assets/sm5/roles/commander.png" alt="Commander" width="30" height="30">', 'Indy',
                       '0', '15', '0', '5', '0', '', ''], row_id='r1', css_class='fire-team'), ReplayPlayer(
                cells=['<img src="/assets/sm5/roles/medic.png" alt="Medic" width="30" height="30">', 'Bumblebee', '0',
                       '20', '0', '0', '0', '', ''], row_id='r2', css_class='fire-team')]),
            ReplayTeam(name='Earth Team', css_class='earth-team', id='earth_team', players=[ReplayPlayer(
                cells=['<img src="/assets/sm5/roles/scout.png" alt="Scout" width="30" height="30">', 'Miles', '0', '15',
                       '0', '0', '0', '', ''], row_id='r3', css_class='earth-team')])], sounds=[ReplaySound(
            asset_urls=['/assets/sm5/audio/Start.0.wav', '/assets/sm5/audio/Start.1.wav',
                        '/assets/sm5/audio/Start.2.wav', '/assets/sm5/audio/Start.3.wav'], id=0, priority=2,
            required=True), ReplaySound(asset_urls=['/assets/sm5/audio/Effect/General Quarters.wav'], id=1, priority=1,
                                        required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Effect/Resupply.0.wav', '/assets/sm5/audio/Effect/Resupply.1.wav',
                        '/assets/sm5/audio/Effect/Resupply.2.wav', '/assets/sm5/audio/Effect/Resupply.3.wav',
                        '/assets/sm5/audio/Effect/Resupply.4.wav'], id=2, priority=0, required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Effect/Scream.0.wav', '/assets/sm5/audio/Effect/Scream.1.wav',
                        '/assets/sm5/audio/Effect/Scream.2.wav', '/assets/sm5/audio/Effect/Shot.0.wav',
                        '/assets/sm5/audio/Effect/Shot.1.wav'], id=3, priority=0, required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Effect/Boom.wav'], id=4, priority=0, required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Rapid Fire.0.wav', '/assets/sm5/audio/Rapid Fire.1.wav',
                        '/assets/sm5/audio/Rapid Fire.2.wav', '/assets/sm5/audio/Rapid Fire.3.wav'], id=5, priority=0,
            required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Missile.0.wav', '/assets/sm5/audio/Missile.1.wav',
                        '/assets/sm5/audio/Missile.2.wav'], id=6, priority=0, required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Zap Own.0.wav', '/assets/sm5/audio/Zap Own.1.wav',
                        '/assets/sm5/audio/Zap Own.2.wav', '/assets/sm5/audio/Zap Own.3.wav'], id=7, priority=0,
            required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Nuke.0.wav', '/assets/sm5/audio/Nuke.1.wav', '/assets/sm5/audio/Nuke.2.wav'],
            id=8, priority=0, required=False), ReplaySound(asset_urls=['/assets/sm5/audio/Elimination.wav'], id=9,
                                                           priority=0, required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Boost.0.wav', '/assets/sm5/audio/Boost.1.wav',
                        '/assets/sm5/audio/Boost.2.wav'], id=10, priority=0, required=False), ReplaySound(
            asset_urls=['/assets/sm5/audio/Do It.wav'], id=11, priority=0, required=False)], intro_sound=ReplaySound(
            asset_urls=['/assets/sm5/audio/Start.0.wav', '/assets/sm5/audio/Start.1.wav',
                        '/assets/sm5/audio/Start.2.wav', '/assets/sm5/audio/Start.3.wav'], id=0, priority=2,
            required=True), start_sound=ReplaySound(asset_urls=['/assets/sm5/audio/Effect/General Quarters.wav'], id=1,
                                                    priority=1, required=False),
                          column_headers=['Role', 'Codename', 'Score', 'Lives', 'Shots', 'Missiles', 'Spec', 'Accuracy',
                                          'K/D'], sort_columns_index=[2],
                          game_start_real_world_timestamp=SM5_GAME_1_START_TIME)

        self.assertEqual(expected, replay)

    async def test_zap_and_down_opponent(self):
        await self.game.events.add(await create_zap_event(2000, self.entity1.entity_id, self.entity2.entity_id))

        replay = await create_sm5_replay(self.game)

        # Commander tagging scout. Scout will go down.
        expected_events = [ReplayEvent(timestamp_millis=2000, message='Indy zaps Miles', team_scores=[100, -20],
                                       cell_changes=[ReplayCellChange(row_id='r1', column=4, new_value='29'),
                                                     # 29 shots
                                                     ReplayCellChange(row_id='r1', column=7,
                                                                      new_value='100.00%'),  # 100% accuracy
                                                     ReplayCellChange(row_id='r3', column=3, new_value='14'),
                                                     # 14 lives
                                                     ReplayCellChange(row_id='r1', column=6, new_value='1'),  # 1 spec
                                                     ReplayCellChange(row_id='r1', column=2, new_value='100'),
                                                     # 100 pts
                                                     ReplayCellChange(row_id='r3', column=2, new_value='-20'),
                                                     # -20 pts
                                                     ReplayCellChange(row_id='r1', column=8, new_value=''),  # K/D
                                                     ReplayCellChange(row_id='r3', column=8, new_value='0.00')],  # K/D
                                       row_changes=[
                                           ReplayRowChange(row_id='r3', new_css_class='earth-team-down')],
                                       # player down
                                       sounds=[ReplaySound(asset_urls=['/assets/sm5/audio/Effect/Scream.0.wav',
                                                                       '/assets/sm5/audio/Effect/Scream.1.wav',
                                                                       '/assets/sm5/audio/Effect/Scream.2.wav',
                                                                       '/assets/sm5/audio/Effect/Shot.0.wav',
                                                                       '/assets/sm5/audio/Effect/Shot.1.wav'],
                                                           id=3, priority=0, required=False)],
                                       sound_stereo_balance=0.5)]

        self.assertEqual(expected_events, replay.events)

    async def test_downed_player_comes_back_up(self):
        await self.game.events.add(await create_zap_event(2000, self.entity1.entity_id, self.entity2.entity_id))
        await self.game.events.add(await create_zap_event(20000, self.entity1.entity_id, self.entity2.entity_id))

        replay = await create_sm5_replay(self.game)

        # Commander tagging scout. Scout will go down. Scout will come back up 8 seconds later (10.000ms in).
        up_event = ReplayEvent(timestamp_millis=10000, message='', team_scores=[],
                               cell_changes=[],
                               row_changes=[
                                   ReplayRowChange(row_id='r3', new_css_class='earth-team')],
                               sounds=[],
                               sound_stereo_balance=0.0)

        self.assertEqual(up_event, replay.events[1])

        # Let's briefly check that the next event has been added as well.
        self.assertEqual(20000, replay.events[2].timestamp_millis)

    async def test_zap_and_damage_opponent(self):
        await self.game.events.add(
            await create_zap_event(2000, self.entity2.entity_id, self.entity1.entity_id, opponent_down=False))
        await self.game.events.add(
            await create_zap_event(20000, self.entity2.entity_id, self.entity1.entity_id, opponent_down=False))

        replay = await create_sm5_replay(self.game)

        # Scout zaps commander. Commander won't go down.
        expected_events = [ReplayEvent(timestamp_millis=2000, message='Miles zaps Indy', team_scores=[-20, 100],
                                       cell_changes=[ReplayCellChange(row_id='r3',
                                                                      column=4,
                                                                      new_value='29'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=7,
                                                                      new_value='100.00%'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=6,
                                                                      new_value='1'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=2,
                                                                      new_value='100'),
                                                     ReplayCellChange(row_id='r1',
                                                                      column=2,
                                                                      new_value='-20'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=8,
                                                                      new_value=''),
                                                     ReplayCellChange(row_id='r1',
                                                                      column=8,
                                                                      new_value='0.00')],  # K/D
                                       row_changes=[],
                                       # player down
                                       sounds=[ReplaySound(asset_urls=['/assets/sm5/audio/Effect/Scream.0.wav',
                                                                       '/assets/sm5/audio/Effect/Scream.1.wav',
                                                                       '/assets/sm5/audio/Effect/Scream.2.wav',
                                                                       '/assets/sm5/audio/Effect/Shot.0.wav',
                                                                       '/assets/sm5/audio/Effect/Shot.1.wav'],
                                                           id=3, priority=0, required=False)],
                                       sound_stereo_balance=-0.5),
                           ReplayEvent(timestamp_millis=20000,
                                       message='Miles zaps Indy',
                                       team_scores=[-40, 200],
                                       cell_changes=[ReplayCellChange(row_id='r3',
                                                                      column=4,
                                                                      new_value='28'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=7,
                                                                      new_value='100.00%'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=6,
                                                                      new_value='2'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=2,
                                                                      new_value='200'),
                                                     ReplayCellChange(row_id='r1',
                                                                      column=2,
                                                                      new_value='-40'),
                                                     ReplayCellChange(row_id='r3',
                                                                      column=8,
                                                                      new_value=''),
                                                     ReplayCellChange(row_id='r1',
                                                                      column=8,
                                                                      new_value='0.00')],
                                       row_changes=[],
                                       sounds=[ReplaySound(asset_urls=['/assets/sm5/audio/Effect/Scream.0.wav',
                                                                       '/assets/sm5/audio/Effect/Scream.1.wav',
                                                                       '/assets/sm5/audio/Effect/Scream.2.wav',
                                                                       '/assets/sm5/audio/Effect/Shot.0.wav',
                                                                       '/assets/sm5/audio/Effect/Shot.1.wav'],
                                                           id=3,
                                                           priority=0,
                                                           required=False)],
                                       sound_stereo_balance=-0.5)]

        self.assertEqual(expected_events, replay.events)


if __name__ == '__main__':
    unittest.main()

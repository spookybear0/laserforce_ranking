import unittest

from sanic import exceptions

from db.types import Team
from helpers.gamehelper import get_players_from_team, get_team_rosters, PlayerInfo, get_player_display_names, \
    get_matchmaking_teams
from tests.helpers.environment import setup_test_database, teardown_test_database, add_entity, get_red_team, \
    get_green_team, get_blue_team


class TestGameHelper(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await setup_test_database()

    async def asyncTearDown(self):
        await teardown_test_database()

    async def test_get_players_from_team(self):
        player1 = {
            "name": "Indy",
            "team": 0,
        }
        player2 = {
            "name": "Barbie",
            "team": 1,
        }
        player3 = {
            "name": "Sonic",
            "team": 1,
        }

        players_in_team = get_players_from_team([player1, player2, player3], team_index=1)

        self.assertCountEqual([player2, player3], players_in_team)

    async def test_get_team_rosters(self):
        entity1, entity_end1 = await add_entity(entity_id="@NotLoggedIn", name="Indy", team=get_red_team())
        entity2, entity_end2 = await add_entity(entity_id="@Red Base", name="Red Base", team=get_red_team(),
                                                type="base")
        entity3, entity_end3 = await add_entity(entity_id="@NotMember", name="Miles", team=get_green_team())
        entity4, entity_end4 = await add_entity(entity_id="LoggedIn", name="Bumblebee", team=get_red_team())
        entity5, entity_end5 = await add_entity(entity_id="KickedPlayer", name="Removed", team=get_red_team(),
                                                omit_entity_end=True)

        roster = await get_team_rosters([entity1, entity2, entity3, entity4, entity5],
                                        [entity_end1, entity_end2, entity_end3, entity_end4])

        player1 = PlayerInfo(entity_start=entity1, entity_end=entity_end1, display_name="Indy")
        # entity2 is not a player2 and should be ignored.
        player3 = PlayerInfo(entity_start=entity3, entity_end=entity_end3, display_name="Miles")
        player4 = PlayerInfo(entity_start=entity4, entity_end=entity_end4, display_name="Bumblebee")
        # entity5 doesn't have an EntityEnds and should be ignored.

        self.assertDictEqual({
            Team.RED: [player1, player4],
            Team.GREEN: [player3]
        }, roster)

    async def test_get_player_display_names(self):
        entity1, entity_end1 = await add_entity(entity_id="@LoggedIn", name="Indy", team=get_red_team(), type="player")
        entity2, entity_end2 = await add_entity(entity_id="@Member", name="Miles", team=get_green_team(), type="player")

        player1 = PlayerInfo(entity_start=entity1, entity_end=entity_end1, display_name="Indy")
        player2 = PlayerInfo(entity_start=entity2, entity_end=entity_end2, display_name="Miles")

        self.assertCountEqual(["Indy", "Miles"], get_player_display_names([player1, player2]))

    async def test_get_matchmaking_teams(self):
        entity1, entity_end1 = await add_entity(entity_id="@NotLoggedIn", name="Indy", team=get_red_team(),
                                                type="player")
        entity2, entity_end2 = await add_entity(entity_id="@NotMember", name="Miles", team=get_green_team(),
                                                type="player")
        entity3, entity_end3 = await add_entity(entity_id="LoggedIn", name="Bumblebee", team=get_red_team(),
                                                type="player")

        roster = await get_team_rosters([entity1, entity2, entity3],
                                        [entity_end1, entity_end2, entity_end3])

        player_matchmaking_1, player_matchmaking_2 = await get_matchmaking_teams(roster)

        # Red team should be team 1.
        self.assertCountEqual(["Indy", "Bumblebee"], player_matchmaking_1)
        self.assertCountEqual(["Miles"], player_matchmaking_2)

    async def test_get_matchmaking_teams_no_red_team(self):
        entity1, entity_end1 = await add_entity(entity_id="@NotLoggedIn", name="Indy", team=get_blue_team(),
                                                type="player")
        entity2, entity_end2 = await add_entity(entity_id="@NotMember", name="Miles", team=get_green_team(),
                                                type="player")
        entity3, entity_end3 = await add_entity(entity_id="LoggedIn", name="Bumblebee", team=get_blue_team(),
                                                type="player")

        roster = await get_team_rosters([entity1, entity2, entity3],
                                        [entity_end1, entity_end2, entity_end3])

        player_matchmaking_1, player_matchmaking_2 = await get_matchmaking_teams(roster)

        # The order of the teams is not defined.
        if "Miles" in player_matchmaking_2:
            self.assertCountEqual(["Indy", "Bumblebee"], player_matchmaking_1)
            self.assertCountEqual(["Miles"], player_matchmaking_2)
        else:
            self.assertCountEqual(["Indy", "Bumblebee"], player_matchmaking_2)
            self.assertCountEqual(["Miles"], player_matchmaking_1)

    async def test_get_matchmaking_teams_one_team_only(self):
        entity1, entity_end1 = await add_entity(entity_id="@LoggedIn", name="Indy", team=get_blue_team(), type="player")

        roster = await get_team_rosters([entity1],
                                        [entity_end1])

        with self.assertRaises(exceptions.ServerError):
            await get_matchmaking_teams(roster)


if __name__ == '__main__':
    unittest.main()

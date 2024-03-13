try:
    from openskill.models import PlackettLuceRating as Rating
except ImportError:
    from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as Rating
from db.game import EntityStarts, EntityEnds, Events
from db.laserball import LaserballStats
from db.sm5 import SM5Stats
from db.types import Permission, GameType, Role, Team, IntRole
from tortoise import Model, fields, functions
from tortoise.expressions import F, Q
from typing import Optional, List
from collections import Counter
import statistics
import bcrypt

class Player(Model):
    id = fields.IntField(pk=True)
    player_id = fields.CharField(20)
    codename = fields.CharField(255)
    entity_id = fields.CharField(50, default="")
    sm5_mu = fields.FloatField(default=25)
    sm5_sigma = fields.FloatField(default=8.333)
    laserball_mu = fields.FloatField(default=25)
    laserball_sigma = fields.FloatField(default=8.333)
    timestamp = fields.DatetimeField(auto_now=True)

    # account stuff
    password = fields.CharField(255, null=True) # hashed password
    permissions = fields.IntEnumField(Permission, default=Permission.USER)
    
    @property
    def sm5_ordinal(self) -> float:
        return self.sm5_mu - 3 * self.sm5_sigma
    
    @property
    def laserball_ordinal(self) -> float:
        return self.laserball_mu - 3 * self.laserball_sigma
    
    @property
    def sm5_rating(self) -> Rating:
        return Rating(self.sm5_mu, self.sm5_sigma)

    @property
    def laserball_rating(self) -> Rating:
        return Rating(self.laserball_mu, self.laserball_sigma)
    
    # account stuff

    async def set_password(self, password: str) -> None:
        from helpers import userhelper
        self.password = userhelper.hash_password(password)
        await self.save()

    def check_password(self, password: Optional[str]) -> bool:
        if self.password is None or password is None:
            return False

        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))
    
    # stats
    
    async def get_favorite_role(self) -> Optional[Role]:
        """
        SM5 only
        """

        # get the most played role
        role = await EntityStarts.filter(entity_id=self.entity_id, sm5games__mission_name__icontains="space marines").annotate(count=functions.Count("role")).order_by("-count").first()
        if role is None:
            return None
        return role.role
    
    async def get_favorite_battlesuit(self, game_type: Optional[GameType]=None) -> Optional[str]:
        """
        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted
        """

        # battlesuit is an entitystarts attribute which is a string
        # we need to count each time a battlesuit is used and return the most used one

        if game_type is None:
            battlesuits = await EntityStarts.filter(entity_id=self.entity_id).values_list("battlesuit", flat=True)
        elif game_type == GameType.SM5:
            battlesuits = await EntityStarts.filter(entity_id=self.entity_id, sm5games__mission_name__icontains="space marines").values_list("battlesuit", flat=True)
        elif game_type == GameType.LASERBALL:
            battlesuits = await EntityStarts.filter(entity_id=self.entity_id, laserballgames__mission_name__icontains="laserball").values_list("battlesuit", flat=True)
        else:
            # raise exception
            raise ValueError("Invalid game_type")

        if not battlesuits:
            return None
        
        # find most common battlesuit
        data = Counter(battlesuits)
        return data.most_common(1)[0][0]
    
    async def get_sean_hits(self, game_type: Optional[GameType]=None) -> int:
        """
        AIDAN REQUESTED THIS

        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted

        returns: number of times the player hit sean (Commander)
        """

        sean_entity_id = "#w7Wt8y"

        if game_type is None:
            return await Events.filter(
                arguments__filter={"0": self.entity_id}
            ).filter(
                Q(arguments__filter={"1": " zaps "}) | Q(arguments__filter={"1": " blocks "}) | Q(arguments__filter={"1": " steals from "})
            ).filter(
                arguments__filter={"2": sean_entity_id}
            ).count()
        elif game_type == GameType.SM5:
            return await Events.filter(
                sm5games__mission_name__icontains="space marines", arguments__filter={"0": self.entity_id}
            ).filter(
                arguments__filter={"1": " zaps "}
            ).filter(
                arguments__filter={"2": sean_entity_id}
            ).count()
        elif game_type == GameType.LASERBALL:
            return await Events.filter(
            laserballgames__mission_name__icontains="laserball", arguments__filter={"0": self.entity_id}
            ).filter(
                Q(arguments__filter={"1": " blocks "}) | Q(arguments__filter={"1": " steals from "})
            ).filter(
                arguments__filter={"2": sean_entity_id}
            ).count()
        else:
            # raise exception
            raise ValueError("Invalid game_type")
    
    async def get_shots_fired(self, game_type: Optional[GameType]=None) -> int:
        """
        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted

        returns: number of shots fired by the player
        """

        if game_type is None:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True) + await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True))
        elif game_type == GameType.SM5:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True))
        elif game_type == GameType.LASERBALL:
            return sum(await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_fired", flat=True))
        
    async def get_shots_hit(self, game_type: Optional[GameType]=None) -> int:
        """
        Argument "game_type" can be None, "sm5", or "laserball"
        None means all game types are counted

        returns: number of shots hit by the player
        """

        if game_type is None:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True) + await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True))
        elif game_type == GameType.SM5:
            return sum(await SM5Stats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True))
        elif game_type == GameType.LASERBALL:
            return sum(await LaserballStats.filter(entity__entity_id=self.entity_id).values_list("shots_hit", flat=True))
    
    async def times_played_as_team(self, team: Team, game_type: GameType=None) -> int:
        """
        If game_type is None, all game types are counted
        """

        if team == Team.RED:
            team_color = "Fire"
        elif team == Team.BLUE:
            team_color = "Ice"
        else:
            team_color = "Earth"
            
        if game_type is None:
            return await EntityStarts.filter(entity_id=self.entity_id, team__color_name=team_color).count()
        else:
            if game_type == GameType.SM5:
                return await EntityStarts.filter(entity_id=self.entity_id, team__color_name=team_color, sm5games__mission_name__icontains="space marines").count()
            elif game_type == GameType.LASERBALL:
                return await EntityStarts.filter(entity_id=self.entity_id, team__color_name=team_color, laserballgames__mission_name__icontains="laserball").count()
            
        
    async def times_played_as_role(self, role: Role) -> int:
        return await EntityStarts.filter(entity_id=self.entity_id, role=IntRole.from_role(role)).count()
    
    async def get_win_percent(self, game_type: GameType=None) -> float:
        """
        If game_type is None, all game types are counted
        """

        if game_type is None:
            #return None

            wins = await EntityStarts.filter(entity_id=self.entity_id, team__real_color_name=F("winner_color"), sm5games__winner__not_isnull="").count()
            losses = await EntityStarts.filter(entity_id=self.entity_id).exclude(team=F("winner"), sm5games__winner__not_isnull="").count()
        else:
            game_type_filter_name = "space marines" if game_type == GameType.SM5 else "laserball"
            wins = await EntityStarts.filter(entity_id=self.entity_id, team__real_color_name=F("winner_color"), sm5games__mission_name__icontains=game_type_filter_name).count()
            losses = await EntityStarts.filter(entity_id=self.entity_id, sm5games__mission_name__icontains=game_type_filter_name).exclude(team=F("winner")).count()
    
        if wins + losses == 0:
            return 0
        
        return wins / (wins + losses)
    
    async def get_wins_as_team(self, team: Team, game_type: GameType=None) -> int:
        """
        If game_type is None, all game types are counted
        """

        if team == Team.RED:
            team_color = "Fire"
        elif team == Team.BLUE:
            team_color = "Ice"
        else:
            team_color = "Earth"
            
        if game_type is None:
            wins = await EntityStarts.filter(entity_id=self.entity_id, team__real_color_name=F("winner_color"), sm5games__winner__not_isnull="").filter(team__color_name=team_color).count()
        else:
            if game_type == game_type.SM5:
                wins = await EntityStarts.filter(sm5games__mission_name__icontains="space marines", entity_id=self.entity_id, team__real_color_name=F("winner_color")).filter(team__color_name=team_color).count()
            else: # laserball
                wins = await EntityStarts.filter(laserballgames__mission_name__icontains="laserball", entity_id=self.entity_id, team__real_color_name=F("winner_color")).filter(team__color_name=team_color).count()
        return wins
    
    # custom funcs for plotting
    
    async def get_median_role_score(self) -> List[float]:
        """
        SM5 only

        returns: roles median score in order of Role enum (Commander, Heavy, Scout, Ammo, Medic)
        """

        scores = []

        for role in range(1, 6):
            entities = await EntityStarts.filter(role=role, entity_id=self.entity_id).values_list("id", flat=True)
            scores_role = await EntityEnds.filter(entity__id__in=entities).values_list("score", flat=True)
            try:
                scores.append(statistics.median(scores_role))
            except statistics.StatisticsError:
                scores.append(0)

        return scores
    
    @staticmethod
    async def get_median_role_score_world(median_role_score_player=None) -> List[float]:
        """
        SM5 only

        returns: roles median score in order of Role enum (Commander, Heavy, Scout, Ammo, Medic)

        we don't want to get median score for roles that haven't been played by the player
        """

        scores = []

        for role in range(1, 6):
            entities = await EntityStarts.filter(role=role).values_list("id", flat=True)
            scores_role = await EntityEnds.filter(entity__id__in=entities).values_list("score", flat=True)

            if median_role_score_player is not None:
                if median_role_score_player[role - 1] == 0:
                    continue

            try:
                scores.append(statistics.median(scores_role))
            except statistics.StatisticsError:
                scores.append(0)

        return scores

    def __str__(self) -> str:
        return f"{self.codename} ({self.player_id})"
    
    def __repr__(self) -> str:
        return f"<Player {self.codename} ({self.player_id})>"
# flake8: noqa: F821
# Disable "unknown name" because we're using forward references here that flake8 has no love for.

from __future__ import annotations

from dataclasses import dataclass

from tortoise import Model, fields

from db.sm5 import SM5Stats
from db.types import Team, IntRole, EventType, PlayerStateType


# general game stuff

class Teams(Model):
    index = fields.IntField()
    name = fields.CharField(50)
    color_enum = fields.IntField()  # no idea what this enum is
    color_name = fields.CharField(50)
    real_color_name = fields.CharField(50)  # this isn't in the tdf, but it's useful for the api (ex: "Fire" -> "Red")

    @property
    def enum(self) -> Team:
        conversions = {
            "Fire": Team.RED,
            "Earth": Team.GREEN,
            "Red": Team.RED,
            "Green": Team.GREEN,
            "Blue": Team.BLUE,
            "Ice": Team.BLUE,
        }

        return conversions[self.color_name]

    async def to_dict(self) -> dict:
        final = {}

        final["index"] = self.index
        final["name"] = self.name
        final["color_enum"] = int(self.color_enum)
        final["color_name"] = self.color_name
        final["real_color_name"] = self.real_color_name

        return final


class EntityStarts(Model):
    id = fields.IntField(pk=True)
    time = fields.IntField()  # time in milliseconds
    entity_id = fields.CharField(50)  # id of the entity
    type = fields.CharField(50)  # can be [player, standard-target, maybe more]
    name = fields.CharField(75)  # name of the entity
    team = fields.ForeignKeyField("models.Teams")
    level = fields.IntField()  # for sm5 this is always 0
    role = fields.IntEnumField(IntRole)  # 0 for targets, no idea what it is for laserball
    battlesuit = fields.CharField(50)  # for targets its the target name
    member_id = fields.CharField(50, null=True)  # only for newer games (or ones with the option to include member_id)

    async def get_player(self) -> "Player":
        # get the player object from the entity
        from db.player import Player
        return await Player.filter(entity_id=self.entity_id).first()

    async def get_entity_end(self) -> "EntityEnds":
        return await EntityEnds.filter(entity__id=self.id).first()

    async def get_sm5_stats(self) -> "SM5Stats":
        return await SM5Stats.filter(entity__id=self.id).first()

    async def get_score(self) -> int:
        return (await self.get_entity_end()).score

    async def to_dict(self) -> dict:
        final = {}

        final["id"] = self.id
        final["time"] = self.time
        final["entity_id"] = self.entity_id
        final["type"] = self.type
        final["name"] = self.name
        final["team"] = (await self.team).real_color_name
        final["team_index"] = (await self.team).index
        final["level"] = self.level
        final["role"] = int(self.role)
        final["battlesuit"] = self.battlesuit
        final["member_id"] = self.member_id

        return final

    def __str__(self) -> str:
        return f"<EntityStarts id={self.id} entity_id={self.entity_id} type={self.type} name={self.name} team={self.team} level={self.level} role={self.role} battlesuit={self.battlesuit} member_id={self.member_id}>"


class Events(Model):
    time = fields.IntField()  # time in milliseconds
    type = fields.CharEnumField(EventType)
    # variable number of fields depending on type of event
    # can be token or string for announcement
    # now make the field
    # Note that it's typically easier to just use entity1, action, and entity2 instead of arguments.
    # This field will remain for legacy reasons.
    arguments = fields.JSONField()  # list of arguments

    # The first entity involved in the action, typically the one performing the action.
    # Can be empty in some cases, for example global events such as "* Mission Start *".
    entity1 = fields.CharField(50, default="")

    # The action being performed by the entity (or the global event, such as "* Mission Start *").
    action = fields.CharField(50, default="")

    # The second entity involved in the action, typically the entity that something is being done to.
    # This can be empty if the action doesn't involve a specific recipient, for example if the main entity
    # activates a nuke.
    entity2 = fields.CharField(50, default="")

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["type"] = self.type.value
        final["arguments"] = self.arguments

        return final


class PlayerStates(Model):
    time = fields.IntField()  # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    state = fields.IntEnumField(PlayerStateType)

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["state"] = self.state

        return final


class Scores(Model):
    time = fields.IntField()  # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    old = fields.IntField()  # old score
    delta = fields.IntField()  # change in score
    new = fields.IntField()  # new score

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["old"] = self.old
        final["delta"] = self.delta
        final["new"] = self.new

        return final

    def __str__(self) -> str:
        return f"<Score {self.old} -> {self.new} ({self.delta})>"

    def __repr__(self) -> str:
        return str(self)


class EntityEnds(Model):
    time = fields.IntField()  # time in milliseconds
    entity = fields.ForeignKeyField("models.EntityStarts", to_field="id")
    type = fields.IntField()  # don't know what enum this is
    score = fields.IntField()
    current_rating_mu = fields.FloatField(null=True)  # only for players, only for ranked games
    current_rating_sigma = fields.FloatField(null=True)  # only for players, only for ranked games
    previous_rating_mu = fields.FloatField(null=True)  # only for players, only for ranked games
    previous_rating_sigma = fields.FloatField(null=True)  # only for players, only for ranked games

    async def get_player(self) -> "Player":
        # get the player object from the entity
        from db.player import Player
        return await Player.filter(entity_id=(await self.entity).entity_id).first()

    async def get_entity_start(self) -> EntityStarts:
        return await self.entity

    async def get_sm5_stats(self) -> "SM5Stats":
        return await SM5Stats.filter(entity__id=(await self.entity).entity_id).first()

    async def to_dict(self) -> dict:
        final = {}

        final["time"] = self.time
        final["entity"] = (await self.entity).entity_id
        final["type"] = self.type
        final["score"] = self.score
        final["current_rating_mu"] = self.current_rating_mu
        final["current_rating_sigma"] = self.current_rating_sigma
        if self.current_rating_mu and self.current_rating_sigma:
            final["current_rating"] = self.current_rating_mu - 3 * self.current_rating_sigma
        else:
            final["current_rating"] = None
        final["previous_rating_mu"] = self.previous_rating_mu
        final["previous_rating_sigma"] = self.previous_rating_sigma
        if self.previous_rating_mu and self.previous_rating_sigma:
            final["previous_rating"] = self.previous_rating_mu - 3 * self.previous_rating_sigma
        else:
            final["previous_rating"] = None

        return final

    def __str__(self) -> str:
        return f"<EntityEnd {self.entity} score={self.score}>"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class PlayerInfo:
    """Information about a player in one particular game."""
    entity_start: EntityStarts
    entity_end: EntityEnds
    display_name: str

    @property
    def is_member(self) -> bool:
        return not self.entity_start.entity_id.startswith("@")

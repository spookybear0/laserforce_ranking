from tortoise import Model, fields
from enum import Enum

class TagType(Enum):
    LF = "LF"  # legacy low Frequency (125kHz)
    HF = "HF"  # nfc high frequency (13.56MHz)

# rfid tag (125khz/13.56mhz) storing id (ex: 2831191 or 47:0f:51:b4)
class Tag(Model):
    id = fields.CharField(max_length=64, unique=True, pk=True)
    type = fields.CharEnumField(TagType) # type of tag (LF/HF)
    player = fields.ForeignKeyField("models.Player", related_name="tags", on_delete=fields.CASCADE)

    @property
    def is_empty(self) -> bool:
        return self.player is None

    def __str__(self):
        return f"Tag(id={self.id}, type={self.type}, player={self.player})"

    class Meta:
        table = "tag"
        ordering = ["id"]
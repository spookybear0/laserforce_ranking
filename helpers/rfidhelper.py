

def to_hex(tag: str):
    return "LF/0D00" + hex(int(tag)).strip("0x").upper()


def to_decimal(tag: str):
    return "000" + str(int(tag.strip("LF/").strip("0D00"), 16))
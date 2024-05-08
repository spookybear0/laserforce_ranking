from datetime import datetime


def suffix(date: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(date % 20, "th")


def strftime_ordinal(format: str, time_: datetime) -> str:
    return time_.strftime(format).replace("{S}", str(time_.day) + suffix(time_.day))

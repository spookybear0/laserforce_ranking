"""Various functions to format values."""


def create_ratio_string(ratio: float) -> str:
    """Converts a ratio to a string, such as "1:2" or "3:4"."""
    if ratio == 0.0:
        return "0:0"

    factor = 1

    if ratio < 0.0:
        ratio *= -1.0
        factor = -1

    while True:
        if ratio >= 0.95:
            return "%.2g:%d" % (ratio, factor)

        if ratio < 0.12:
            ratio *= 10
            factor *= 10
        elif ratio < 0.22:
            ratio *= 5
            factor *= 5
        elif ratio < 0.4:
            ratio *= 3
            factor *= 3
        else:
            ratio *= 2
            factor *= 2

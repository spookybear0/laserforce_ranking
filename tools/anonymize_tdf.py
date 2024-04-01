"""Script to remove all PII from TDF files."""
import random
import string
import sys
from collections import defaultdict


def _create_random_entity_id():
    """Returns a random string that looks like an entity ID, for example #CLv25"""
    chars = string.ascii_letters + string.digits
    return "#%s" % "".join(random.sample(chars, random.randint(5, 7)))


def _create_random_player_name():
    """Returns a random string that represents a player name.

    This string might be one or two words and might have a Unicode character in it."""
    name = random.choice(string.ascii_uppercase) + "".join(random.sample(string.ascii_lowercase, random.randint(3, 7)))

    if random.randint(0, 1) > 0:
        name += " " + random.choice(string.ascii_uppercase) + "".join(
            random.sample(string.ascii_lowercase, random.randint(3, 7)))

    if random.randint(0, 10) > 6:
        name += "☺"

    return name


def anonymize_tdf(input_filename: str, output_filename: str):
    with open(input_filename, "r", encoding="utf-16") as input_file:
        with open(output_filename, "w", encoding="utf-16") as output_file:
            # All maps have the original name as key and the random pseudo-name as values.
            entity_ids = defaultdict(_create_random_entity_id)
            player_names = defaultdict(_create_random_player_name)

            for line in input_file:
                elements = line.strip().split("\t")

                if not elements:
                    print(line, file=output_file)
                    continue

                if elements[0] == "3":
                    # An "entity-start" entry.
                    if len(elements) < 5:
                        raise ValueError("Entity-start definition with missing columns: %s" % line)

                    if elements[2][0] != "#":
                        # This is not a player, so there's no PII.
                        print(line, file=output_file)
                        continue

                    elements[2] = entity_ids[elements[2]]
                    elements[4] = player_names[elements[4]]
                    print("\t".join(elements), file=output_file)
                else:
                    # For all other entries, we can simply look for the entity ID
                    # (which is distinct enough) and replace it with the dummy.
                    sanitized_elements = [
                        element if element not in entity_ids else entity_ids[element] for element in elements
                    ]

                    print("\t".join(sanitized_elements), file=output_file)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: anonyize_tdf.py <input_file.tdf> <output_file.tdf>")
        exit(10)

    anonymize_tdf(sys.argv[1], sys.argv[2])

# helpers/og_images.py

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from laserforce_ranking.models import EntityType, Team, SM5Game, EntityStart, SM5Stats
from django.conf import settings
from pathlib import Path
from typing import List

WIDTH = 1200
HEIGHT = 630


ASSETS_DIR = Path(settings.BASE_DIR) / "assets"


def get_font(size, bold=False) -> FreeTypeFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(ASSETS_DIR / "fonts" / filename), size)

def draw_team(
    draw,
    image,
    sm5game: SM5Game,
    team: Team,
    x: int,
    y: int,
    width: int,
    height: int,
    team_font: FreeTypeFont,
    score_font: FreeTypeFont,
    normal_font: FreeTypeFont,
    bold_font: FreeTypeFont,
    small_font: FreeTypeFont
):
    color = team.enum.plain_color.rgb_tuple

    # background

    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=16,
        fill=(31, 34, 40),
    )

    # team color bar

    draw.rounded_rectangle(
        (x, y, x + width, y + 7),
        radius=4,
        fill=color,
    )

    # team name

    draw.text(
        (x + 20, y + 18),
        team.name,
        font=team_font,
        fill=color,
    )

    # team score

    score = (
        team.score
        + sm5game.get_team_score_adjustment(team.enum)
    )

    score_text = str(score)

    bbox = draw.textbbox(
        (0, 0),
        score_text,
        font=score_font,
    )

    draw.text(
        (
            x + width - 20 - (bbox[2] - bbox[0]),
            y + 15,
        ),
        score_text,
        font=score_font,
        fill=(245, 245, 245),
    )

    # doubles %

    doubles = team.doubles_percent or 0

    doubles_text = f"Doubles: {doubles * 100:.2f}%"

    draw.text(
        (x + 20, y + 53),
        doubles_text,
        font=small_font,
        fill=(150, 155, 165),
    )

    # get players

    players: List[EntityStart] = list(
        team.entity_starts
        .filter(
            type=EntityType.PLAYER,
        )
        .select_related(
            "entity_end",
            "sm5_stats",
        )
        .order_by(
            "-entity_end__score",
        )
    )

    table_y = y + 88

    # header

    headers = [
        ("ROLE", 20),
        ("PLAYER", 75),
        ("SCORE", 260),
        ("MVP", 325),
        ("K/D", 380),
        ("ACC", 435),
        ("M HITS", 485),
    ]

    for text, offset in headers:
        draw.text(
            (x + offset, table_y),
            text,
            font=small_font,
            fill=(105, 110, 120),
        )

    draw.line(
        (
            x + 15,
            table_y + 25,
            x + width - 15,
            table_y + 25,
        ),
        fill=(60, 63, 70),
        width=1,
    )

    # player rows

    row_y = table_y + 38

    for entity in players:
        end = entity.entity_end
        stats: SM5Stats = entity.sm5_stats

        role_image_path = ASSETS_DIR / "sm5" / "roles" / f"{entity.role.name.lower()}.png"

        if role_image_path and role_image_path.exists():
            role_image = Image.open(role_image_path).convert("RGBA").resize((30, 30))
            image.paste(role_image, (x + 20, row_y - 5), role_image)
        else:
            # fallback to text if image is not available
            role = (
                entity.role.name.upper()[:4]
                if entity.role
                else "—"
            )

            draw.text(
                (x + 20, row_y),
                role,
                font=bold_font,
                fill=(190, 195, 205),
            )

        # codename

        name = entity.name or "Unknown"

        if len(name) > 21:
            name = name[:20] + "…"

        draw.text(
            (x + 75, row_y),
            name,
            font=normal_font,
            fill=(235, 235, 240),
        )

        # score

        draw.text(
            (x + 260, row_y),
            str(end.score),
            font=normal_font,
            fill=(235, 235, 240),
        )

        # MVP

        draw.text(
            (x + 325, row_y),
            f"{stats.mvp_points:.1f}",
            font=normal_font,
            fill=(235, 235, 240),
        )

        # K/D

        draw.text(
            (x + 380, row_y),
            f"{stats.kd_ratio:.2f}",
            font=normal_font,
            fill=(235, 235, 240),
        )

        # acc

        draw.text(
            (x + 435, row_y),
            f"{stats.accuracy * 100:.0f}%",
            font=normal_font,
            fill=(235, 235, 240),
        )

        # medic hits

        draw.text(
            (x + 485, row_y),
            str(stats.medic_hits_str),
            font=normal_font,
            fill=(235, 235, 240),
        )

        draw.line(
            (
                x + 15,
                row_y + 27,
                x + width - 15,
                row_y + 27,
            ),
            fill=(47, 50, 56),
            width=1,
        )

        row_y += 43

        if row_y > y + height - 20:
            break

def generate_sm5_game_image(sm5game):
    """
    Generate a 1200x630 Open Graph image for an SM5Game.

    Accepts an SM5Game instance directly.
    """

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (24, 26, 31),
    )

    draw = ImageDraw.Draw(image)

    title_font = get_font(30, bold=True)
    team_font = get_font(23, bold=True)
    score_font = get_font(30, bold=True)
    normal_font = get_font(16)
    bold_font = get_font(16, bold=True)
    small_font = get_font(13)

    # get teams

    teams = list(
        sm5game.teams
        .exclude(name="Neutral")
        .exclude(color_enum=0)
        .order_by("index")
    )

    if len(teams) != 2:
        raise ValueError(
            f"Expected 2 SM5 teams, got {len(teams)}"
        )

    # header

    draw.text(
        (40, 25),
        "LF RANKING",
        font=title_font,
        fill=(240, 240, 240),
    )

    game = sm5game

    site = str(game.site_id)

    if hasattr(sm5game, "ID_TO_SITE"):
        site = sm5game.ID_TO_SITE.get(
            game.site_id,
            game.site_id,
        )

    header = f"SM5 · Game #{game.pk}"

    draw.text(
        (40, 68),
        header,
        font=normal_font,
        fill=(155, 160, 170),
    )

    if game.start_time:
        date_text = game.start_time.strftime(
            "%b %d, %Y · %H:%M"
        )

        bbox = draw.textbbox(
            (0, 0),
            date_text,
            font=normal_font,
        )

        draw.text(
            (
                WIDTH - 40 - (bbox[2] - bbox[0]),
                38,
            ),
            date_text,
            font=normal_font,
            fill=(155, 160, 170),
        )

    draw.text(
        (
            WIDTH - 40 - draw.textbbox(
                (0, 0),
                site,
                font=small_font,
            )[2],
            68,
        ),
        site,
        font=small_font,
        fill=(120, 125, 135),
    )

    draw.line(
        (40, 102, WIDTH - 40, 102),
        fill=(55, 58, 65),
        width=2,
    )

    # teams
    draw_team(
        draw=draw,
        image=image,
        sm5game=sm5game,
        team=teams[0],
        x=40,
        y=120,
        width=550,
        height=430,
        team_font=team_font,
        score_font=score_font,
        normal_font=normal_font,
        bold_font=bold_font,
        small_font=small_font,
    )

    draw_team(
        draw=draw,
        image=image,
        sm5game=sm5game,
        team=teams[1],
        x=610,
        y=120,
        width=550,
        height=430,
        team_font=team_font,
        score_font=score_font,
        normal_font=normal_font,
        bold_font=bold_font,
        small_font=small_font,
    )

    # footer

    footer = (
        f"{'RANKED' if game.ranked else 'UNRANKED'}"
        f" · {game.duration}"
    )

    draw.text(
        (40, 585),
        footer,
        font=small_font,
        fill=(110, 115, 125),
    )

    footer_right = "laserforce.spoo.uk"

    bbox = draw.textbbox(
        (0, 0),
        footer_right,
        font=small_font,
    )

    draw.text(
        (
            WIDTH - 40 - (bbox[2] - bbox[0]),
            585,
        ),
        footer_right,
        font=small_font,
        fill=(110, 115, 125),
    )

    # export png

    output = BytesIO()

    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output
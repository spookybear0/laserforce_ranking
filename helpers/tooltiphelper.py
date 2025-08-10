from helpers.gamehelper import SM5_STATE_COLORS

# Tooltips that are plain strings (basic HTML is allowed), will be embedded in the attribute.
_PLAIN_TOOLTIPS = {
    # Tooltips for SM5 games.
    "sm5_role": "The role this player had",
    "sm5_codename": "Name of the player",
    "sm5_rating": "Rating for this player at the point after this game has been played",
    "sm5_rating_difference": "Rating difference for this player at the point after this game has been played. " +
                            "A positive number means the player gained rating, a negative number means they lost rating. " +
                            "A zero means the rating did not change.",
    "sm5_score": "Final score",
    "sm5_positive_score": "Final score without any reductions (no penalties for getting zapped, missiled, nuked, etc)",
    "sm5_points_minute": "Number of points per minute of time the player spent in the game",
    "sm5_lives_left": "Number of lives left when the game finished",
    "sm5_alive": "The time the player was alive in the game (if red, the player was eliminated)",
    "sm5_shots_left": "Number of shots left when the game finished",
    "sm5_accuracy": "Percentage of shots that hit something",
    "sm5_kd_ratio": "Ratio of how many times this player zapped someone vs. how many times they got zapped. " +
                    "The number is about zaps, <b>not</b> missiles, nukes, or downs.",
    "sm5_missiled_other": "Number of times this player successfully missiled another player",
    "sm5_missiled": "Number of times this player got successfully missiled",
    "sm5_shot_team": "Number of times this player zapped a team mate",
    "sm5_missiled_team": "Number of times this player missiled a team mate",
    "sm5_medic_hits": "Number of times this player hit an enemy medic",
    "sm5_you_zapped": "How many times you zapped this particular player",
    "sm5_zapped_you": "How many times this particular player zapped you",
    "sm5_hit_ratio": "The ratio between you zapping the player and they zapping you",
    "sm5_you_missiled": "How many times you missiled this particular player",
    "sm5_missiled_you": "How many times this particular player missiled you",
    "sm5_penalty": "Penalty",
    # Other tooltips.
    "unranked_reason_ended_early": "Ended early",
    "unranked_reason_too_small": "Too small",
    "unranked_reason_too_large": "Too large",
    "unranked_reason_unbalanced": "Unbalanced",
    "unranked_reason_unknown": "Unknown reason",
}

# Tooltips that are complex that they're implemented as separate DIV tags. The value is the ID of the tag.
_COMPLEX_TOOLTIPS = {
    # Tooltips for SM5 games.
    "sm5_states": "tooltip-sm5-states",
    "sm5_mvp_points": "tooltip-sm5-mvp-points",
}

# Mapping of an SM5 state to its description in the tooltip.
_SM5_STATE_DESCRIPTIONS = {
    "Active": "Active",
    "Down": "Down for whatever reason, except while being resupplied",
    "Down (Resup)": "Down while being resupplied",
    "Resettable": "Down but resettable (can be zapped again)",
}


def _insert_tooltip(tooltip_id: str) -> str:
    """Inserts an attribute into a HTML element that adds a Tippy tooltip.

    Depending on the tooltip ID, this is either an inline tooltip string or a reference to a separate DIV element.

    Args:
        tooltip_id: ID of the tooltip. This is a key either in _PLAIN_TOOLTIPS or _COMPLEX_TOOLTIPS.
    """
    if tooltip_id in _PLAIN_TOOLTIPS:
        return "data-tippy-content=\"%s\"" % _PLAIN_TOOLTIPS[tooltip_id]

    if tooltip_id in _COMPLEX_TOOLTIPS:
        return "data-template=\"%s\"" % _COMPLEX_TOOLTIPS[tooltip_id]

    raise ValueError("Unknown tooltip ID %s" % tooltip_id)


# This is the main blob that can be passed down to HTML templates. It contains
# everything a template needs to handle tooltips.
TOOLTIP_INFO = {
    "sm5_state_legend": [
        {
            "color": SM5_STATE_COLORS[state],
            "description": _SM5_STATE_DESCRIPTIONS[state],
        } for state in SM5_STATE_COLORS.keys()
    ],
    "insert_tooltip": _insert_tooltip
}

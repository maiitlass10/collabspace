"""
How a user appears to collaborators in the editor (name + color).

The server is the single source of truth: the WebSocket consumer overwrites
whatever name/color a browser claims with the values computed here, so nobody
can pretend to be someone else.
"""

# Dark enough for white text (labels on carets and avatars).
# Must be "#RRGGBB": Tiptap's caret extension ignores any other format.
PRESENCE_COLORS = [
    "#4f46e5",  # indigo
    "#0891b2",  # cyan
    "#059669",  # emerald
    "#d97706",  # amber
    "#db2777",  # pink
    "#7c3aed",  # violet
    "#dc2626",  # red
    "#2563eb",  # blue
    "#65a30d",  # lime
    "#c2410c",  # orange
]


def presence_color(user) -> str:
    """Stable color per account: the same user always gets the same color."""
    return PRESENCE_COLORS[user.pk % len(PRESENCE_COLORS)]


def presence_identity(user) -> dict:
    """The `user` field the server puts in every awareness (presence) state."""
    return {"id": user.pk, "name": user.display_name, "color": presence_color(user)}

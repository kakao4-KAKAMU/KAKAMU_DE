"""Feed/Comment summary lookup Cypher."""

from __future__ import annotations

from typing import Final

GET_FEED_SUMMARY: Final[str] = """
MATCH (f:Feed {feed_id: $feed_id})
RETURN f.summary AS summary
LIMIT 1
"""

GET_COMMENT_SUMMARY: Final[str] = """
MATCH (c:Comment {comment_id: $comment_id})
RETURN c.summary AS summary
LIMIT 1
"""

GET_MOVIE_PLOT_RAW: Final[str] = """
MATCH (m:Movie {movie_id: $movie_id})
RETURN m.plot_raw AS plot_raw
LIMIT 1
"""


__all__ = [
    "GET_COMMENT_SUMMARY",
    "GET_FEED_SUMMARY",
    "GET_MOVIE_PLOT_RAW",
]

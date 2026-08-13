"""Fast unstructured pre-router (TF-IDF + numpy cosine)."""

from ins_claims_agent.pre_router.route_text import (
    CONTENT_ID,
    DEFAULT_MARGIN,
    DEFAULT_THRESHOLD,
    LABELS,
    route_unstructured,
)

__all__ = [
    "CONTENT_ID",
    "DEFAULT_MARGIN",
    "DEFAULT_THRESHOLD",
    "LABELS",
    "route_unstructured",
]

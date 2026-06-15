"""ID generation helpers for probes and patterns."""

from uuid import uuid4


def new_probe_id() -> str:
    """Generate a short, unique probe identifier (e.g. ``P-1a2b3c4d``)."""
    return f"P-{uuid4().hex[:8]}"

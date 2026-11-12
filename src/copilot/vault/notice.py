"""Partial view notices for role-based access control (D68)."""
from .models import PARTIAL_VIEW_NOTICE


def render_partial_view_notice() -> str:
    """Return the standard notice banner text when viewing formal books without cash memo."""
    return PARTIAL_VIEW_NOTICE

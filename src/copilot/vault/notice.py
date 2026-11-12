"""Partial view notices for role-based access control (D68)."""

PARTIAL_VIEW_NOTICE = "Formal books only. The owner's cash memo is not included in this view."


def render_partial_view_notice():
    """Render the standard notice banner when viewing formal books without cash memo."""
    import streamlit as st

    st.info(PARTIAL_VIEW_NOTICE)

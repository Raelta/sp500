import streamlit as st
from src.ui.auth import render_logout_button
from src.ui.utils import get_app_version

def render_footer():
    """
    Renders a persistent footer at the bottom of the page.
    Contains Logout button, Branding, and Version info.
    """
    st.divider()
    
    # Use columns to organize the footer
    # Layout: [Logout Button] [Branding (Center)] [Version (Right)]
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Logout button
        # render_logout_button renders st.sidebar.button by default?
        # No, let's check src/ui/auth.py
        # It renders st.sidebar.button("Log Out").
        # We need to change that function or use a different one.
        pass

    with col2:
        # Branding (Centered)
        st.markdown(
            "<div style='text-align: center; color: gray; margin-top: 5px;'>"
            "Built by Realta"
            "</div>", 
            unsafe_allow_html=True
        )
        
    with col3:
        # Version info (Right aligned)
        ver = get_app_version()
        st.markdown(
            f"<div style='text-align: right; color: gray; font-size: 0.8em; margin-top: 5px;'>"
            f"v0.1.{ver['count']} ({ver['hash']})"
            "</div>",
            unsafe_allow_html=True
        )

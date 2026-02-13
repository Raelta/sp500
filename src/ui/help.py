import streamlit as st
import json
import os

PREFS_FILE = ".user_prefs.json"

def get_preferences():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_preferences(prefs):
    try:
        with open(PREFS_FILE, "w") as f:
            json.dump(prefs, f)
    except Exception:
        pass

def render_help_page():
    st.header("Help & Information")
    st.markdown("""
    **Project Overview**
    This tool is designed for analyzing SP500 intraday price movements, specifically identifying "Bump & Slide" patterns. 
    It allows you to explore historical data and run goal-seeking algorithms to find optimal parameters for trading strategies.

    **Key Features:**
    - **Exploration Mode:** Interactive visualization of price data with configurable bump/slide detection.
    - **Goal Seek Mode:** Automated search for profitable parameter configurations using historical backtesting.
    - **Cloud Integration:** Offload heavy computations to Google Cloud Run (optional).

    **Built by Raelta**
    """)
    
    st.markdown("---")
    
    # Checkbox for "Never show again"
    prefs = get_preferences()
    current_setting = prefs.get("never_show_help", False)
    
    never_show = st.checkbox("Never show this on startup again", value=current_setting)
    
    if st.button("Close Help", type="primary"):
        prefs["never_show_help"] = never_show
        save_preferences(prefs)
        st.session_state.show_help = False
        st.rerun()

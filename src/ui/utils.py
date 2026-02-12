import streamlit as st
import subprocess
import time as time_module

def get_app_version():
    """
    Returns a dictionary with version info: hash, count, date.
    """
    try:
        short_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
        count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).decode('ascii').strip()
        date = subprocess.check_output(['git', 'show', '-s', '--format=%cd', '--date=format:%Y-%m-%d %H:%M', 'HEAD']).decode('ascii').strip()
        return {
            "hash": short_hash,
            "count": count,
            "date": date
        }
    except Exception:
        return {
            "hash": "Unknown",
            "count": "0",
            "date": "Unknown"
        }

def render_checkbox_dropdown(label, options, key_prefix, default_all=True):
    """
    Renders an Excel-style dropdown with checkboxes and 'Select All'.
    Returns a list of selected options.
    """
    # Initialize session state for this component if not present
    all_key = f"{key_prefix}_all"
    
    # Check if we need to initialize individual keys
    # We do this once or if the options list changes drastically (simple check)
    if all_key not in st.session_state:
        st.session_state[all_key] = default_all
        for opt in options:
            st.session_state[f"{key_prefix}_{opt}"] = default_all

    # Callback for Select All
    def toggle_all():
        new_state = st.session_state[all_key]
        for opt in options:
            st.session_state[f"{key_prefix}_{opt}"] = new_state

    # Callback for Individual Item (Updates Select All visual state)
    def toggle_item():
        # If any item is unchecked, Select All should be unchecked
        # If all items are checked, Select All should be checked
        all_checked = True
        for opt in options:
            if not st.session_state.get(f"{key_prefix}_{opt}", False):
                all_checked = False
                break
        st.session_state[all_key] = all_checked

    # UI Rendering
    selected_items = []
    
    # Calculate count for the label (e.g., "Years (5 selected)")
    # We need to peek at current state (or default)
    current_selected_count = 0
    for opt in options:
        if st.session_state.get(f"{key_prefix}_{opt}", default_all):
            current_selected_count += 1
            
    with st.expander(f"{label} ({current_selected_count})", expanded=False):
        # Select All Checkbox
        st.checkbox("(Select All)", key=all_key, on_change=toggle_all)
        
        # Individual Checkboxes
        for opt in options:
            # We use the key directly to bind to session state
            is_checked = st.checkbox(str(opt), key=f"{key_prefix}_{opt}", on_change=toggle_item)
            if is_checked:
                selected_items.append(opt)
                
    return selected_items

def log_perf(label, start_time):
    # Helper to log performance
    duration = time_module.time() - start_time
    msg = f"[PERF] {label}: {duration:.4f}s"
    print(msg)
    if 'perf_logs' not in st.session_state:
        st.session_state.perf_logs = []
    st.session_state.perf_logs.append(msg)
    return time_module.time() # Return new start time

def inject_compact_sidebar_style():
    """
    Injects CSS to make the sidebar more compact.
    """
    st.markdown(
        """
        <style>
        /* Compact Sidebar Container */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }
        
        /* Reduce vertical spacing between widgets */
        section[data-testid="stSidebar"] .stElementContainer {
            margin-bottom: 0.25rem !important;
        }
        
        /* Compact Headings */
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3 {
            margin-top: 0.5rem !important;
            margin-bottom: 0.25rem !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            font-size: 1rem !important;
        }
        
        /* Compact Labels */
        section[data-testid="stSidebar"] label {
            margin-bottom: 0.0rem !important;
            font-size: 0.8rem !important;
        }

        /* Compact Inputs */
        section[data-testid="stSidebar"] input {
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
            min-height: 0px !important;
            height: auto !important;
            font-size: 0.8rem !important;
        }
        
        /* Compact Selectbox/NumberInput containers */
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {
            min-height: 28px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }
        
        /* Compact Number Input Buttons */
        section[data-testid="stSidebar"] button[kind="secondary"] {
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            height: 28px !important;
            min-height: 28px !important;
        }

        /* Reduce vertical gap in columns */
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
            gap: 0.25rem !important;
        }
        
        /* Divider spacing */
        section[data-testid="stSidebar"] hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Radio button spacing */
        section[data-testid="stSidebar"] .stRadio > div {
            margin-top: -10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

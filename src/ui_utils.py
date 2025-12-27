import streamlit as st
import subprocess

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

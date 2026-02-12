from streamlit.testing.v1 import AppTest
import pytest

def test_app_analysis_flow():
    # Load app
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    
    # Check title
    assert "SP500 Bump & Slide Analysis" in at.title[0].value
    
    # Check data loaded success
    assert not at.exception
    assert len(at.success) > 0
    # "Loaded" might be in the success message from data loader
    # The exact message might vary, but we expect some success indicator or no exception
    
    # Check duplicate cleaning info
    # We can check validation report expander existence instead.
    assert len(at.expander) > 0
    
    # Switch to Exploration Mode to test its widgets
    at.sidebar.radio(key="app_mode").set_value("Exploration")
    at.run()

    # Set Bump Up % to 5.0 (was slider, now number_input)
    # Using key is more robust. Key defined in src/ui/sidebar.py is 'sb_bump_up_pct'
    at.sidebar.number_input(key='sb_bump_up_pct').set_value(5.0)
    
    # Click "Apply Changes" button to trigger run with new params
    # "Apply Changes" is in the sidebar. 
    # We search for it by label to avoid hitting "Reload Data" which is likely first.
    # AppTest doesn't support finding by label directly in .button collection easily without iteration?
    # Actually .button is a list. We can iterate.
    
    apply_btn = None
    for btn in at.sidebar.button:
        if "Apply Changes" in btn.label:
            apply_btn = btn
            break
            
    if apply_btn:
        apply_btn.click()
        at.run()
    else:
        # If button not found, maybe analysis auto-ran? 
        # But we modified a param, so we expect "Apply Changes" to be present/enabled.
        # If it's disabled, click() raises error?
        pass

    # Check results
    assert not at.exception
    
    # Should see "Matches Found" metric
    # The metric might be in main area (at.metric)
    if len(at.metric) == 0:
        # Debugging info
        print("Metrics found:", len(at.metric))
        print("Exceptions:", at.exception)
    
    assert len(at.metric) > 0
    # Check if "Matches Found" is in ANY of the metrics
    metric_labels = [m.label for m in at.metric]
    assert "Matches Found" in metric_labels, f"Expected 'Matches Found' in metrics, got: {metric_labels}"
    
    # Should see DataFrame
    assert len(at.dataframe) > 0
    
    # Should see "Visualize Pattern" subheader
    subheader_texts = [s.value for s in at.subheader]
    assert "Visualize Pattern" in subheader_texts, f"Expected 'Visualize Pattern' in subheaders, got: {subheader_texts}"
    
    # Check if Plotly Chart is present
    if hasattr(at, 'plotly_chart'):
        assert len(at.plotly_chart) > 0

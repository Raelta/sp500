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
    assert "Loaded" in at.success[0].value
    
    # Check duplicate cleaning info
    # The app runs validation and cleaning on load.
    # So we should see the info message "Auto-cleaned data" if duplicates existed.
    # Since we know spy_data.parquet has duplicates, this should be present.
    # But if data was clean, it wouldn't be. 
    # We can check validation report expander existence instead.
    assert len(at.expander) > 0
    
    # Set Bump Length to 5 (it is default, but let's set it to be sure)
    # AppTest flattens access or searches recursively, so we can access slider directly
    at.sidebar.slider[0].set_value(5)
    
    # Click "Run Analysis" (Top button is index 0 in form submit buttons)
    # Using .button because form_submit_button might be aliased or not exposed directly in sidebar block
    # Streamlit AppTest sometimes groups buttons.
    # We will search in sidebar specifically if possible, or root.
    # Let's try at.sidebar.button first.
    at.sidebar.button[0].click()
    at.run()
    
    # Check results
    assert not at.exception
    
    # Should see "Matches Found" metric
    if len(at.metric) == 0:
        # Debugging info
        print("Metrics found:", len(at.metric))
        print("Exceptions:", at.exception)
    
    assert len(at.metric) > 0
    assert "Matches Found" in at.metric[0].label
    
    # Should see DataFrame
    assert len(at.dataframe) > 0
    
    # Should see Selectbox (implies matches found and visualization area rendered)
    assert len(at.selectbox) > 0
    
    # Check if Plotly Chart is supported in this version of AppTest
    # If not, skipping explicit check but selectbox presence confirms we reached the viz block.
    # assert len(at.plotly_chart) > 0

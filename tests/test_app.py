from streamlit.testing.v1 import AppTest
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

def test_app_analysis_flow():
    # Use patch to replace load_data_cached to avoid timeout and load synthetic data
    with patch("src.data_loader.load_data_cached") as mock_load_data:
        
        # Create a small synthetic dataframe that AppTest can handle quickly
        dates = pd.date_range(start="2020-04-06 09:30:00", periods=100, freq="min")
        dummy_df = pd.DataFrame({
            "date": dates,
            "open": [100.0] * 100,
            "high": [101.0] * 100,
            "low": [99.0] * 100,
            "close": [100.5] * 100,
            "volume": [1000] * 100
        })
        
        dummy_val_report = {
            'duplicates': {'count': 0, 'data': pd.DataFrame()},
            'missing_values': {'count': 0, 'data': pd.DataFrame()},
            'intraday_gaps': {'count': 0, 'data': pd.DataFrame()},
            'missing_minutes': {'count': 0, 'data': pd.DataFrame()}
        }
        
        mock_load_data.return_value = (dummy_df, dummy_val_report)
        
        # Patch find_bumps_and_slides to return dummy data immediately
        # This prevents the test from hanging on heavy computation
        with patch("src.ui.exploration.find_bumps_and_slides") as mock_find:
            # Return valid structure for results
            mock_find.return_value = (pd.DataFrame({
                'date': [pd.Timestamp("2020-04-06 13:53:00")], 
                'close': [100.0],
                'bump_change': [5.0],
                'slide_change': [-5.0],
                'bump_vol': [1000],
                'slide_vol': [1000],
                'bump_up_pct': [5.0],
                'slide_up_pct': [5.0],
                'bump_start_price': [95.0],
                'bump_end_price': [100.0],
                'slide_start_price': [100.0],
                'slide_end_price': [95.0],
                'bump_end_date': [pd.Timestamp("2020-04-06 14:00:00")],
                'slide_end_date': [pd.Timestamp("2020-04-06 14:10:00")],
                'data_gap': [False]
            }), {'total_rows': 100, 'total_bumps': 1, 'hits': 1, 'misses': 0, 'true_hits': 1})

            # Load app
            at = AppTest.from_file("app.py", default_timeout=120)
            
            # Pre-authenticate to bypass login screen
            at.session_state["authenticated"] = True
            at.session_state["username"] = "testuser"
            
            at.run()

            # Handle Help Page if open
            if len(at.header) > 0 and "Help & Information" in at.header[0].value:
                # Find close button
                close_btn = None
                for btn in at.button:
                    if "Close Help" in btn.label:
                        close_btn = btn
                        break
                if close_btn:
                    close_btn.click()
                    at.run()

            # Check data loaded success
            assert not at.exception
            assert len(at.success) > 0
            
            # Check duplicate cleaning info
            # We can check validation report expander existence instead.
            assert len(at.expander) > 0
            
            # Switch to Exploration Mode to test its widgets
            # Navigation is now at top level (not sidebar)
            at.radio(key="app_mode").set_value("Exploration")
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

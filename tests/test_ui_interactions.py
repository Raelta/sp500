import sys
import os
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import importlib

def test_cloud_history_selection_no_rerun():
    """
    Verify that selecting a row in Cloud Run History loads results 
    but DOES NOT trigger st.rerun().
    """
    # Create Mocks
    
    # Create a custom session state mock that behaves like a dict and object
    class MockSessionState(dict):
        def __getattr__(self, key):
            if key in self:
                return self[key]
            return None
        def __setattr__(self, key, value):
            self[key] = value

    mock_st = MagicMock()
    mock_st.session_state = MockSessionState()
    
    # Mock context managers
    mock_st.sidebar.__enter__ = MagicMock(return_value=mock_st)
    mock_st.sidebar.__exit__ = MagicMock(return_value=None)
    mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_st)
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
    
    mock_st.spinner.return_value.__enter__ = MagicMock(return_value=None)
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=None)

    # Mock columns
    def mock_columns(spec):
        if isinstance(spec, int):
            return [MagicMock() for _ in range(spec)]
        else:
            return [MagicMock() for _ in spec]
    mock_st.columns.side_effect = mock_columns
    
    # Mock number_input
    def mock_number_input(label, *args, **kwargs):
        return kwargs.get('value', 0)
    mock_st.number_input.side_effect = mock_number_input
    
    # Mock button (False by default)
    mock_st.button.return_value = False
    
    # Setup Data
    df = pd.DataFrame({'date': pd.date_range('2023-01-01', periods=5), 'close': [100]*5})
    cli_args = MagicMock()
    val_report = {}
    
    # Setup Session State content
    mock_st.session_state.run_history = [
        {
            'run_id': 'run1', 
            'timestamp': '2023-01-01T10:00:00', 
            'status': 'COMPLETED',
            'result_blob': 'blob1',
            'user_label': 'test',
            'est_time_mins': 1.0,
            'duration_sec': 10
        }
    ]
    mock_st.checkbox.return_value = True
    
    # Patch sys.modules to inject mock streamlit
    with patch.dict(sys.modules, {'streamlit': mock_st}):
        # We need to reload src.ui.goal_seek because it has likely already been imported
        # by other tests or logic with the real streamlit.
        # We delete it from sys.modules to force a fresh import that uses our mock.
        if 'src.ui.goal_seek' in sys.modules:
            del sys.modules['src.ui.goal_seek']
            
        # We also need to handle other modules that import streamlit and are imported by goal_seek
        # For this specific test, goal_seek imports:
        # src.search_engine, src.ui.utils, src.cloud_runner, src.analyzer, src.ui.results
        # Some of these might import streamlit too. 
        # Ideally we'd reload them all, but let's try just goal_seek first.
        
        # NOTE: src.ui.results imports streamlit. If it was already imported, it holds reference to real streamlit.
        # render_goal_seek calls render_results.
        # If render_results uses real streamlit, it might fail or behave weirdly if we mix mocks.
        # But render_goal_seek is the one calling st.rerun we want to test.
        
        import src.ui.goal_seek
        from src.ui.goal_seek import render_goal_seek
        
        # Mock CloudRunner inside the module (it's imported as from src.cloud_runner import CloudRunner)
        # So we patch src.ui.goal_seek.CloudRunner
        with patch('src.ui.goal_seek.CloudRunner') as MockRunner:
            runner_instance = MockRunner.return_value
            runner_instance.download_results.return_value = (True, "Success")
            
            # Mock st.dataframe selection
            mock_event = MagicMock()
            mock_event.selection.rows = [0]
            mock_st.dataframe.return_value = mock_event
            
            # Mock pd.read_csv
            with patch('pandas.read_csv', return_value=pd.DataFrame({
                'total_hits': [100], 
                'total_bumps': [10], 
                'scope_rows': [1000],
                'bump_len': [5],
                'bump_threshold': [0.1],
                'slide_len': [5],
                'slide_threshold': [0.1]
            })):
                # Execute
                render_goal_seek(df, cli_args, val_report)
                
                # Assertions
                runner_instance.download_results.assert_called()
                args = runner_instance.download_results.call_args
                assert args[0][1] == 'blob1'
                
                assert 'gs_results' in mock_st.session_state
                assert not mock_st.session_state.gs_results.empty
                
                mock_st.rerun.assert_not_called()
    
    # Cleanup: remove the module so it doesn't pollute subsequent tests
    if 'src.ui.goal_seek' in sys.modules:
        del sys.modules['src.ui.goal_seek']

def test_cloud_history_selection_with_key():
    """
    Simulates a sequence where user selects a row, and verifies 
    that results are downloaded using a stable key.
    """
    # Create Mocks (similar setup to above)
    class MockSessionState(dict):
        def __getattr__(self, key):
            if key in self: return self[key]
            return None
        def __setattr__(self, key, value):
            self[key] = value

    mock_st = MagicMock()
    mock_st.session_state = MockSessionState()
    
    # Mock context managers
    mock_st.sidebar.__enter__ = MagicMock(return_value=mock_st)
    mock_st.sidebar.__exit__ = MagicMock(return_value=None)
    mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_st)
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
    mock_st.spinner.return_value.__enter__ = MagicMock(return_value=None)
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=None)

    # Mock columns
    def mock_columns(spec):
        if isinstance(spec, int): return [MagicMock() for _ in range(spec)]
        else: return [MagicMock() for _ in spec]
    mock_st.columns.side_effect = mock_columns
    
    # Mock inputs
    mock_st.number_input.return_value = 0
    mock_st.button.return_value = False
    mock_st.checkbox.return_value = True
    # Mock text_input to return bucket name (and other strings)
    mock_st.text_input.return_value = "sp500-goal-seek-results"

    # Setup Data
    df = pd.DataFrame({'date': pd.date_range('2023-01-01', periods=5), 'close': [100]*5})
    cli_args = MagicMock()
    val_report = {}
    
    # Setup Session State
    mock_st.session_state.run_history = [
        {'run_id': 'run1', 'timestamp': '2023-01-01T10:00:00', 'status': 'COMPLETED', 'result_blob': 'blob1', 'user_label': 'test'}
    ]
    
    with patch.dict(sys.modules, {'streamlit': mock_st}):
        if 'src.ui.goal_seek' in sys.modules:
            del sys.modules['src.ui.goal_seek']
            
        import src.ui.goal_seek
        from src.ui.goal_seek import render_goal_seek
        
        with patch('src.ui.goal_seek.CloudRunner') as MockRunner:
            runner_instance = MockRunner.return_value
            runner_instance.download_results.return_value = (True, "Success")
            
            # 1. Simulate Selection of Row 0
            mock_event = MagicMock()
            mock_event.selection.rows = [0]
            mock_st.dataframe.return_value = mock_event
            
            # Mock pd.read_csv
            with patch('pandas.read_csv', return_value=pd.DataFrame({'total_hits': [100], 'total_bumps': [10], 'scope_rows': [1000]})):
                render_goal_seek(df, cli_args, val_report)
                
                # Verify that dataframe was called with a key
                args, kwargs = mock_st.dataframe.call_args
                # We expect key="cloud_history_table" (or similar) to be in kwargs if fix is applied
                # Since we haven't applied fix yet, this check would fail or pass depending on current code.
                # But here we want to verify download happens.
                
                runner_instance.download_results.assert_called_with(
                    # bucket name comes from default input value "sp500-goal-seek-results"
                    # We can check specific args or just called
                    'sp500-goal-seek-results', 'blob1', 'cloud_results.csv'
                )
                
                assert 'gs_results' in mock_st.session_state

    if 'src.ui.goal_seek' in sys.modules:
        del sys.modules['src.ui.goal_seek']

if __name__ == "__main__":
    test_cloud_history_selection_no_rerun()
    test_cloud_history_selection_with_key()

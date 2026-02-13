import pytest
from unittest.mock import MagicMock, patch
import sys
import datetime

# Mock modules that depend on streamlit before importing src.ui.auth
# This is necessary because src.ui.auth imports streamlit at the top level
sys.modules["streamlit"] = MagicMock()
sys.modules["extra_streamlit_components"] = MagicMock()

# Now we can import the module under test
from src.ui.auth import _hash_token, check_password, logout

def test_hash_token_consistency():
    """Test that hashing is deterministic."""
    h1 = _hash_token("user1")
    h2 = _hash_token("user1")
    assert h1 == h2
    
def test_hash_token_uniqueness():
    """Test that different inputs produce different hashes."""
    h1 = _hash_token("user1")
    h2 = _hash_token("user2")
    assert h1 != h2

@patch("src.ui.auth.st")
@patch("src.ui.auth.get_manager")
def test_check_password_already_authenticated(mock_get_manager, mock_st):
    """Test that check_password returns True immediately if session state is set."""
    # Setup
    mock_st.session_state = {"authenticated": True}
    
    # Execute
    result = check_password()
    
    # Verify
    assert result is True
    # Should check session state first
    mock_get_manager.assert_called_once()

@patch("src.ui.auth.st")
@patch("src.ui.auth.get_manager")
def test_check_password_cookie_login(mock_get_manager, mock_st):
    """Test that valid cookies trigger auto-login."""
    # Setup
    mock_st.session_state = {}
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    # Mock valid cookie data
    username = "testuser"
    token = _hash_token(username)
    
    # Configure mock behavior for get()
    def get_side_effect(k):
        if k == "sp500_user": return username
        if k == "sp500_token": return token
        return None
    mock_manager.get.side_effect = get_side_effect
    
    # Execute
    result = check_password()
    
    # Verify
    assert result is True
    assert mock_st.session_state["authenticated"] is True
    assert mock_st.session_state["username"] == username

@patch("src.ui.auth.st")
@patch("src.ui.auth.get_manager")
def test_check_password_invalid_cookie(mock_get_manager, mock_st):
    """Test that invalid cookies do NOT trigger auto-login."""
    # Setup
    mock_st.session_state = {}
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    # Mock TAMPERED cookie data
    username = "testuser"
    token = "wrong_token"
    
    mock_manager.get.side_effect = lambda k: username if k == "sp500_user" else (token if k == "sp500_token" else None)
    
    # Execute (should render login form and return False)
    result = check_password()
    
    # Verify
    assert result is False
    assert mock_st.session_state.get("authenticated", False) is False
    mock_st.markdown.assert_called() # "## Login"

@patch("src.ui.auth.st")
@patch("src.ui.auth.get_manager")
def test_logout(mock_get_manager, mock_st):
    """Test logout clears session and cookies."""
    # Setup
    mock_st.session_state = {"authenticated": True, "username": "user"}
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    # Execute
    logout()
    
    # Verify
    assert mock_st.session_state["authenticated"] is False
    assert "username" not in mock_st.session_state
    
    # Verify cookies deleted with keys
    assert mock_manager.delete.call_count == 2
    mock_manager.delete.assert_any_call("sp500_user", key="del_user_cookie")
    mock_manager.delete.assert_any_call("sp500_token", key="del_token_cookie")
    
    mock_st.rerun.assert_called_once()

@patch("src.ui.auth.st")
@patch("src.ui.auth.get_manager")
def test_check_password_form_submit_valid(mock_get_manager, mock_st):
    """Test login form submission with correct password."""
    # Setup
    mock_st.session_state = {}
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    mock_manager.get.return_value = None
    
    # Mock secrets
    mock_st.secrets = {"password": "test_password"}
    
    # Mock inputs
    mock_st.text_input.side_effect = ["testuser", "test_password"] # Username, Password
    mock_st.form_submit_button.return_value = True # Submitted
    
    # Execute
    check_password()
    
    # Verify
    assert mock_st.session_state["authenticated"] is True
    assert mock_st.session_state["username"] == "testuser"
    mock_st.success.assert_called_once()
    mock_manager.set.call_count == 2

@patch("src.ui.auth.st")
@patch("src.ui.auth.get_manager")
def test_check_password_env_var_fallback(mock_get_manager, mock_st):
    """Test login using environment variable when secrets are missing."""
    # Setup
    mock_st.session_state = {}
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    mock_manager.get.return_value = None
    
    # Mock secrets raising KeyError (empty secrets)
    mock_st.secrets = {}
    
    # Mock inputs
    mock_st.text_input.side_effect = ["testuser", "env_password"]
    mock_st.form_submit_button.return_value = True
    
    # Mock environment variable
    import os
    with patch.dict(os.environ, {"APP_PASSWORD": "env_password"}):
        # Execute
        check_password()
    
    # Verify
    assert mock_st.session_state["authenticated"] is True
    mock_st.success.assert_called_once()

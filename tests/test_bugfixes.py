import sys
from unittest.mock import MagicMock

# Mock psutil before importing cloud_job
sys.modules['psutil'] = MagicMock()

import pytest
import json
from src.ui.utils import derive_result_blob_name, get_change_labels
from cloud_job import parse_job_config

def test_derive_result_blob_name():
    # Standard case
    assert derive_result_blob_name("metadata_user_2026.json") == "results_user_2026.csv"
    # Case with underscores in user label
    assert derive_result_blob_name("metadata_my_user_label_123.json") == "results_my_user_label_123.csv"
    # Edge case: what if metadata_ appears twice? (Only first should be replaced)
    assert derive_result_blob_name("metadata_metadata.json") == "results_metadata.csv"

def test_get_change_labels():
    # Value mode
    labels = get_change_labels("value", "value")
    assert labels == ("Bump Change", "Slide Change", "", "")
    
    # Percent mode
    labels = get_change_labels("percent", "percent")
    assert labels == ("Bump Change %", "Slide Change %", "%", "%")
    
    # Mixed
    labels = get_change_labels("percent", "value")
    assert labels == ("Bump Change %", "Slide Change", "%", "")

def test_parse_job_config():
    # Valid config
    config = {"params_grid": {}, "fixed_params": {"bump_thresh_type": "percent"}}
    json_str = json.dumps(config)
    
    # Standard
    assert parse_job_config(json_str) == config
    
    # With gcloud escape prefix
    assert parse_job_config(f"^~^{json_str}") == config
    
    # Invalid/Empty
    assert parse_job_config("") is None
    assert parse_job_config(None) is None

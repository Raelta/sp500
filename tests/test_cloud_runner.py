import pytest
from unittest.mock import patch, MagicMock
from src.cloud_runner import CloudRunner

@patch('src.cloud_runner.run_v2')
@patch('src.cloud_runner.storage')
@patch('src.cloud_runner.google.auth.default')
def test_cloud_runner_get_credentials(mock_auth, mock_storage, mock_run):
    mock_auth.return_value = (MagicMock(), "project-id")
    runner = CloudRunner("test-project")
    creds = runner.get_credentials()
    assert creds is not None
    assert mock_auth.called

@patch('src.cloud_runner.run_v2')
@patch('src.cloud_runner.google.auth.default')
def test_cloud_runner_run_job(mock_auth, mock_run):
    mock_auth.return_value = (MagicMock(), "project-id")
    
    # Mock run_client and operation
    mock_jobs_client = MagicMock()
    mock_run.JobsClient.return_value = mock_jobs_client
    mock_operation = MagicMock()
    mock_jobs_client.run_job.return_value = mock_operation
    
    runner = CloudRunner("test-project")
    
    with patch('src.cloud_runner.st') as mock_st:
        success, msg = runner.run_job("test-job", {"param": "value"})
        
        assert success is True
        assert "submitted" in msg
        mock_jobs_client.run_job.assert_called_once()
        
        # Verify the config was passed as an EnvVar override
        mock_run.RunJobRequest.assert_called_once()
        kwargs = mock_run.RunJobRequest.call_args[1]
        assert kwargs['name'] == "projects/test-project/locations/us-central1/jobs/test-job"
        
@patch('src.cloud_runner.storage')
@patch('src.cloud_runner.google.auth.default')
def test_cloud_runner_download_results(mock_auth, mock_storage):
    mock_auth.return_value = (MagicMock(), "project-id")
    
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    
    mock_storage.Client.return_value = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    runner = CloudRunner("test-project")
    
    success, msg = runner.download_results("test-bucket", "test-blob.json", "/tmp/dest.json")
    
    assert success is True
    mock_client.bucket.assert_called_with("test-bucket")
    mock_bucket.blob.assert_called_with("test-blob.json")
    mock_blob.download_to_filename.assert_called_with("/tmp/dest.json")

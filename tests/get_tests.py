import io
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, UploadFile
from app.app import app
from pytest_mock import MockerFixture
from unittest.mock import patch, MagicMock
from app.s3_config import BUCKET_NAME
from app.models import GetFile

client = TestClient(app)

@patch("app.actions.get_all_files")
def test_get_all_files_success(mock_get_all_files: MagicMock) -> None:
    # Set up the mock to return a list of GetFile objects
    mock_get_all_files.return_value = [
        GetFile(filename="file1.pdf", s3_key="abc123_file1.pdf", url="https://mocked_s3/abc123_file1.pdf"),
        GetFile(filename="file2.docx", s3_key="def456_file2.docx", url="https://mocked_s3/def456_file2.docx")
    ]

    response = client.get("/get_all/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["filename"] == "file1.pdf"
    assert data[0]["s3_key"] == "abc123_file1.pdf"
    assert data[0]["url"] == "https://mocked_s3/abc123_file1.pdf"

    assert data[1]["filename"] == "file2.docx"
    assert data[1]["s3_key"] == "def456_file2.docx"
    assert data[1]["url"] == "https://mocked_s3/def456_file2.docx"

# test for get_all_files with error
@patch("app.actions.get_all_files")
def test_get_all_files_error(mock_get_all_files: MagicMock) -> None:
    mock_get_all_files.side_effect = RuntimeError("S3 service unavailable")

    response = client.get("/get_all/")
    assert response.status_code == 500
    assert "S3 service unavailable" in response.json()["detail"]

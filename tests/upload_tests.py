import io
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, UploadFile
from app.app import app
from app.actions import upload_file
from pytest_mock import MockerFixture
from app.schemas import UploadFileResponse

client = TestClient(app)


def test_upload_success(mocker: MockerFixture) -> None:
    mock_response = UploadFileResponse(filename="test.txt", s3_key="t3stk3y123", url="testurl/aws/blahbahblah")
    
    mocker.patch("app.actions.upload_file", return_value=mock_response)
    
    file_content = b"Test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/upload/", files=files)
    
    assert response.status_code == 200
    assert response.json() == {"filename": "test.txt", "s3_key": "t3stk3y123", "url": "testurl/aws/blahbahblah"}


def test_upload_missing_file() -> None:
    response = client.post("/upload/")
    assert response.status_code == 400
    assert response.json()["detail"] == "File is required."


def test_upload_internal_server_error(mocker: MockerFixture) -> None:
    mocker.patch("app.actions.upload_file", side_effect=Exception("Test server error"))

    file_content = b"Test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/upload/", files=files)

    assert response.status_code == 500
    assert "Test server error" in response.json()["detail"]

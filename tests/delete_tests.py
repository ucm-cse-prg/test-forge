import io
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, UploadFile
from app.app import app
from pytest_mock import MockerFixture

client = TestClient(app)

def test_delete_success(mocker: MockerFixture) -> None:
    # Mock the delete_file function to simulate successful deletion
    mocker.patch("app.api.delete_material", return_value=None)

    # Simulate a delete request

    # this key has to be real for the test to pass btw. 
    s3_key = "017e4175-7016-4fae-9281-3edff1da1f2b_ENGR180 - Lab 5.pdf"
    response = client.delete(f"/delete/{s3_key}")

    assert response.status_code == 200

def test_delete_not_found(mocker: MockerFixture) -> None:
    # Mock the delete_file function to simulate a not found error
    mocker.patch("app.api.delete_material", side_effect=Exception("File not found"))

    # Simulate a delete request
    s3_key = "non_existent_key"
    response = client.delete(f"/delete/{s3_key}")

    # Check the response status code and detail
    assert response.status_code == 500
    assert response.json()["detail"] == "404: File not found"

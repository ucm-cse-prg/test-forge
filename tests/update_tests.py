import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from app.app import app

client = TestClient(app)


def test_update_metadata_success(mocker: MockerFixture) -> None:
    mock_update = mocker.patch("app.actions.update_file_metadata", return_value=None)

    s3_key = "1234_CSE130_Lab2.pdf"
    new_filename = "renamed"

    response = client.patch(f"/update/{s3_key}", json={"new_filename": new_filename})

    assert response.status_code == 200
    assert response.json() == {"detail": "File metadata updated successfully."}
    mock_update.assert_called_once_with(s3_key, new_filename)


def test_update_metadata_not_found(mocker: MockerFixture) -> None:
    from fastapi import HTTPException

    def raise_404(*args: tuple, **kwargs: dict) -> None:
        raise HTTPException(status_code=404, detail="File metadata not found.")

    mocker.patch("app.actions.update_file_metadata", side_effect=raise_404)

    s3_key = "non_existent_key"
    new_filename = "new_file_name"

    response = client.patch(f"/update/{s3_key}", json={"new_filename": new_filename})

    assert response.status_code == 404
    assert response.json()["detail"] == "File metadata not found."


def test_update_metadata_missing_new_filename() -> None:
    s3_key = "some_key"
    response = client.patch(f"/update/{s3_key}", json={"new_filename": ""})

    assert response.status_code == 500
    assert "new_filename is required" in response.json()["detail"]


def test_update_metadata_missing_s3_key() -> None:
    response = client.patch("/update/", json={"new_filename": "something"})
    assert response.status_code == 404 
    
# ---------------------------------------------------------------------------------------
# replace_file tests

def test_replace_file_success(mocker: MockerFixture) -> None:
    mock_replace = mocker.patch("app.actions.replace_file", return_value=None)

    s3_key = "1234_CSE130_Lab2.pdf"
    files = {"file": ("new_file.pdf", b"dummy content", "application/pdf")}

    response = client.patch(f"/replace/{s3_key}", files=files)

    assert response.status_code == 200
    assert response.json() == {"detail": "File replaced successfully."}
    assert mock_replace.call_count == 1
    called_key, called_file = mock_replace.call_args[0]
    assert called_key == s3_key
    assert called_file.filename == "new_file.pdf"


def test_replace_file_not_found(mocker: MockerFixture) -> None:
    from fastapi import HTTPException

    def raise_404(*args: tuple, **kwargs: dict) -> None:
        raise HTTPException(status_code=404, detail="File not found.")

    mocker.patch("app.actions.replace_file", side_effect=raise_404)

    s3_key = "missing_file.pdf"
    files = {"file": ("file.pdf", b"dummy content", "application/pdf")}

    response = client.patch(f"/replace/{s3_key}", files=files)

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found."

def test_replace_file_missing_file() -> None:
    s3_key = "some_file.pdf"

    response = client.patch(f"/replace/{s3_key}")

    assert response.status_code == 422 or response.status_code == 400
    assert "detail" in response.json()

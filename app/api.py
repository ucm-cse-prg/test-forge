# mypy: ignore-errors
import typing
from typing import List, Optional
from functools import wraps
from botocore.exceptions import ClientError

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse

import app.actions as Actions
from app.exceptions import APIException
#from app.schemas import UploadFileResponse, GetFileResponse, UpdateFileRequest
import app.schemas as Schemas

router = APIRouter()


# This decorator is used to handle exceptions that occur in the API endpoints.
@typing.no_type_check
def http_exception(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Try to make the API call and return the result if successful.
            return await func(*args, **kwargs)
        except APIException as e:
            # If an exception occurs, raise an HTTPException with the error code and detail.
            raise HTTPException(status_code=e.code, detail=e.detail)

    return wrapper


@router.get("/")
@http_exception
async def root() -> HTMLResponse:
    content: str = await Actions.home_page()
    return HTMLResponse(
        content=content,
        status_code=200,
    )


@router.post("/upload/")
async def upload_material(file: UploadFile = File(None), uploader_id: Optional[str] = None) -> Schemas.UploadFileResponse:
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")
    try:
        return await Actions.upload_file(file, uploader_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error{str(e)}")


@router.delete("/delete/{s3_key}")
async def delete_material(s3_key: str) -> None:
    try:
        return await Actions.delete_file(s3_key)
    
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=500, detail=f"No file found with key '{s3_key}'")
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_all/", response_model=List[Schemas.GetFileResponse])
async def retrieve_all_files() -> List[Schemas.GetFileResponse]:
    try:
        return await Actions.get_all_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/get_metadata/", response_model=List[Schemas.GetMetaDataResponse])
async def retrieve_all_metadata() -> List[Schemas.GetMetaDataResponse]:
    try:
        return await Actions.get_metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.patch("/update/{s3_key}")
async def update_material(s3_key: str, payload: Schemas.UpdateFileRequest) -> dict:
    try:
        await Actions.update_file_metadata(s3_key, payload.new_filename)
        return {"detail": "File metadata updated successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.patch("/replace/{s3_key}")
async def replace_material(s3_key: str, file: UploadFile = File(None)) -> dict:
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")
    try:
        await Actions.replace_file(s3_key, file)
        return {"detail": "File replaced successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

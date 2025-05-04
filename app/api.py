# mypy: ignore-errors
import typing
from typing import List, Optional
from functools import wraps
from botocore.exceptions import ClientError
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse

import app.actions as Actions
from app.exceptions import APIException
import app.schemas as Schemas
import app.models as Models

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


#-------------------------------------------------------------------------------------------------------------------------
@router.get("/")
@http_exception
async def root() -> HTMLResponse:
    content: str = await Actions.home_page()
    return HTMLResponse(
        content=content,
        status_code=200,
    )


@router.post("/upload/")
@http_exception
async def upload_material(file: UploadFile = File(None), uploader_id: Optional[str] = None, course_id: str = "", visibility: str = 'private', go_public_at: Optional[datetime] = None) -> Schemas.UploadFileResponse:
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")
    
    return await Actions.upload_file(file, course_id, uploader_id, visibility, go_public_at)


@router.delete("/delete/{s3_key}")
@http_exception
async def delete_material(s3_key: str) -> None:
    try:
        return await Actions.delete_file(s3_key)
    
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=500, detail=f"No file found with key '{s3_key}'")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_all/", response_model=List[Schemas.GetFileResponse])
@http_exception
async def retrieve_all_files() -> List[Schemas.GetFileResponse]:
    return await Actions.get_all_files()
    

@router.get("/get_metadata/", response_model=List[Schemas.GetMetaDataResponse])
@http_exception
async def retrieve_all_metadata(user_type: str, course_id: str) -> List[Schemas.GetMetaDataResponse]:
    # this is just here to restrict student type users from accessing private metadata for right now. 
    dummy_user = Models.UserModel(username="dummy", user_type=user_type) # Dummy user for the mock authentication system. 
    return await Actions.get_metadata(dummy_user, course_id)
    

@router.patch("/update/{s3_key}")
@http_exception
async def update_material(s3_key: str, payload: Schemas.UpdateFileRequest) -> dict:
    await Actions.update_file_metadata(s3_key, payload.new_filename)
    return {"detail": "File metadata updated successfully."}
    
    
@router.patch("/replace/{s3_key}")
@http_exception
async def replace_material(s3_key: str, file: UploadFile = File(None)) -> dict:
    if file is None:
        raise HTTPException(status_code=400, detail="File is required.")
    
    await Actions.replace_file(s3_key, file)
    return {"detail": "File replaced successfully."}


#-------------------------------------------------------------------------------------------------------------------------
# Course related endpoints
@router.post("/create_course/", response_model=Schemas.GetCourseResponse)
@http_exception
async def create_course(course: Models.CourseModel) -> Schemas.GetCourseResponse:
    return await Actions.create_course(course)

# basic course retrieval endpoint
@router.get("/get_all_courses", response_model=List[Schemas.GetCourseResponse])
@http_exception
async def get_all_courses() -> List[Schemas.GetCourseResponse]:
    return await Actions.get_all_courses()

# basic course deletion endpoint
@router.delete("/delete_course/{course_id}")
@http_exception
async def delete_course(course_id: str) -> None:
        return await Actions.delete_course(course_id)

# basic course update endpoint
@router.patch("/update_course/{course_id}")
@http_exception
async def update_course(course_id: str, course: Models.CourseModel) -> dict:
    await Actions.update_course(course_id, course)
    return {"detail": "Course updated successfully."}
    
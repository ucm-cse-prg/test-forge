"""
API Request and Response schemas Definitions based on Pydantic Models

These models are used to define the structure of data that is sent and received through the API.
"""
from app.models import FileModel, MetaDataModel, CourseModel
from pydantic import Field, BaseModel
from typing import Optional
from datetime import datetime
from beanie import PydanticObjectId
from bson import ObjectId

class UploadFileResponse(FileModel):
    course_id: str = Field(default="")
    s3_key: str = Field(default="")
    visibility: Optional[str] = Field(default="private")
    go_public_at: Optional[datetime] = None

class GetFileResponse(FileModel):
    pass

class UpdateFileRequest(BaseModel):
    new_filename: str = Field(default="")

class GetMetaDataResponse(MetaDataModel):
    pass

class CreateCourseRequest(CourseModel):
    pass

class GetCourseResponse(CourseModel):
    id: Optional[PydanticObjectId] = Field(alias="_id")
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            PydanticObjectId: str
        }
        arbitrary_types_allowed = True

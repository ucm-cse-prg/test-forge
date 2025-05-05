"""
Data Models based on Pydantic Models

These Models form the backbone of the application, providing a way to validate and serialize data.
Request/response schemas as well as database documents are derived from these models.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from beanie import PydanticObjectId
from bson import ObjectId


class CourseModel(BaseModel):
    course_id: str = Field(max_length=10) # going to make the course id the foreign key for Files. 
    course_name: str = Field(max_length=200)
    course_description: Optional[str] = Field(max_length=200)
    visibility: str = Field(default='public')
    collaborators: list[str] = Field(default_factory=list)
    creator_id: Optional[str] = Field(default="")
    date_created: datetime = Field(default_factory=datetime.now)

    @field_validator("course_id")
    @classmethod
    def check_id_length(cls, v: str) -> str:
        if len(v) > 10:
            raise ValueError("Course ID must be less than 10 characters") # assuming course id would be something like "CSE195"
        return v
    
    class Config:
        populate_by_name = True # this is to allow the use of alias in the model
        json_encoders = {
            ObjectId: str,
            PydanticObjectId: str
        }
        arbitrary_types_allowed = True


class FileModel(BaseModel):
    course_id: str = Field(max_length=200)
    filename: Optional[str] = Field(max_length=300)
    s3_key: str = Field()
    url: str = ""

    @field_validator("filename")
    @classmethod
    def check_name_length(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("Filename must be less than 300 characters")
        return v


class MetaDataModel(BaseModel):
    course_id: str = Field(max_length=200) # the foreign key for the course the file belongs to
    filename: Optional[str] = Field(max_length=300)
    s3_key: str = Field(default="")
    url: str = "" 
    uploaded_at: Optional[datetime] = Field(default_factory=datetime.now)
    content_type: Optional[str] = Field(default="")
    file_size: Optional[int] = Field(default=0)
    uploader_id: Optional[str] = None
    visibility: Optional[str] = Field(default="private")
    go_public_at: Optional[datetime] = Field(default=None)


# --------------------------------------------------------------------------------------------------------------------------------
# placeholder User model that will allow me to make a super barebones "authentication" system. 
class UserModel(BaseModel):
    username: str = Field(max_length=50)
    user_type: Literal["student", "professor", "admin"] = Field(default="student") # using Literal to restrict user_type to specific values

# --------------------------------------------------------------------------------------------------------------------------------




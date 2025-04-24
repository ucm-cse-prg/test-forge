"""
Data Models based on Pydantic Models

These Models form the backbone of the application, providing a way to validate and serialize data.
Request/response schemas as well as database documents are derived from these models.
"""
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    filename: str = Field(default="")
    s3_key: str
    url: str 

class GetFile(BaseModel):
    filename: str = Field(default="")
    s3_key: str = Field(default="")
    url: str

class UpdateRequest(BaseModel):
    new_filename: str = Field(default="")

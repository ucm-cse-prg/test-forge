"""
Data Models based on Pydantic Models

These Models form the backbone of the application, providing a way to validate and serialize data.
Request/response schemas as well as database documents are derived from these models.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class FileModel(BaseModel):
    filename: Optional[str] = Field(max_length=50)
    s3_key: str = Field()
    url: str = ""

    @field_validator("filename")
    @classmethod
    def check_name_length(cls, v: str) -> str:
        if len(v) > 50:
            raise ValueError("Filename must be less than 50 characters")
        return v


class MetaDataModel(BaseModel):
    filename: Optional[str] = Field(max_length=50)
    s3_key: str = Field(default="")
    uploaded_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    content_type: Optional[str] = Field(default="")
    file_size: Optional[int] = Field(default=0)
    uploader_id: Optional[str] = None


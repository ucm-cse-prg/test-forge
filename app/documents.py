"""
Database document models for Beanie ODM with MongoDB.
"""

from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Define Beanie document models that represent your MongoDB collections.
# Use Beanie's Document base class combined with Pydantic models

"""
defining the structure for uploading the file metadata to the mongo db. All metadata is associated with a file in the s3 bucket.
When someone needs to access the file, the get_all function generates a presigned url that expires in an hour, so that is not stored with the rest
of the metadata. 
"""
class FileMetaData(Document):
    filename: str = Field(default="")
    s3_key: str = Field(default="")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    content_type: str = Field(default="")
    file_size: int = Field(default=0) # filesize will be retrieved as bytes (ex. 120kB = 120000 bytes)
    uploader_id: Optional[str] = None

    class Settings: 
        collection = "file_metadata"


# this line is critical for Beanie to recognize the document models.
# add any additional documents to the list, ex [FileMetaData, AnotherDocument, ...]
DOCUMENTS: list[type[Document]] = [FileMetaData]

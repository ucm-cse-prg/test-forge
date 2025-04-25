"""
Database document models for Beanie ODM with MongoDB.
"""

from beanie import Document
from app.models import MetaDataModel

# Define Beanie document models that represent your MongoDB collections.
# Use Beanie's Document base class combined with Pydantic models

"""
defining the structure for uploading the file metadata to the mongo db. All metadata is associated with a file in the s3 bucket.
When someone needs to access the file, the get_all function generates a presigned url that expires in an hour, so that is not stored with the rest
of the metadata. 
"""

class FileMetaData(Document, MetaDataModel):
    class Settings:
        collection = "file_metadata"


# this line is critical for Beanie to recognize the document models.
# add any additional documents to the list, ex [FileMetaData, AnotherDocument, ...]
DOCUMENTS: list[type[Document]] = [FileMetaData]

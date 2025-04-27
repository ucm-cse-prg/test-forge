"""
Database document models for Beanie ODM with MongoDB.
"""

from beanie import Document
from app.models import MetaDataModel, CourseModel

# Define Beanie document models that represent your MongoDB collections.
# Use Beanie's Document base class combined with Pydantic models

"""
defining the structure for uploading the file metadata to the mongo db. All metadata is associated with a file in the s3 bucket.
When someone needs to access the file, the get_all function generates a presigned url that expires in an hour, so that is not stored with the rest
of the metadata. 
"""

class FileMetaData(Document, MetaDataModel): #inheriting from the MetaDataModel
    class Settings:
        collection = "file_metadata"


class Course(Document, CourseModel): # inheriting from the CourseModel
    class Settings:
        collection = "courses"


# this line is critical for Beanie to recognize the document models.
# add any additional documents to the list, ex [FileMetaData, AnotherDocument, ...]
DOCUMENTS: list[type[Document]] = [FileMetaData, Course]

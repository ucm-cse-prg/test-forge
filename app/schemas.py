"""
API Request and Response schemas Definitions based on Pydantic Models

These models are used to define the structure of data that is sent and received through the API.
"""
from app.models import FileModel, MetaDataModel
from pydantic import Field, BaseModel

class UploadFileResponse(FileModel):
    s3_key: str = Field(default="")

class GetFileResponse(FileModel):
    pass

class UpdateFileRequest(BaseModel):
    new_filename: str = Field(default="")

class GetMetaDataResponse(MetaDataModel):
    pass

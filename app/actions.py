"""
Actions for handling the internal logic of API endpoints.
"""

import typing
from typing import List, Optional
from functools import wraps
from importlib.metadata import metadata
from fastapi import UploadFile, HTTPException, Query
from botocore.exceptions import ClientError
import uuid

from app.exceptions import InternalServerError
# from app.models import UploadResponse, GetFile
from app.models import FileModel
from app.schemas import UploadFileResponse, GetFileResponse
from app.s3_config import s3_client, BUCKET_NAME
from app.documents import FileMetaData

PROJECT_METADATA = metadata("fastapi-app")

# Wrapper function to run action and rais InternalServerError if it fails
@typing.no_type_check
def run_action(action):
    @wraps(action)
    async def wrapper(*args, **kwargs):
        try:
            # Call the wrapped function with provided arguments.
            return await action(*args, **kwargs)
        except Exception as e:
            # Convert APIException into HTTPException with corresponding code and message.
            raise InternalServerError(str(e))

    return wrapper


# Example usage of the run_action decorator
@run_action
async def home_page() -> str:
    # Get project metadata
    project_name = PROJECT_METADATA["Name"]
    project_version = PROJECT_METADATA["Version"]
    project_description = PROJECT_METADATA["Summary"]

    # Generate mockup HTML content for the home page
    content = f"""
        <html>
            <head>
                <title>{project_name}</title>
            </head>
            <body>
                <h1>Welcome to the {project_name}</h1>
                <p>{project_description}</p>
                <footer>
                    <p>version {project_version}</p>
                </footer>
            </body>
        </html>
        """

    # Uncomment the following line to raise an exception for testing purposes
    # raise Exception("This is a test exception")

    return content

@run_action
async def upload_metadata(file: UploadFile, file_key: str, content_type: Optional[str] = None, file_size: Optional[int] = 0, uploader_id: Optional[str] = None) -> None:
    file_metadata = FileModel(
        filename=file.filename,
        s3_key=file_key,
        url=s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': file_key},
        ExpiresIn=3600  # URL expiration time in seconds
    ),)
    
    # metadata: FileMetaData = await FileMetaData(
    #         filename=file.filename,
    #         s3_key=file_key,
    #         content_type=content_type,
    #         file_size=file_size,
    #         uploader_id=uploader_id,
    #     ).insert()
    metadata = await FileMetaData(
        filename=file_metadata.filename, # errors come up if i dont include the "or unknown" part. 
        s3_key=file_metadata.s3_key,
        content_type=content_type,
        file_size=file.size,
        uploader_id=uploader_id,
    ).insert()
 
    if not metadata:
        raise HTTPException(status_code=500, detail="Failed to save metadata to MongoDB.")
    
@run_action
async def delete_metadata(s3_key: str) -> None:
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required.")
    
    metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if metadata:
        await metadata.delete()
    else:
        raise HTTPException(status_code=404, detail="Metadata not found.")


@run_action
# making this function in case we need it, not quite sure where it would fit in as of right now
async def get_metadata() -> List[FileMetaData]: 
        metadata = await FileMetaData.find_all().to_list()
        return metadata


@run_action
async def upload_file(file: UploadFile, uploader_id: Optional[str] = None) -> UploadFileResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    file_key = f"{uuid.uuid4()}_{file.filename}" # this is the unique file key that will be used for other operations like deletion.
    # uuid is a unique identifier that pretty much acts as the file id in the s3 bucket.
    # this prevents even files with the exact same name from having the same unique identifier. 

    # getting the content type and the file size for the metadata. 
    content_type = file.content_type

    file.file.seek(0, 2)
    file_size = file.file.tell()  # move the file pointer to the end of the file to get the size
    file.file.seek(0)

    s3_client.upload_fileobj(file.file, BUCKET_NAME, file_key)

    # file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"
    # generating a presigned url to give access to the the private file as opposed to the public bucket url above.

    # Currently, the presigned url cannot be followed. I think that this is bc the rook ceph stuff is only accessible within the cluster.
    # I think that bc im developing locally, my system doesnt know how to follow the endpoint url given to me or something. 
    file_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': file_key},
        ExpiresIn=3600  # URL expiration time in seconds
    )

    await upload_metadata(file, file_key, content_type, file_size , uploader_id) # saving the metadata to the mongo db.

    return UploadFileResponse(filename=file.filename, s3_key=file_key, url=file_url)

    
# delete_file requries the s3_key associated with the file to be deleted. 
@run_action
async def delete_file(s3_key: str = Query(default=None, description='The s3 key given to the uploaded file when uploading')) -> None:
    if s3_key is None:
        raise HTTPException(status_code=400, detail="The 's3_key' query parameter is required.")
    
    try:
        # first you gotta check if the file exists before deleting it. 
        s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # if it doesnt, raise a 404 error. 
            raise HTTPException(status_code=404, detail="File not found")
        else:
            raise
        
    # if it does, then go ahead. 
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
    await delete_metadata(s3_key) # deleting the associated metadata from the mongo db.
    

@run_action
async def get_all_files() -> List[GetFileResponse]:
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    contents = response.get("Contents", [])

    files = [] 
    for obj in contents:
        s3_key = obj["Key"]
        filename = "_".join(s3_key.split("_")[1:]) # removing the uuid part of the filename 
            
        # Commented code below is for public urls, will delete when i have access to the kubernetes cluster. 
        # file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600  # URL expiration time in seconds
        )

        files.append(GetFileResponse(filename=filename, s3_key=s3_key, url=file_url))

    return files


@run_action
async def update_file_metadata(s3_key: str, new_filename: str) -> None:
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required.")
    if not new_filename:
        raise HTTPException(status_code=400, detail="new_filename is required.")
    
    existing_metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if not existing_metadata:
        raise HTTPException(status_code=404, detail="File metadata not found.")
    
    if not existing_metadata.filename:
        raise HTTPException(status_code=400, detail="Filename is missing in the metadata.")
    
    old_extension = existing_metadata.filename.split(".")[-1] # extracting the old extension
        
    uuid_part = s3_key.split("_")[0]# extracting the uuid of the s3 key 
        
    new_s3_key = f"{uuid_part}_{new_filename}.{old_extension}" # concatenating the old uuid with the new file name and old extension
        
    # copying the object in s3
    s3_client.copy_object(
        Bucket=BUCKET_NAME,
        CopySource={'Bucket': BUCKET_NAME, 'Key': s3_key},
        Key=new_s3_key
    )
        
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key) # deleting the old version
        
    # updating the metadata associated with the file 
    existing_metadata.filename = new_filename
    existing_metadata.s3_key = new_s3_key
    await existing_metadata.save()
    

@run_action
async def replace_file(s3_key: str, new_file: UploadFile) -> None:
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required.")
    if not new_file:
        raise HTTPException(status_code=400, detail="new_file is required.")
    
    s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key) # making sure the file exists
        
    # recalculating the file size
    new_file.file.seek(0, 2)
    new_file_size = new_file.file.tell()
    new_file.file.seek(0)

    s3_client.upload_fileobj(new_file.file, BUCKET_NAME, s3_key) # uploading with the same key
        
    # updating the metadata associated with the file
    existing_metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if existing_metadata:
        existing_metadata.filename = new_file.filename
        existing_metadata.content_type = new_file.content_type
        existing_metadata.file_size = new_file_size
        await existing_metadata.save()
    else:
        raise HTTPException(status_code=404, detail="File metadata not found.")

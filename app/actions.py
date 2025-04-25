"""
Actions for handling the internal logic of API endpoints.
"""




import typing
from typing import List, Optional
from functools import wraps
from importlib.metadata import metadata
from fastapi import UploadFile, File, HTTPException, Query, Body
from botocore.exceptions import BotoCoreError, ClientError
import uuid
import asyncio

from app.exceptions import InternalServerError
from app.models import UploadResponse, GetFile
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


async def upload_metadata(file: UploadFile, file_key: str, content_type: Optional[str] = None, file_size: Optional[int] = 0, uploader_id: Optional[str] = None) -> None:
    metadata: FileMetaData = await FileMetaData(
            filename=file.filename,
            s3_key=file_key,
            content_type=content_type,
            file_size=file_size,
            uploader_id=uploader_id,
        ).insert()
 
    if not metadata:
        raise HTTPException(status_code=500, detail="Failed to save metadata to MongoDB.")
    

async def delete_metadata(s3_key: str) -> None:
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required.")
    
    metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if metadata:
        await metadata.delete()
    else:
        raise HTTPException(status_code=404, detail="Metadata not found.")


# making this function in case we need it, not quite sure where it would fit in as of right now
async def get_metadata() -> List[FileMetaData]:
    try: 
        metadata = await FileMetaData.find_all().to_list()
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# this will be changed when the MinIO server is up and running. 
async def upload_file(file: UploadFile, uploader_id: Optional[str] = None) -> UploadResponse:
    try:
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

        return UploadResponse(filename=file.filename, s3_key=file_key, url=file_url)

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# delete_file requries the s3_key associated with the file to be deleted. 
async def delete_file(s3_key: str = Query(default=None, description='The s3 key given to the uploaded file when uploading')) -> None:
    if s3_key is None:
        raise HTTPException(status_code=400, detail="The 's3_key' query parameter is required.")
    
    try:
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
    
    except (BotoCoreError, ClientError) as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=str(e))
        raise
    
    
async def get_all_files() -> List[GetFile]:
    try:
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

            files.append(GetFile(filename=filename, s3_key=s3_key, url=file_url))

        return files

    except Exception as e:
        raise RuntimeError(f"Failed to list S3 bucket contents: {str(e)}")

"""
So, S3 doesnt really support directly updating files (like changing a file name, etc).
Therefore, to "update" a file, it would have to pretty much be copied to a new s3 key, with a new name, and then the old one would be deleted.

Likewise, I could store the metadata somewhere else, like in the mongo and have the metadata be associated to the path of the actual file in the S3 bucket.
Then, when someone wants to update the file metadata, that could be changed while still keeping the same file in the s3 bucket. 

"""

# idea: Each piece of metadata has an associated s3 key, each with its own unique identifer (uuid). 
# when a file needs to be updated with new metadata and or content, we would use the uuid of the file of interest, 
# then, when it gets reuploaded to the s3 bucket, the old version will be overwritten, effectively updating the file without interrupting the LLM's process. 

async def update_file_metadata(s3_key: str, new_filename: str) -> None:
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required.")
    if not new_filename:
        raise HTTPException(status_code=400, detail="new_filename is required.")
    
    existing_metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if not existing_metadata:
        raise HTTPException(status_code=404, detail="File metadata not found.")
    
    try:
        
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
        
    except (BotoCoreError, ClientError) as s3_error:
        raise HTTPException(status_code=500, detail=f"S3 error: {str(s3_error)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")
    

async def replace_file(s3_key: str, new_file: UploadFile) -> None:
    if not s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required.")
    if not new_file:
        raise HTTPException(status_code=400, detail="new_file is required.")
    
    try:
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
        
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

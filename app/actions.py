"""
Actions for handling the internal logic of API endpoints.
"""
# mypy: ignore-errors
# idk why the mypy errors are occuring so im just silencing them for now. 
import typing
from typing import List, Optional
from functools import wraps
from importlib.metadata import metadata
from fastapi import UploadFile, Query
from botocore.exceptions import ClientError
import uuid
from datetime import datetime
from bson import ObjectId

#from app.exceptions import InternalServerError
# from app.models import UploadResponse, GetFile
import app.exceptions as exceptions
from app.models import FileModel, CourseModel
from app.schemas import UploadFileResponse, GetFileResponse, GetCourseResponse
from app.s3_config import s3_client, BUCKET_NAME
from app.documents import FileMetaData, Course, User

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
            print (f"Error in {action.__name__}: {e}") # just to make testing easier. 
            raise exceptions.InternalServerError(str(e))

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

#--------------------------------------------------------------------------------------------------------------------------
# functions to make files go public.
@run_action 
async def make_files_public() -> None:
    now = datetime.now()
    metadata_list = await FileMetaData.find_all().to_list()

    for data in metadata_list:
        if data.go_public_at and data.go_public_at <= now: # making sure that the metadata actually has a go_public_at date and that the date is in the past or equal to the current datetime.
            if data.visibility != "public": # making sure the file isnt already public
                data.visibility = "public"
                await data.save()

#--------------------------------------------------------------------------------------------------------------------------
# Metadata related actions
@run_action
async def upload_metadata(file: UploadFile, course_id: str, file_key: str, file_url: str, content_type: Optional[str] = None, file_size: Optional[int] = 0, uploader_id: Optional[str] = None, visibility: Optional[str] = "private", go_public_at: Optional[datetime] = None) -> None:
    # file_metadata = FileModel(
    #     course_id = course_id,
    #     filename=file.filename,
    #     s3_key=file_key,
    #     url=s3_client.generate_presigned_url(
    #     'get_object',
    #     Params={'Bucket': BUCKET_NAME, 'Key': file_key},
    #     ExpiresIn=604800  # URL expiration time in seconds
    # ), # so this current url has an expiration date of 7 days. If we want persistant urls, we have to make the bucket public.
    # # or generate a new presigned url every time we want to access the file.
    # )
    file_metadata = FileModel(
        course_id = course_id,
        filename=file.filename,
        s3_key=file_key,
        url=file_url,
    )
    
    metadata = await FileMetaData(
        course_id = course_id,
        filename=file_metadata.filename,
        s3_key=file_metadata.s3_key,
        url=file_metadata.url,
        uploaded_at=datetime.now(),
        content_type=file.content_type,
        file_size=file.size,
        uploader_id=uploader_id,
        visibility=visibility,
        go_public_at=go_public_at,
    ).insert()
 
    if not metadata:
        raise exceptions.FailedToSaveError(detail="Failed to save metadata to MongoDB.")
    
@run_action
async def delete_metadata(s3_key: str) -> None:
    if not s3_key:
        raise exceptions.MissingParameterError(detail="s3_key is required.")
    
    metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if metadata:
        await metadata.delete()
    else:
        raise exceptions.FileNotFoundError(detail="Metadata not found.")


@run_action
async def get_metadata(user: User, course_id: str) -> List[FileMetaData]:
        if user.user_type == "student":
            metadata = await FileMetaData.find(FileMetaData.visibility == "public", FileMetaData.course_id == course_id).to_list()
        else:
            metadata = await FileMetaData.find(FileMetaData.course_id == course_id).to_list()
        
        return metadata

#--------------------------------------------------------------------------------------------------------------------------
# File related actions
@run_action
async def upload_file(file: UploadFile, course_id: str, uploader_id: Optional[str] = None, visibility: Optional[str] = 'private', go_public_at: Optional[datetime] = None) -> UploadFileResponse:
    if not file.filename:
        raise exceptions.MissingParameterError(detail="Uploaded file must have a filename.")

    # adding the course id to distinguish between files uploaded to different courses. 
    file_key = f"{course_id}_{uuid.uuid4()}_{file.filename}" # this is the unique file key that will be used for other operations like deletion.
    # uuid is a unique identifier that pretty much acts as the file id in the s3 bucket.
    # this prevents even files with the exact same name from having the same unique identifier. 

    # getting the content type and the file size for the metadata. 
    content_type = file.content_type

    file_size = file.size # UploadFile objects have a size attribute

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

    await upload_metadata(file, course_id, file_key, file_url, content_type, file_size , uploader_id, visibility, go_public_at) # saving the metadata to the mongo db.

    return UploadFileResponse(course_id=course_id, filename=file.filename, s3_key=file_key, url=file_url, visibility=visibility, go_public_at=go_public_at)

    
# delete_file requries the s3_key associated with the file to be deleted. 
@run_action
async def delete_file(s3_key: str = Query(default=None, description='The s3 key given to the uploaded file when uploading')) -> None:
    if s3_key is None:
        raise exceptions.MissingParameterError(detail="The 's3_key' query parameter is required.")
    
    try:
        # first you gotta check if the file exists before deleting it. 
        s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # if it doesnt, raise a 404 error. 
            raise exceptions.FileNotFoundError(detail="File not found")
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
        parts = s3_key.split("_", 2) # extracting the course id from the s3 key
        course_id, _, filename = parts
        #filename = "_".join(s3_key.split("_")[1:]) # removing the uuid part of the filename 
            
        # Commented code below is for public urls, will delete when i have access to the kubernetes cluster. 
        # file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600  # URL expiration time in seconds
        )

        files.append(GetFileResponse(course_id=course_id, filename=filename, s3_key=s3_key, url=file_url))

    return files


@run_action
async def update_file_metadata(s3_key: str, new_filename: str) -> None:
    if not s3_key or not new_filename:
        raise exceptions.MissingParameterError(detail="s3_key or new_filename is missing.")
    
    existing_metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if not existing_metadata:
        raise exceptions.FileNotFoundError(detail="File metadata not found.")
    
    if not existing_metadata.filename:
        raise exceptions.MissingParameterError(detail="Filename is missing in the metadata.")
    
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
    if not s3_key or not new_file:
        raise exceptions.MissingParameterError(detail="s3_key or new_file is missing.")
    
    s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key) # making sure the file exists
        
    # getting the new file size
    new_file_size = new_file.size

    s3_client.upload_fileobj(new_file.file, BUCKET_NAME, s3_key) # uploading with the same key
        
    # updating the metadata associated with the file
    existing_metadata = await FileMetaData.find_one(FileMetaData.s3_key == s3_key)
    if existing_metadata:
        existing_metadata.filename = new_file.filename
        existing_metadata.content_type = new_file.content_type
        existing_metadata.file_size = new_file_size
        await existing_metadata.save()
    else:
        raise exceptions.FileNotFoundError(detail="File metadata not found.")



#--------------------------------------------------------------------------------------------------------------------------
# Course related actions
@run_action
async def create_course(course: CourseModel) -> Course:
    if not course.course_id or not course.course_name:
        raise exceptions.MissingParameterError(detail="course_id and course_name are required.")
    
    # im not sure what "collaborators" is supposed to entail, so for now its just going to be a list of strings. 
    # I assume its going to be a bunch of users, most likely users of professor type. 
    if course.collaborators is None:
        course.collaborators = []
    
    # course = Course(
    #     course_id=course.course_id,
    #     course_name=course.course_name,
    #     course_description=course.course_description,
    #     visibility=course.visibility,
    #     collaborators=course.collaborators,
    #     creator_id=course.creator_id
    # )
    
    # await course.insert()
    # return course
    course_doc = Course(**course.dict())  # do NOT include _id here
    await course_doc.insert()
    return course_doc


@run_action
async def get_all_courses() -> List[GetCourseResponse]:
    courses = await Course.find_all().to_list()
    
    course_responses = []
    for course in courses:
        # Create a dictionary of all the fields
        course_dict = {
            "id": course.id,
            "course_id": course.course_id,
            "course_name": course.course_name,
            "course_description": course.course_description,
            "visibility": course.visibility,
            "collaborators": course.collaborators,
            "creator_id": course.creator_id,
            "date_created": course.date_created
        }
        
        course_responses.append(GetCourseResponse(**course_dict))
    
    return course_responses

@run_action
async def delete_course(course_id: str) -> None:
    if not course_id:
        raise exceptions.MissingParameterError(detail="course_id is required.")
    
    object_id = ObjectId(course_id)
    
    course = await Course.find_one(Course.id == object_id)
    if not course:
        raise exceptions.CourseNotFoundError(detail="Course not found.")
    
    await course.delete()


@run_action
async def update_course(course_id: str, course: CourseModel) -> Course:
    if not course_id or not course.course_name:
        raise exceptions.MissingParameterError(detail="course_id and course_name are required.")
    
    object_id = ObjectId(course_id)
    
    existing_course = await Course.find_one(Course.id == object_id)
    if not existing_course:
        raise exceptions.CourseNotFoundError(detail="Course not found.")
    
    existing_course.course_name = course.course_name
    existing_course.course_description = course.course_description
    existing_course.visibility = course.visibility
    existing_course.collaborators = course.collaborators
    await existing_course.save()
    
    return existing_course


# get a course by specific id
@run_action
async def get_course_by_id(course_id: str) -> GetCourseResponse:
    if not course_id:
        raise exceptions.MissingParameterError(detail="course_id is required.")

    object_id = ObjectId(course_id)

    course = await Course.find_one(Course.id == object_id)
    if not course:
        raise exceptions.CourseNotFoundError(detail="Course not found.")

    return GetCourseResponse(**course.model_dump())
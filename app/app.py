"""
This is the main application file for the FastAPI application.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

# -------------------------------------------------
# scheduler related imports 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger # for testing. Makes the scheduler run in intervals instead of at a specific time.
from app.actions import make_files_public
# -------------------------------------------------

from app.api import router
from app.config import get_settings
from app.mongo import close_mongo, init_mongo, check_mongo_connection

# Load application settings from environment or configuration.
SETTINGS = get_settings()


# Function to run on application startup.
async def startup() -> None:
    """
    Startup function to initialize the application.

    This function is called when the FastAPI application starts up.
    It initializes the MongoDB connection and sets up Beanie ODM.
    """
    #await check_mongo_connection()
    await init_mongo()
    # Additional startup logic can be added here.


# Function run on application shutdown.
async def shutdown() -> None:
    """
    Shutdown function to clean up resources.

    This function is called when the FastAPI application shuts down.
    It closes the MongoDB connection and performs any necessary cleanup.
    """
    await close_mongo()
    # Additional shutdown logic can be added here.


# Lifespan context manager for FastAPI application.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager for FastAPI.

    This context manager handles startup and shutdown events for the application.
    On startup, it connects to MongoDB by calling init_mongo().
    On shutdown, any required cleanup logic (e.g., closing database connections)
    can be added here.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control is yielded back after startup actions.
    """
    await startup()  # Connect to MongoDB during app startup

    scheduler = AsyncIOScheduler() # scheduler so that we can automatically make files public when their make_public time is reached. 
    
    # adding the job to the scheduler. 
    scheduler.add_job(
        make_files_public,
        CronTrigger(hour=0, minute=0), # making the scheduled function run every day at midnight. This can be changed to run on intervals instead of a set time. 
        id="make_files_public_job"
    )


    scheduler.start()  # Start the scheduler
    print("Scheduler has been started.")

    yield  # Yield control back to the application

    await shutdown()  # Perform cleanup actions on app shutdown
    scheduler.shutdown()
    print("Scheduler has been shutdown.")


# Create a FastAPI application instance, using the custom lifespan context manager.
app = FastAPI(lifespan=lifespan)

# Include API routes
app.include_router(router)

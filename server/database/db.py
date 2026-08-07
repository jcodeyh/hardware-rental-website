import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import Config

logger = logging.getLogger(__name__)

DATABASE_URL = Config().database_url
DATABASE_USERNAME = Config().database_username
DATABASE_PASSWORD = Config().database_password

URL = f"mongodb+srv://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_URL}"

client = MongoClient(URL)  # Connect to MongoDB using the constructed URL

db = client[Config().database_name]

def init_indexes():
    try:
        db.users.create_index("username", unique=True)
        db.projects.create_index("projectId", unique=True)
        db.hardware.create_index("hwName", unique=True)
    except PyMongoError:
        logger.exception("Could not create indexes")
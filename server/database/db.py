from pymongo import MongoClient
from config import Config

DATABASE_URL = Config().database_url
DATABASE_USERNAME = Config().database_username
DATABASE_PASSWORD = Config().database_password

URL = f"mongodb+srv://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_URL}"

client = MongoClient(URL)  # Connect to MongoDB using the constructed URL

db = client[Config().database_name]

def init_indexes():
    db.users.create_index("username", unique=True)
from dotenv import load_dotenv
from os import getenv

class Config:
    def __init__(self):
        load_dotenv()  # Load environment variables
        self.database_url = getenv('DATABASE_URL')  # Get the database URL
        self.database_username = getenv('DATABASE_USERNAME')  # Get the database username
        self.database_password = getenv('DATABASE_PASSWORD')  # Get the database password
        self.database_name = getenv('DATABASE_NAME')  # Get the database name
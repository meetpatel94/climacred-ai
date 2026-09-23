import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import mongomock
from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_db = None
_is_mock = False

def get_mongo_client():
    global _client, _is_mock
    if _client is not None:
        return _client
    try:
        client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
        # Try to ping
        client.admin.command('ping')
        logger.info(f"Connected to MongoDB at {settings.MONGODB_URI}")
        _client = client
        _is_mock = False
    except Exception as e:
        logger.warning(f"MongoDB connection failed ({e}), falling back to mongomock in-memory DB. Data will not persist across restarts without real MongoDB.")
        _client = mongomock.MongoClient()
        _is_mock = True
    return _client

def get_database():
    global _db
    if _db is not None:
        return _db
    client = get_mongo_client()
    _db = client[settings.MONGODB_DATABASE]
    return _db

def is_mock_db() -> bool:
    # Ensure client initialized
    get_mongo_client()
    return _is_mock

def get_collection(name: str):
    db = get_database()
    return db[name]

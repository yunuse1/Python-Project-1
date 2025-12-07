import os
import time
import logging
import pymongo
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

logger = logging.getLogger(__name__)


DEFAULT_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DEFAULT_DB = os.getenv("MONGO_DB", "mydatabase")
DEFAULT_COLLECTION = os.getenv("MONGO_COLLECTION", "customers")
DEFAULT_TIMEOUT_MS = 5000

def get_client(uri: str | None = None, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> pymongo.MongoClient:
	"""
	Return a connected MongoClient. Raises ConnectionError on failure.
	"""
	uri = uri or DEFAULT_URI
	client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
	try:
		client.admin.command("ping")
	except (ServerSelectionTimeoutError, ConnectionFailure) as e:
		raise ConnectionError(f"Could not connect to MongoDB at {uri}: {e}")
	return client

def get_db(db_name: str = DEFAULT_DB, client: pymongo.MongoClient | None = None) -> pymongo.database.Database:
	"""
	Return a Database object.
	"""
	client = client or get_client()
	return client[db_name]

def get_collection(db_name: str = DEFAULT_DB, collection_name: str = DEFAULT_COLLECTION, client: pymongo.MongoClient | None = None) -> pymongo.collection.Collection:
	"""
	Return a Collection object.
	"""
	db = get_db(db_name, client)
	return db[collection_name]

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
	
	max_retries = int(os.environ.get("MONGO_CONNECT_RETRIES", "12"))
	retry_interval = int(os.environ.get("MONGO_CONNECT_INTERVAL", "5"))  
	attempt = 0
	while attempt < max_retries:
		try:
			client = get_client()
			db = get_db(client=client)
			col = get_collection(client=client)
			logger.info("MongoDB connection successful.")
			break
		except ConnectionError as err:
			attempt += 1
			logger.error(f"Could not connect to MongoDB (attempt {attempt}/{max_retries}): {err}")
			if attempt >= max_retries:
				logger.error("Maximum retry attempts reached. Exiting.")
				break
			logger.info(f"Waiting {retry_interval} seconds before retrying...")
			time.sleep(retry_interval)
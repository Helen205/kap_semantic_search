import logging
import chromadb
from chromadb.config import Settings
from .config import config
import redis
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)

class ClientWrapper:
    _instance = None
    def __init__(self):
        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClientWrapper, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            self.client = chromadb.HttpClient(
                host=config.CHROMA_HOST,
                port=config.CHROMA_PORT,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            logger.info("ChromaDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

    def get_or_create_collection(self, name):
        try:
            collection = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Collection '{name}' retrieved/created successfully")
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection '{name}': {e}")
            raise

    def get_collection(self, name):
        try:
            collection = self.client.get_collection(
                name=name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Collection '{name}' retrieved successfully")
            return collection
        except Exception as e:
            logger.error(f"Failed to get collection '{name}': {e}")
            raise

    def delete_collection(self, name):
        try:
            self.client.delete_collection(
                name=name
            )
            logger.info(f"Created or retrieved collection: {name}")
        except Exception as e:
            logger.error(f"Collection creation error'{name}': {e}")
            raise

class RedisClient:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise

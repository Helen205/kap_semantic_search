import logging
import chromadb
from chromadb.config import Settings
from config import config
import redis
from chromadb.utils import embedding_functions as ef

logger = logging.getLogger(__name__)

class ClientWrapper:
    def __init__(self):
        self._client = self._connect()

    def _connect(self):
        try:            
            _client = chromadb.HttpClient( 
                host=config.CHROMA_HOST,
                port=config.CHROMA_PORT,
                tenant=config.CHROMA_TENANT,
                database="default_database",
                settings=Settings(allow_reset=True, anonymized_telemetry=False,
                                persist_directory=config.CHROMA_PERSIST_DIRECTORY
                                )
            )
            logger.info("Successfully connected to Chroma")
            
            return _client
            
            
        except Exception as e:
            logger.error(f"Chroma connection error: {e}")
            raise

    def get_collection(self, name, embedding_function):
        try:
            if embedding_function is None:
                embedding_function = ef.DefaultEmbeddingFunction()

            collection = self._client.get_or_create_collection(
                name=name,
                embedding_function=embedding_function
            )
            logger.info(f"Created or retrieved collection: {name}")
            return collection
        except Exception as e:
            logger.error(f"Collection creation error: {e}")
            raise
        

    @property
    def client(self):
        return self._client
class RedisClient:
    def __init__(self):
        self.host = config.REDIS_HOST
        self.port = config.REDIS_PORT
        self.decode_responses = True

    def _connect(self):
        try:
            client = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=self.decode_responses
            )
            return client
        except Exception as e:
            print(f"Error connecting to Redis: {e}")
            return None

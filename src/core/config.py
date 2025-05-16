from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Config(BaseSettings):
    CHROMA_HOST: str
    CHROMA_PORT: int
    CHROMA_TENANT: str
    CHROMA_PERSIST_DIRECTORY: str
    LAST_PROCESSED_TABLE_PATH: str
    GOOGLE_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: int
    ENV: str
    CHROMA_SERVER_CORS_ALLOW_ORIGINS: str
    CHROMA_SERVER_AUTH_PROVIDER: str
    LAST_PROCESSED_PATH: str

    @property
    def REDIS_URL(self) -> str:
        return f"redis://redis:{self.REDIS_PORT}/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  

config = Config()


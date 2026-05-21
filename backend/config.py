from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "HR Interview Simulator"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    OPENAI_API_KEY: str = "your-openai-api-key-here"
    LLM_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"

    FAISS_INDEX_PATH: str = "data/faiss_index"
    DATABASE_URL: str = "sqlite:///./hr_simulator.db"

    DEFAULT_ANSWER_TIME_LIMIT: int = 120
    MAX_QUESTIONS_PER_SESSION: int = 10

    model_config = ConfigDict(env_file=".env")


settings = Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./evaluator.db"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    github_token: str | None = None
    llm_provider: str = "groq"
    llm_model: str = "llama3-8b-8192"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    chroma_enabled: bool = False
    chroma_persist_dir: str = "./.chroma"
    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    stt_model: str | None = None
    stt_language: str | None = None
    tts_model: str | None = None
    tts_voice: str | None = None
    whisper_model: str = "tiny"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

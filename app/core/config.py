# core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NATS_URL: str = Field("nats://smart_energy_nats:4222", env="NATS_URL")
    LOG_DIR: str = Field("logs", env="LOG_DIR")
    BACKEND_API_URL: str = Field("http://smart_energy_backend:8000", env="BACKEND_API_URL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

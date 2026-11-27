from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.bak", extra="ignore")

    database_url: str
    log_level: str = "INFO"


settings = Settings()

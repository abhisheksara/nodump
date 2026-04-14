from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./research_feed.db"
    twitter_bearer_token: str = ""
    fetch_interval_hours: int = 6
    feed_limit: int = 10
    user_interests: str = "LLMs,agents,applied ML,inference,fine-tuning"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

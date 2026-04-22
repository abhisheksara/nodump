from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    database_url: str = "postgresql://feed:feed@localhost:5432/research_feed"
    dashboard_url: str = "http://localhost:3000"

    nudge_hour: int = 7
    nudge_minute: int = 0
    nudge_min_stories: int = 3

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = "abhisheksara27@gmail.com"

    allowed_origins: str = "http://localhost:3000"

    runs_dir: str = "./runs"
    runs_retention_days: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

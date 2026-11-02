from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str = ""
    gemini_api_key: str = ""
    jwt_secret: str = "810144f3f2fcbcfe7c918030b79be1b262b3bd5dfabc38e9f3c367f227f638d6"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
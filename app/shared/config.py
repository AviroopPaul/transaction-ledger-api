from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ledger:ledger@localhost:5432/ledger"


settings = Settings()

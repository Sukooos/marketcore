from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="marketcore_", extra="ignore")

    binance_ws_url: str
    database_dsn: str
    redis_dsn: str
    top_of_book_interval_ms: int = 250
    symbols: tuple[str, ...] = Field(default=("btcusdt", "ethusdt", "solusdt"))

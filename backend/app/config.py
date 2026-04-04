from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'FinClaw API'
    app_env: str = 'development'
    app_host: str = '127.0.0.1'
    app_port: int = 8000
    cors_origins: str = '*'
    database_url: str = 'sqlite:///./finclaw.db'

    alpaca_api_key: str = ''
    alpaca_secret_key: str = ''
    alpaca_paper: bool = True
    alpaca_base_url: str = 'https://paper-api.alpaca.markets'

    default_cash_limit: float = 500
    default_max_order_notional: float = 100
    default_max_daily_trades: int = 3
    default_approved_tickers: str = 'AAPL,MSFT,NVDA,GOOGL,BTCUSD,ETHUSD'

    armoriq_enabled: bool = False
    armoriq_api_key: str = ''

    @property
    def approved_tickers(self) -> list[str]:
        return [item.strip().upper() for item in self.default_approved_tickers.split(',') if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

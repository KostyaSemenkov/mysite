from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+asyncpg://board:board@localhost:5432/board'
    jwt_secret: str = 'dev-secret-not-for-production'
    jwt_ttl_seconds: int = 7 * 24 * 3600
    # origins через запятую в одной переменной
    cors_origins: str = 'http://localhost:5173,https://lemurqa.ru'
    # общий секрет с сайтом Django для SSO-токенов
    sso_secret: str = 'dev-sso-secret-not-for-production'

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]


settings = Settings()

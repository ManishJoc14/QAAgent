from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = PROJECT_ROOT / "artifacts" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    app_env: str = "local"

    cors_allowed_origins_raw: str = "http://127.0.0.1:5173,http://localhost:5173"
    trusted_hosts_raw: str = "127.0.0.1,localhost"
    force_https: bool = False
    api_auth_secret: str = "local-dev-auth-secret-change-me"

    provider_name: str = "mistral"
    provider_model: str = "mistral-large-latest"
    provider_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def trusted_hosts(self) -> list[str]:
        return [
            host.strip() for host in self.trusted_hosts_raw.split(",") if host.strip()
        ]

    def validate_security_settings(self) -> None:
        if self.app_env.lower() != "production":
            return

        if self.api_auth_secret == "local-dev-agent-auth-secret-change-me":
            raise ValueError("API_AUTH_SECRET must be overridden in production.")
        if len(self.api_auth_secret) < 32:
            raise ValueError(
                "API_AUTH_SECRET must be at least 32 characters in production."
            )
        if not self.cors_allowed_origins:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS_RAW must define explicit origins in production."
            )
        if "*" in self.cors_allowed_origins:
            raise ValueError("Wildcard CORS origin is not allowed in production.")
        if not self.trusted_hosts:
            raise ValueError(
                "TRUSTED_HOSTS_RAW must define explicit hosts in production."
            )
        if "*" in self.trusted_hosts:
            raise ValueError("Wildcard trusted host is not allowed in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()

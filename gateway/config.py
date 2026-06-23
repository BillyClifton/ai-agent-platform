from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database – must be set via the DATABASE_URL environment variable.
    # No default is provided here; use docker-compose.yml or k8s/secret.yaml.
    database_url: str

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "agent-tasks"

    # Gateway
    log_level: str = "info"
    gateway_url: str = "http://localhost:8000"

    # CORS – stored as a JSON string so it is easy to pass via env var
    cors_origins: str = '["http://localhost:3000","http://localhost:8000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()

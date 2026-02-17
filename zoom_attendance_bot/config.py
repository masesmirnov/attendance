from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .utils.validation import is_valid_column, normalize_column, strip_or_none


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Telegram
    bot_token: SecretStr

    # OpenAI
    openai_api_key: SecretStr
    openai_model: str = "gpt-5.2"
    openai_store: bool = False

    # Google Service Account
    google_service_account_file: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_SERVICE_ACCOUNT_FILE", "GOOGLE_APPLICATION_CREDENTIALS"),
    )

    # Sheets
    default_sheet_id: str | None = None
    worksheet_name: str
    roster_name_col: str
    roster_start_row: int

    # Access
    admin_ids: set[int] | None = None

    # Runtime
    log_level: str = "INFO"
    polling_concurrency_limit: int = 5

    # Persistence
    user_sheet_db_path: Path = Path("./data/user_sheets.sqlite3")

    @field_validator("bot_token", "openai_api_key", mode="before")
    @classmethod
    def _require_nonempty_secrets(cls, v: Any) -> Any:
        s = strip_or_none(v)
        if not s:
            raise ValueError("BOT_TOKEN and OPENAI_API_KEY are required (set them in .env)")
        return s

    @field_validator("worksheet_name", mode="before")
    @classmethod
    def _require_worksheet_name(cls, v: Any) -> str:
        s = strip_or_none(v)
        if not s:
            raise ValueError("WORKSHEET_NAME is required (set it in .env)")
        return s

    @field_validator("default_sheet_id", mode="before")
    @classmethod
    def _empty_sheet_id_to_none(cls, v: Any) -> str | None:
        return strip_or_none(v)

    @field_validator("roster_name_col", mode="before")
    @classmethod
    def _require_roster_col(cls, v: Any) -> str:
        s = strip_or_none(v)
        if not s:
            raise ValueError("ROSTER_NAME_COL is required (set it in .env)")
        s = normalize_column(s)
        if not is_valid_column(s):
            raise ValueError("ROSTER_NAME_COL must be like 'B' or 'AA'")
        return s

    @field_validator("roster_start_row", mode="before")
    @classmethod
    def _require_roster_start_row(cls, v: Any) -> int:
        s = strip_or_none(v)
        if not s:
            raise ValueError("ROSTER_START_ROW is required (set it in .env)")
        try:
            n = int(s)
        except Exception as e:
            raise ValueError("ROSTER_START_ROW must be an integer") from e
        if n < 1:
            raise ValueError("ROSTER_START_ROW must be >= 1")
        return n

    @field_validator("google_service_account_file", mode="before")
    @classmethod
    def _expand_sa_path(cls, v: Any) -> Path | None:
        if not v:
            return None
        return Path(v).expanduser().resolve()

    @field_validator("user_sheet_db_path", mode="before")
    @classmethod
    def _expand_db_path(cls, v: Any) -> Path:
        return Path(v).expanduser().resolve()

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: Any) -> set[int] | None:
        s = strip_or_none(v)
        if not s:
            return None
        items = [x.strip() for x in s.split(",") if x.strip()]
        out: set[int] = set()
        for it in items:
            if not it.isdigit():
                raise ValueError("ADMIN_IDS must be comma-separated integers")
            out.add(int(it))
        return out

    @model_validator(mode="after")
    def _validate_google_auth_source(self) -> "Settings":
        if self.google_service_account_file is None:
            raise ValueError("Provide GOOGLE_SERVICE_ACCOUNT_FILE")
        if not self.google_service_account_file.exists():
            raise ValueError(f"Service account file not found: {self.google_service_account_file}")
        return self

    @cached_property
    def google_service_account_info(self) -> dict[str, Any]:
        assert self.google_service_account_file is not None
        raw = self.google_service_account_file.read_text(encoding="utf-8")
        return json.loads(raw)

    @cached_property
    def service_account_email(self) -> str:
        info = self.google_service_account_info
        email = info.get("client_email")
        if not isinstance(email, str) or not email:
            raise ValueError("Service account JSON has no client_email")
        return email

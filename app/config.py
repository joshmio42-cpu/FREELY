from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr("postgresql://freely:freely@localhost:5432/freely")
    internal_api_token: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    ai_fast_model: str = "openai:gpt-5.4-nano"
    ai_quality_model: str = "openai:gpt-5.4-mini"
    strong_lead_threshold: int = Field(default=70, ge=0, le=100)
    pipeline_process_limit: int = Field(default=5, ge=1, le=100)
    freelancer_min_description_chars: int = Field(default=80, ge=1, le=2000)
    remoteok_api_url: str = "https://remoteok.com/api"
    scout_limit: int = Field(default=100, ge=1, le=500)
    scout_contract_only: bool = True
    jobicy_enabled: bool = True
    jobicy_api_url: str = "https://jobicy.com/api/v2/remote-jobs"
    jobicy_scout_limit: int = Field(default=100, ge=1, le=200)
    remotive_enabled: bool = True
    remotive_api_url: str = "https://remotive.com/api/remote-jobs"
    remotive_scout_limit: int = Field(default=100, ge=1, le=200)
    github_issues_enabled: bool = True
    github_api_url: str = "https://api.github.com/search/issues"
    github_token: SecretStr = SecretStr("")
    github_issue_queries: str = (
        "is:issue is:open bounty automation || "
        "is:issue is:open bounty python || "
        'is:issue is:open "paid task" spreadsheet'
    )
    github_scout_limit: int = Field(default=25, ge=1, le=50)
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: SecretStr = SecretStr("")
    telegram_poll_timeout: int = Field(default=20, ge=5, le=50)
    freelancer_api_authorized: bool = False
    freelancer_oauth_token: SecretStr = SecretStr("")
    freelancer_api_url: str = "https://www.freelancer.com/api/projects/0.1"
    freelancer_search_query: str = (
        "n8n automation api integration openai python data entry excel google sheets "
        "web research virtual assistant web scraping chatbot lead generation wordpress"
    )
    freelancer_scout_limit: int = Field(default=50, ge=1, le=100)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key.get_secret_value())

    @property
    def freelancer_enabled(self) -> bool:
        return self.freelancer_api_authorized and bool(
            self.freelancer_oauth_token.get_secret_value()
        )

    @property
    def telegram_commands_enabled(self) -> bool:
        return bool(
            self.telegram_bot_token.get_secret_value()
            and self.telegram_chat_id.get_secret_value()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

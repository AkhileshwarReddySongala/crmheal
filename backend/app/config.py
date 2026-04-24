import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    tinyfish_api_key: str = os.getenv("TINYFISH_API_KEY", "")
    vapi_api_key: str = os.getenv("VAPI_API_KEY", "")
    vapi_phone_number_id: str = os.getenv("VAPI_PHONE_NUMBER_ID", "")
    vapi_webhook_url: str = os.getenv("VAPI_WEBHOOK_URL", "")
    guild_workspace_id: str = os.getenv("GUILD_WORKSPACE_ID", "zxc")
    guild_workspace_url: str = os.getenv("GUILD_WORKSPACE_URL", "https://app.guild.ai/users/akhileshwar.songala/workspaces/zxc")
    guild_agent_name: str = os.getenv("GUILD_AGENT_NAME", "crm-heal")
    ghost_db_url: str = os.getenv("GHOST_DB_URL", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    use_mock_tinyfish: bool = env_bool("USE_MOCK_TINYFISH", True)
    use_mock_vapi: bool = env_bool("USE_MOCK_VAPI", True)
    auto_verify: bool = env_bool("AUTO_VERIFY", False)
    demo_verify_button: bool = env_bool("DEMO_VERIFY_BUTTON", True)
    vapi_timeout_seconds: int = int(os.getenv("VAPI_TIMEOUT_SECONDS", "45"))
    REASONER_PROVIDER: str = os.getenv("REASONER_PROVIDER", "rule")
    AKASH_API_KEY: str = os.getenv("AKASHML_API_KEY") or os.getenv("AKASH_API_KEY", "")
    AKASH_BASE_URL: str = os.getenv("AKASH_BASE_URL", "https://api.akashml.com/v1")
    AKASH_MODEL: str = os.getenv("AKASH_MODEL", "DeepSeek-V3.2")
    USE_LLM_REASONING: bool = env_bool("USE_LLM_REASONING", False)


settings = Settings()

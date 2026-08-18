from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = 'dev'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    log_level: str = 'INFO'

    database_url: str
    redis_url: str

    tg_api_id: int | None = None
    tg_api_hash: str | None = None
    tg_session_name: str = 'leadgen_session'

    openrouter_api_key: str | None = None
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    model_filter: str = 'openrouter/qwen/qwen3-8b'
    model_score: str = 'openrouter/deepseek/deepseek-chat-v3.1'
    model_summary: str = 'openai/gpt-5-mini'
    model_dialog: str = 'openai/gpt-5-mini'
    model_hard_dialog: str = 'openai/gpt-5'

    # Routing and cost controls
    hot_score_threshold: int = 85
    handoff_score_threshold: int = 90
    max_context_messages: int = 12
    max_facts_in_prompt: int = 6
    max_reply_chars: int = 420

    # Escalate to hard model when these terms are present in incoming lead message.
    hard_trigger_keywords: str = (
        'цена,бюджет,договор,кп,коммерческое,предоплата,гарантия,кейсы,риски,сроки,внедрение,интеграция'
    )

    human_review_chat_id: str | None = None


settings = Settings()

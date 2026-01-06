"""
Configuration constants for Perplexity AI API.

This module contains all configurable constants used throughout the library.
Modify these values to customize behavior without changing core code.
"""

from typing import Dict

# API Configuration
API_BASE_URL = "https://www.perplexity.ai"
API_VERSION = "2.18"
API_TIMEOUT = 30

# Endpoints
ENDPOINT_AUTH_SESSION = f"{API_BASE_URL}/api/auth/session"
ENDPOINT_AUTH_SIGNIN = f"{API_BASE_URL}/api/auth/signin/email"
ENDPOINT_SSE_ASK = f"{API_BASE_URL}/rest/sse/perplexity_ask"
ENDPOINT_UPLOAD_URL = f"{API_BASE_URL}/rest/uploads/batch_create_upload_urls"
ENDPOINT_ATTACHMENT_PROCESSING_SUBSCRIBE = (
    f"{API_BASE_URL}/rest/sse/attachment_processing/subscribe"
)
ENDPOINT_SOCKET_IO = f"{API_BASE_URL}/socket.io/"

# Emailnator Configuration
EMAILNATOR_BASE_URL = "https://www.emailnator.com"
EMAILNATOR_GENERATE_ENDPOINT = f"{EMAILNATOR_BASE_URL}/generate-email"
EMAILNATOR_MESSAGE_LIST_ENDPOINT = f"{EMAILNATOR_BASE_URL}/message-list"

# Account Limits
DEFAULT_COPILOT_QUERIES = 5
DEFAULT_FILE_UPLOADS = 10
ACCOUNT_TIMEOUT = 20  # seconds to wait for email

# Search Modes
SEARCH_MODES = ["auto", "pro", "reasoning", "deep research"]
SEARCH_SOURCES = ["web", "scholar", "social"]
SEARCH_LANGUAGES = ["en-US", "en-GB", "pt-BR", "es-ES", "fr-FR", "de-DE", "pl-PL"]

# Request Defaults
DEFAULT_TIMEZONE = "UTC"
DEFAULT_SEARCH_FOCUS = "internet"
DEFAULT_PROMPT_SOURCE = "user"
DEFAULT_QUERY_SOURCE = "home"
DEFAULT_IS_RELATED_QUERY = False
DEFAULT_IS_SPONSORED = False
DEFAULT_LOCAL_SEARCH_ENABLED = False
DEFAULT_USE_SCHEMATIZED_API = True
DEFAULT_SEND_BACK_TEXT_IN_STREAMING_API = False
DEFAULT_SKIP_SEARCH_ENABLED = True
DEFAULT_NAV_SUGGESTIONS_DISABLED = False
DEFAULT_ALWAYS_SEARCH_OVERRIDE = False
DEFAULT_OVERRIDE_NO_SEARCH = False
DEFAULT_SHOULD_ASK_FOR_MCP_TOOL_CONFIRMATION = True
DEFAULT_BROWSER_AGENT_ALLOW_ONCE_FROM_TOGGLE = False
DEFAULT_FORCE_ENABLE_BROWSER_AGENT = False
DEFAULT_SUPPORTED_BLOCK_USE_CASES = [
    "answer_modes",
    "media_items",
    "knowledge_cards",
    "inline_entity_cards",
    "place_widgets",
    "finance_widgets",
    "prediction_market_widgets",
    "sports_widgets",
    "flight_status_widgets",
    "news_widgets",
    "shopping_widgets",
    "jobs_widgets",
    "search_result_widgets",
    "inline_images",
    "inline_assets",
    "placeholder_cards",
    "diff_blocks",
    "inline_knowledge_cards",
    "entity_group_v2",
    "refinement_filters",
    "canvas_mode",
    "maps_preview",
    "answer_tabs",
    "price_comparison_widgets",
    "preserve_latex",
    "in_context_suggestions",
]
DEFAULT_SUPPORTED_FEATURES = ["browser_agent_permission_banner_v1.1"]

# Model Mappings
MODEL_MAPPINGS: Dict[str, Dict[str, str]] = {
    "auto": {None: "turbo"},
    "pro": {
        None: "pplx_pro",
        "pplx_pro": "pplx_pro",
        "pplx-pro": "pplx_pro",
        "pplx_pro_upgraded": "pplx_pro_upgraded",
        "pplx-pro-upgraded": "pplx_pro_upgraded",
        "sonar": "experimental",
        "experimental": "experimental",
        "gpt-5.2": "gpt52",
        "gpt52": "gpt52",
        "gpt-5.1": "gpt51",
        "gpt51": "gpt51",
        "gpt-5": "gpt5",
        "gpt5": "gpt5",
        "gpt-4.1": "gpt41",
        "gpt41": "gpt41",
        "claude-4.5-sonnet": "claude45sonnet",
        "claude45sonnet": "claude45sonnet",
        "gemini-3-flash": "gemini30flash",
        "gemini30flash": "gemini30flash",
        "grok-4.1": "grok41nonreasoning",
        "grok41nonreasoning": "grok41nonreasoning",
        "grok-4-1": "grok41nonreasoning",
        "grok-4": "grok4nonthinking",
        "grok4nonthinking": "grok4nonthinking",
    },
    "reasoning": {
        None: "pplx_reasoning",
        "pplx_reasoning": "pplx_reasoning",
        "pplx-reasoning": "pplx_reasoning",
        "pplx_study": "pplx_study",
        "pplx-study": "pplx_study",
        "gpt-5.2-thinking": "gpt52_thinking",
        "gpt52_thinking": "gpt52_thinking",
        "gpt-5.1-thinking": "gpt51_thinking",
        "gpt51_thinking": "gpt51_thinking",
        "gpt-5-thinking": "gpt5_thinking",
        "gpt5_thinking": "gpt5_thinking",
        "gpt5_pro": "gpt5_pro",
        "gpt-5-pro": "gpt5_pro",
        "o3pro": "o3pro",
        "o3-pro": "o3pro",
        "claude-4.5-sonnet-thinking": "claude45sonnetthinking",
        "claude45sonnetthinking": "claude45sonnetthinking",
        "claude-4.5-opus": "claude45opus",
        "claude45opus": "claude45opus",
        "claude-4.5-opus-thinking": "claude45opusthinking",
        "claude45opusthinking": "claude45opusthinking",
        "claude-4.1-opus": "claude41opus",
        "claude41opus": "claude41opus",
        "claude-4.1-opus-thinking": "claude41opusthinking",
        "claude41opusthinking": "claude41opusthinking",
        "gemini-3.0-pro": "gemini30pro",
        "gemini30pro": "gemini30pro",
        "gemini-2.5-pro": "gemini25pro",
        "gemini25pro": "gemini25pro",
        "gemini-3-flash-high": "gemini30flash_high",
        "gemini30flash_high": "gemini30flash_high",
        "kimi-k2-thinking": "kimik2thinking",
        "kimik2thinking": "kimik2thinking",
        "grok-4.1-reasoning": "grok41reasoning",
        "grok41reasoning": "grok41reasoning",
        "grok-4-1-reasoning": "grok41reasoning",
        "grok-4-thinking": "grok4",
        "grok4": "grok4",
    },
    "deep research": {
        None: "pplx_alpha",
        "pplx_alpha": "pplx_alpha",
        "pplx-alpha": "pplx_alpha",
        "claude40sonnetthinking_research": "claude40sonnetthinking_research",
        "claude40opusthinking_research": "claude40opusthinking_research",
        "o3pro_research": "o3pro_research",
        "o3-pro-research": "o3pro_research",
    },
}

# Labs Models
LABS_MODELS = [
    "r1-1776",
    "sonar-pro",
    "sonar",
    "sonar-reasoning-pro",
    "sonar-reasoning",
    "claude40sonnetthinking_labs",
    "claude40opusthinking_labs",
    "o3pro_labs",
    "pplx_beta",
]

# HTTP Headers Template
DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "dnt": "1",
    "priority": "u=0, i",
    "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"128.0.6613.120"',
    "sec-ch-ua-full-version-list": '"Not;A=Brand";v="24.0.0.0", "Chromium";v="128.0.6613.120"',  # noqa: E501
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"19.0.0"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",  # noqa: E501
}

# Emailnator Headers Template
EMAILNATOR_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "dnt": "1",
    "origin": EMAILNATOR_BASE_URL,
    "priority": "u=1, i",
    "referer": f"{EMAILNATOR_BASE_URL}/",
    "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"128.0.6613.120"',
    "sec-ch-ua-full-version-list": '"Not;A=Brand";v="24.0.0.0", "Chromium";v="128.0.6613.120"',  # noqa: E501
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"19.0.0"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",  # noqa: E501
    "x-requested-with": "XMLHttpRequest",
}

# Retry Configuration
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_EXCEPTIONS = (ConnectionError, TimeoutError)

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
LOG_FILE = "perplexity.log"

# Rate Limiting
RATE_LIMIT_MIN_DELAY = 1.0  # seconds
RATE_LIMIT_MAX_DELAY = 3.0  # seconds
RATE_LIMIT_ENABLED = True

# Validation Patterns
EMAIL_SUBJECT_PATTERN = "Sign in to Perplexity"
SIGNIN_URL_PATTERN = r'"(https://www\.perplexity\.ai/api/auth/callback/email\?callbackUrl=.*?)"'

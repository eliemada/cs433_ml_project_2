"""
Configuration for available LLM models via OpenRouter.
"""

AVAILABLE_MODELS = {
    # Fast & Cheap Tier
    "openai/gpt-5-mini": {
        "name": "GPT-5 Mini",
        "provider": "OpenAI",
        "tier": "fast",
        "context": 128000,
        "description": "Fast & cost-effective, multimodal"
    },
    "google/gemini-3-pro-preview": {
        "name": "Gemini 3 Pro Preview",
        "provider": "Google",
        "tier": "fast",
        "context": 65500,
        "description": "Ultra-fast inference"
    },
    "openai/gpt-5o": {
        "name": "GPT-5o",
        "provider": "OpenAI",
        "tier": "fast",
        "context": 128000,
        "description": "Full GPT-5o model, more capable than mini"
    },

    # Balanced Tier
    "anthropic/claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
        "tier": "balanced",
        "context": 200000,
        "description": "Excellent reasoning & coding"
    },
    "google/gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "provider": "Google",
        "tier": "balanced",
        "context": 1000000,
        "description": "Top performance, massive context"
    },
    "deepseek/deepseek-chat": {
        "name": "DeepSeek Chat",
        "provider": "DeepSeek",
        "tier": "balanced",
        "context": 64000,
        "description": "Strong open-source option"
    },

    # Premium Tier
    "anthropic/claude-sonnet-4.5": {
        "name": "Claude Sonnet 4.5",
        "provider": "Anthropic",
        "tier": "premium",
        "context": 200000,
        "description": "Latest flagship, complex reasoning"
    },
    "deepseek/deepseek-r1": {
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "tier": "premium",
        "context": 64000,
        "description": "Top Arena performance"
    },
    "qwen/qwen-2.5-72b-instruct": {
        "name": "Qwen 2.5 72B",
        "provider": "Qwen",
        "tier": "premium",
        "context": 128000,
        "description": "Excellent technical content"
    }
}

DEFAULT_MODEL = "openai/gpt-5-mini"

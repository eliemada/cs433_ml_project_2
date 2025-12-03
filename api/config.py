"""
Configuration for available LLM models via OpenRouter.
"""

AVAILABLE_MODELS = {
    # Fast & Cheap Tier
    "openai/gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "tier": "fast",
        "context": 128000,
        "description": "Fast & cost-effective, multimodal"
    },
    "openai/gpt-4o": {
        "name": "GPT-4o",
        "provider": "OpenAI",
        "tier": "fast",
        "context": 128000,
        "description": "Full GPT-4o model, more capable than mini"
    },
    "google/gemini-2.0-flash-exp": {
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "tier": "fast",
        "context": 32000,
        "description": "Ultra-fast inference"
    },

    # Balanced Tier
    "anthropic/claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
        "tier": "balanced",
        "context": 200000,
        "description": "Excellent reasoning & coding"
    },
    "google/gemini-pro-1.5": {
        "name": "Gemini Pro 1.5",
        "provider": "Google",
        "tier": "balanced",
        "context": 2000000,
        "description": "Large context, strong performance"
    },
    "deepseek/deepseek-chat": {
        "name": "DeepSeek Chat",
        "provider": "DeepSeek",
        "tier": "balanced",
        "context": 64000,
        "description": "Strong open-source option"
    },

    # Premium Tier
    "anthropic/claude-3-opus": {
        "name": "Claude 3 Opus",
        "provider": "Anthropic",
        "tier": "premium",
        "context": 200000,
        "description": "Most capable Claude model"
    },
    "deepseek/deepseek-r1": {
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "tier": "premium",
        "context": 64000,
        "description": "Top Arena performance with reasoning"
    },
    "qwen/qwen-2.5-72b-instruct": {
        "name": "Qwen 2.5 72B",
        "provider": "Qwen",
        "tier": "premium",
        "context": 128000,
        "description": "Excellent technical content"
    }
}

DEFAULT_MODEL = "openai/gpt-4o-mini"

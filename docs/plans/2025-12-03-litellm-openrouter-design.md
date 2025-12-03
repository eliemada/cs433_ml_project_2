# LiteLLM + OpenRouter Integration Design

**Date:** 2025-12-03
**Status:** Approved
**Goal:** Enable easy testing and comparison of multiple LLM providers through a unified interface

## Overview

Replace the current OpenAI-only chat integration with LiteLLM + OpenRouter to provide:
- Access to 8 curated top-tier models from 5 providers (OpenAI, Anthropic, Google, DeepSeek, Qwen)
- Single API key management through OpenRouter
- Beautiful frontend model selector with tier-based organization
- Graceful error handling with automatic fallback

## Key Design Decisions

1. **Keep OpenAI embeddings unchanged** - Current `OpenAIEmbedder` stays for embeddings only
2. **OpenRouter for all chat models** - Single unified API, no individual provider keys needed
3. **Curated model list** - 8 hand-picked models across 3 tiers (Fast, Balanced, Premium)
4. **Default model:** `openai/gpt-4o-mini` - Fast, cost-effective, reliable
5. **Frontend control** - Users can select any model via elegant dropdown

## Architecture

### Current State
```
User → Frontend → FastAPI → OpenAI Client → OpenAI API
                          ↓
                    OpenAI Embedder (unchanged)
```

### New State
```
User → Frontend (Model Selector) → FastAPI → LiteLLM → OpenRouter → Multiple Providers
                                          ↓
                                    OpenAI Embedder (unchanged)
```

## Model Selection

### Fast & Cheap Tier
- **openai/gpt-4o-mini** (default)
  - Fast & cost-effective, multimodal
  - 128K context window

- **google/gemini-2.0-flash-exp**
  - Ultra-fast inference
  - 32K context window

### Balanced Tier
- **anthropic/claude-3.5-sonnet**
  - Excellent reasoning & coding
  - 200K context window
  - 1.28M requests/month on OpenRouter

- **google/gemini-2.5-pro**
  - Top leaderboard performance
  - 1M context window
  - 905K requests/month on OpenRouter

- **deepseek/deepseek-chat**
  - Strong open-source option
  - 64K context window

### Premium Tier
- **anthropic/claude-sonnet-4.5**
  - Latest flagship for complex reasoning
  - 200K context window

- **deepseek/deepseek-r1**
  - Ranks 4th on Chatbot Arena
  - 64K context window

- **qwen/qwen-2.5-72b-instruct**
  - Excellent for technical content
  - 128K context window

**Source:** [OpenRouter Rankings December 2025](https://openrouter.ai/rankings?view=month)

## Implementation Details

### Backend Changes

#### 1. New Configuration File: `api/config.py`

```python
AVAILABLE_MODELS = {
    # Fast & Cheap
    "openai/gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "tier": "fast",
        "context": 128000,
        "description": "Fast & cost-effective, multimodal"
    },
    "google/gemini-2.0-flash-exp": {
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "tier": "fast",
        "context": 32000,
        "description": "Ultra-fast inference"
    },

    # Balanced
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

    # Premium
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

DEFAULT_MODEL = "openai/gpt-4o-mini"
```

#### 2. Update `api/main.py`

**Remove:**
```python
from openai import OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)
```

**Add:**
```python
from litellm import completion
from api.config import AVAILABLE_MODELS, DEFAULT_MODEL

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.environ.get("OPENROUTER_APP_NAME", "RAG Research Assistant")
```

**Replace chat completion call:**
```python
# Add model validation
if request.model not in AVAILABLE_MODELS:
    raise HTTPException(400, f"Invalid model: {request.model}")

# Generate answer using LiteLLM
try:
    completion_response = completion(
        model=request.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        api_base="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        temperature=0.3,
        max_tokens=2000,
        extra_headers={
            "HTTP-Referer": OPENROUTER_SITE_URL,
            "X-Title": OPENROUTER_APP_NAME
        }
    )

    answer = completion_response.choices[0].message.content

except Exception as e:
    logger.error(f"LLM completion failed for {request.model}: {e}")

    # Fallback to default model
    if request.model != DEFAULT_MODEL:
        try:
            completion_response = completion(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                api_base="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
                temperature=0.3,
                max_tokens=2000
            )
            answer = f"[Using fallback model {DEFAULT_MODEL}]\n\n{completion_response.choices[0].message.content}"
        except:
            raise HTTPException(503, "All LLM providers unavailable")
    else:
        raise HTTPException(503, f"LLM error: {str(e)}")
```

#### 3. New `/models` endpoint:

```python
@app.get("/models")
def get_available_models():
    """Return list of available models for frontend."""
    return {
        "models": [
            {
                "id": model_id,
                "name": info["name"],
                "provider": info["provider"],
                "tier": info["tier"],
                "context": info["context"],
                "description": info["description"]
            }
            for model_id, info in AVAILABLE_MODELS.items()
        ],
        "default": DEFAULT_MODEL
    }
```

### Frontend Changes

#### 1. New Component: `frontend/components/ModelSelector.tsx`

```tsx
import { useState, useEffect } from 'react';
import { ChevronDown, Zap, Scale, Crown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Model {
  id: string;
  name: string;
  provider: string;
  tier: 'fast' | 'balanced' | 'premium';
  description: string;
  context: number;
}

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
}

const tierConfig = {
  fast: {
    icon: Zap,
    color: 'text-blue-500',
    label: 'Fast & Cheap'
  },
  balanced: {
    icon: Scale,
    color: 'text-purple-500',
    label: 'Balanced'
  },
  premium: {
    icon: Crown,
    color: 'text-amber-500',
    label: 'Premium'
  }
};

export function ModelSelector({ selectedModel, onModelChange }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/models')
      .then(res => res.json())
      .then(data => {
        setModels(data.models);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load models:', err);
        setLoading(false);
      });
  }, []);

  const selected = models.find(m => m.id === selectedModel);

  // Group models by tier
  const groupedModels = {
    fast: models.filter(m => m.tier === 'fast'),
    balanced: models.filter(m => m.tier === 'balanced'),
    premium: models.filter(m => m.tier === 'premium')
  };

  if (loading) {
    return <div className="animate-pulse bg-gray-200 dark:bg-gray-700 h-12 w-64 rounded-xl" />;
  }

  return (
    <div className="relative">
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-gray-800
                   border border-gray-200 dark:border-gray-700 rounded-xl
                   hover:border-gray-300 dark:hover:border-gray-600
                   transition-all duration-200 shadow-sm hover:shadow-md min-w-[280px]"
      >
        {selected && (
          <>
            {(() => {
              const TierIcon = tierConfig[selected.tier].icon;
              return <TierIcon className={`w-4 h-4 ${tierConfig[selected.tier].color}`} />;
            })()}
            <div className="text-left flex-1">
              <div className="text-sm font-medium text-gray-900 dark:text-white">
                {selected.name}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {selected.provider}
              </div>
            </div>
          </>
        )}
        <ChevronDown
          className={`w-4 h-4 transition-transform text-gray-400
                     ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Menu */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full mt-2 w-full min-w-[320px] max-w-md
                         bg-white dark:bg-gray-800 rounded-xl shadow-xl border
                         border-gray-200 dark:border-gray-700 overflow-hidden z-50"
            >
              {Object.entries(groupedModels).map(([tier, tierModels]) => {
                const TierIcon = tierConfig[tier as keyof typeof tierConfig].icon;
                const tierColor = tierConfig[tier as keyof typeof tierConfig].color;
                const tierLabel = tierConfig[tier as keyof typeof tierConfig].label;

                if (tierModels.length === 0) return null;

                return (
                  <div key={tier}>
                    {/* Tier Header */}
                    <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50
                                  border-b border-gray-200 dark:border-gray-700">
                      <div className="flex items-center gap-2">
                        <TierIcon className={`w-3.5 h-3.5 ${tierColor}`} />
                        <span className="text-xs font-semibold uppercase tracking-wider
                                       text-gray-600 dark:text-gray-400">
                          {tierLabel}
                        </span>
                      </div>
                    </div>

                    {/* Models in Tier */}
                    {tierModels.map(model => (
                      <button
                        key={model.id}
                        onClick={() => {
                          onModelChange(model.id);
                          setIsOpen(false);
                        }}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-50
                                  dark:hover:bg-gray-700/50 transition-colors
                                  ${model.id === selectedModel ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900 dark:text-white">
                                {model.name}
                              </span>
                              <span className="text-xs text-gray-400 dark:text-gray-500">
                                {model.provider}
                              </span>
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                              {model.description}
                            </div>
                            <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                              {(model.context / 1000).toFixed(0)}K context
                            </div>
                          </div>
                          {model.id === selectedModel && (
                            <Check className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                );
              })}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
```

#### 2. Update Chat Page

Add model selector to the chat interface:

```tsx
// In your chat page component
import { ModelSelector } from '@/components/ModelSelector';

export default function ChatPage() {
  const [selectedModel, setSelectedModel] = useState("openai/gpt-4o-mini");
  const [messages, setMessages] = useState([]);

  const sendMessage = async (userMessage: string) => {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: userMessage,
        model: selectedModel,  // Include selected model
        top_k: 10,
        use_reranker: true
      })
    });

    const data = await response.json();
    // Handle response...
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Top Bar with Model Selector */}
      <div className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80
                      backdrop-blur-lg border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            Research Assistant
          </h1>
          <ModelSelector
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
          />
        </div>
      </div>

      {/* Chat messages and input */}
      {/* ... rest of chat UI ... */}
    </div>
  );
}
```

### Environment Variables

Update `.env`:

```bash
# Embeddings (existing - keep as is)
OPENAI_API_KEY=sk-...

# LLM Chat (new)
OPENROUTER_API_KEY=sk-or-v1-...

# Optional: OpenRouter tracking
OPENROUTER_SITE_URL=https://your-app.com
OPENROUTER_APP_NAME=RAG Research Assistant

# Existing variables
S3_BUCKET=cs433-rag-project2
ZEROENTROPY_API_KEY=...
CHUNK_TYPE=coarse
```

### Dependencies

Update `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps
    "litellm>=1.0.0",
]
```

## Testing Strategy

### Manual Testing Checklist

- [ ] Default model (gpt-4o-mini) works correctly
- [ ] Can switch between all 8 models
- [ ] Each tier (fast/balanced/premium) displays correctly
- [ ] Model descriptions and metadata show properly
- [ ] Dark mode support works
- [ ] Fallback mechanism triggers on model failure
- [ ] Error messages are user-friendly
- [ ] Model selection persists during chat session
- [ ] `/models` endpoint returns correct data
- [ ] OpenRouter API key authentication works

### Integration Tests

```python
# tests/test_litellm_integration.py
import pytest
from api.config import AVAILABLE_MODELS, DEFAULT_MODEL

def test_all_models_configured():
    """Ensure all models have required fields."""
    for model_id, config in AVAILABLE_MODELS.items():
        assert "name" in config
        assert "provider" in config
        assert "tier" in config
        assert "context" in config
        assert "description" in config
        assert config["tier"] in ["fast", "balanced", "premium"]

def test_default_model_exists():
    """Ensure default model is in available models."""
    assert DEFAULT_MODEL in AVAILABLE_MODELS

@pytest.mark.integration
def test_chat_with_each_model(client):
    """Test chat endpoint with each model."""
    for model_id in AVAILABLE_MODELS.keys():
        response = client.post("/chat", json={
            "message": "Hello, what is machine learning?",
            "model": model_id,
            "top_k": 5,
            "use_reranker": False
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
```

## Migration Plan

1. **Phase 1: Setup**
   - [ ] Add `OPENROUTER_API_KEY` to environment
   - [ ] Install `litellm` dependency: `uv add litellm`
   - [ ] Create `api/config.py` with model definitions

2. **Phase 2: Backend**
   - [ ] Update `api/main.py` with LiteLLM integration
   - [ ] Add `/models` endpoint
   - [ ] Add model validation
   - [ ] Implement error handling and fallback

3. **Phase 3: Frontend**
   - [ ] Create `ModelSelector.tsx` component
   - [ ] Update chat page to include model selector
   - [ ] Test UI in light and dark modes
   - [ ] Ensure responsive design

4. **Phase 4: Testing**
   - [ ] Test default model (gpt-4o-mini)
   - [ ] Test each provider (OpenAI, Anthropic, Google, DeepSeek, Qwen)
   - [ ] Test fallback mechanism
   - [ ] Test error scenarios
   - [ ] Load test with multiple concurrent requests

5. **Phase 5: Deployment**
   - [ ] Deploy backend changes
   - [ ] Deploy frontend changes
   - [ ] Monitor logs for errors
   - [ ] Validate with production traffic

## Success Criteria

- ✓ Users can select from 8 curated models across 3 tiers
- ✓ Default model (gpt-4o-mini) works reliably
- ✓ All providers accessible through single OpenRouter key
- ✓ Beautiful, intuitive UI for model selection
- ✓ Graceful error handling with automatic fallback
- ✓ No changes to existing embedding functionality
- ✓ Model selection persists during chat session

## Future Enhancements

- Add model performance metrics (speed, cost per request)
- Show real-time model availability status
- Add model recommendations based on query type
- Cache model metadata to reduce API calls
- Add A/B testing framework to compare model responses
- Support custom model parameters (temperature, max_tokens) per model

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [OpenRouter API Docs](https://openrouter.ai/docs)
- [OpenRouter Model Rankings](https://openrouter.ai/rankings?view=month)
- [Top AI Models on OpenRouter 2025](https://www.teamday.ai/blog/top-ai-models-openrouter-2025)

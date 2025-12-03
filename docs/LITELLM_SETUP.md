# LiteLLM + OpenRouter Setup Guide

This guide walks you through setting up and using the new LiteLLM + OpenRouter integration.

## Quick Start

### 1. Get OpenRouter API Key

1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Go to [API Keys](https://openrouter.ai/keys)
3. Create a new API key
4. Copy your key (starts with `sk-or-v1-...`)

### 2. Configure Environment Variables

Add to your `.env` file (or `.env.local` for frontend):

```bash
# Required: OpenRouter API key for chat models
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: For OpenRouter usage tracking
OPENROUTER_SITE_URL=https://your-app.com
OPENROUTER_APP_NAME=RAG Research Assistant

# Keep existing: For embeddings only
OPENAI_API_KEY=sk-your-openai-key
```

### 3. Install Dependencies

Backend dependencies are already installed via `uv`:

```bash
# Already done - litellm is in pyproject.toml
uv sync
```

### 4. Start the Services

**Backend:**
```bash
cd /path/to/project-2-rag
uvicorn api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### 5. Test the Integration

1. Open http://localhost:3000
2. Look for the model selector in the top right of the chat interface
3. Try different models and ask questions!

## Available Models

### Fast & Cheap (⚡)
- **GPT-4o Mini** (OpenAI) - Default, best balance
- **Gemini 2.0 Flash** (Google) - Ultra-fast inference

### Balanced (⚖️)
- **Claude 3.5 Sonnet** (Anthropic) - Excellent reasoning
- **Gemini 2.5 Pro** (Google) - Top performance, 1M context
- **DeepSeek Chat** - Strong open-source option

### Premium (👑)
- **Claude Sonnet 4.5** (Anthropic) - Latest flagship
- **DeepSeek R1** - Top Arena performance
- **Qwen 2.5 72B** - Excellent for technical content

## Features

✅ **Single API Key** - OpenRouter handles all providers
✅ **Beautiful UI** - Tier-based dropdown with animations
✅ **Automatic Fallback** - Falls back to GPT-4o Mini on errors
✅ **Dark Mode** - Full dark mode support
✅ **Model Metadata** - Shows context window, provider, description
✅ **Unchanged Embeddings** - OpenAI embeddings still work as before

## Testing Different Models

### Quick Test via API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the main challenges in AI policy?",
    "model": "anthropic/claude-3.5-sonnet",
    "top_k": 10,
    "use_reranker": true
  }'
```

### Get Available Models

```bash
curl http://localhost:8000/models
```

Response:
```json
{
  "models": [
    {
      "id": "openai/gpt-4o-mini",
      "name": "GPT-4o Mini",
      "provider": "OpenAI",
      "tier": "fast",
      "context": 128000,
      "description": "Fast & cost-effective, multimodal"
    },
    ...
  ],
  "default": "openai/gpt-4o-mini"
}
```

## Model Comparison Tips

1. **Start with Fast models** for quick iterations
2. **Use Balanced** for most production queries
3. **Reserve Premium** for complex analysis tasks

### When to Use Each Tier

**Fast (⚡):**
- Simple Q&A
- Quick lookups
- High-volume requests
- Development/testing

**Balanced (⚖️):**
- Standard policy questions
- Multi-paragraph analysis
- Synthesis across sources
- Production workloads

**Premium (👑):**
- Complex reasoning tasks
- Deep technical analysis
- Novel research questions
- Critical decisions

## Troubleshooting

### Error: "OpenRouter API key not configured"

**Solution:** Add `OPENROUTER_API_KEY` to your `.env` file and restart the backend.

### Error: "Invalid model: xyz"

**Solution:** Check available models via `/api/models` endpoint. Model ID must exactly match (e.g., `openai/gpt-4o-mini`).

### Model returns "[Using fallback model...]"

**Cause:** Primary model failed or unavailable.
**Result:** System automatically used GPT-4o Mini instead.
**Action:** Check OpenRouter status or try a different model.

### Frontend doesn't show model selector

**Causes:**
1. Backend `/models` endpoint not responding
2. Frontend not connected to backend
3. CORS issue

**Solutions:**
```bash
# Check backend health
curl http://localhost:8000/health

# Check models endpoint
curl http://localhost:8000/models

# Check frontend API URL
# In frontend/.env.local:
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Cost Optimization

### Model Costs (Approximate per 1M tokens)

| Model | Input Cost | Output Cost | Use Case |
|-------|-----------|-------------|----------|
| GPT-4o Mini | $0.15 | $0.60 | Default, balanced |
| Gemini 2.0 Flash | Free tier | Free tier | High volume |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Premium quality |
| DeepSeek Chat | $0.14 | $0.28 | Cost-effective |

**Tips:**
- Use GPT-4o Mini (default) for 90% of queries
- Reserve Claude/Premium for complex analysis
- Monitor usage in OpenRouter dashboard

## Advanced Configuration

### Adding New Models

Edit `api/config.py`:

```python
AVAILABLE_MODELS = {
    # ... existing models

    "new-provider/new-model": {
        "name": "New Model Name",
        "provider": "Provider",
        "tier": "balanced",  # fast | balanced | premium
        "context": 128000,
        "description": "Model description"
    }
}
```

### Customizing Default Model

Edit `api/config.py`:

```python
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"  # Change here
```

Or override via environment:

```bash
export DEFAULT_MODEL="google/gemini-2.5-pro"
```

### Adjusting Fallback Behavior

In `api/main.py`, the fallback logic is in the `/chat` endpoint. You can customize:

- Disable fallback (raise error immediately)
- Add retry logic
- Try multiple fallback models
- Log fallback events

## Monitoring & Analytics

### OpenRouter Dashboard

View usage stats at https://openrouter.ai/activity

Shows:
- Requests per model
- Token usage
- Costs
- Error rates

### Backend Logs

LiteLLM integration logs to standard output:

```bash
# Watch logs
tail -f backend.log | grep "LLM completion"
```

## Next Steps

1. ✅ **Test each model** - Try all 8 models with sample queries
2. ✅ **Compare outputs** - See which models work best for your use case
3. ✅ **Monitor costs** - Check OpenRouter dashboard after 1 week
4. ✅ **Optimize** - Adjust model selection based on quality/cost trade-offs
5. ✅ **Scale** - Deploy to production with confidence

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [OpenRouter Docs](https://openrouter.ai/docs)
- [OpenRouter Model Rankings](https://openrouter.ai/rankings)
- [Design Document](./plans/2025-12-03-litellm-openrouter-design.md)

## Support

For issues:
1. Check the [design document](./plans/2025-12-03-litellm-openrouter-design.md)
2. Review backend logs for errors
3. Test with `curl` to isolate frontend/backend issues
4. Check OpenRouter status page

---

**Last Updated:** 2025-12-03
**Version:** 1.0.0

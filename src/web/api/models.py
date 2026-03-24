"""Model discovery endpoints."""
import urllib.request
import urllib.parse
import json

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
async def list_models(host: str = Query("http://localhost:11434", description="Ollama server URL")):
    """List models available on the Ollama server."""
    from src.utils.model_providers import OllamaProvider

    provider = OllamaProvider(host=host)
    if not provider.is_available():
        return {"error": f"Ollama not reachable at {host}", "models": []}

    models = provider.list_models()
    return {
        "host": host,
        "models": [
            {
                "name": m.name,
                "size_human": m.size_human,
                "quantization": m.quantization,
                "family": m.family,
                "display_name": m.display_name,
            }
            for m in models
        ],
    }


@router.get("/openai")
async def list_openai_models(
    base_url: str = Query(..., description="OpenAI-compatible API base URL"),
    api_key: str = Query("", description="API key (optional for local servers)"),
):
    """List models from an OpenAI-compatible /v1/models endpoint."""
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    print(url)
    print(headers)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = data.get("data", [])
        return {
            "base_url": base_url,
            "models": [
                {
                    "name": m.get("id", ""),
                    "owned_by": m.get("owned_by", ""),
                    "display_name": m.get("id", ""),
                }
                for m in models
            ],
        }
    except Exception as e:
        return {"error": str(e), "models": []}


@router.get("/huggingface/search")
async def search_huggingface_models(
    query: str = Query(..., description="Search query"),
    api_key: str = Query("", description="HuggingFace API token (for gated models)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search HuggingFace Hub for models."""
    url = f"https://huggingface.co/api/models?search={urllib.parse.quote(query)}&limit={limit}&sort=downloads&direction=-1"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            models = json.loads(resp.read().decode("utf-8"))
        return {
            "query": query,
            "models": [
                {
                    "id": m.get("id", ""),
                    "author": m.get("author", ""),
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                    "pipeline_tag": m.get("pipeline_tag", ""),
                    "tags": m.get("tags", [])[:5],
                    "display_name": f"{m.get('id', '')} ({_fmt_downloads(m.get('downloads', 0))} DL)",
                }
                for m in models
            ],
        }
    except Exception as e:
        return {"error": str(e), "models": []}


def _fmt_downloads(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

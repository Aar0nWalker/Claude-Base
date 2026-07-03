"""Optional thin Anthropic (Claude) text-completion helper.

Lazily-created singleton client, same shape as the source project's
anthropic_client.py. Empty ANTHROPIC_API_KEY -> ai_text_enabled() is False and
callers should skip the feature entirely; nothing here is required for the
base template to run.
"""
from typing import Optional

from anthropic import AsyncAnthropic

from .config import settings

_client: Optional[AsyncAnthropic] = None


def ai_text_enabled() -> bool:
    """True when an API key is configured — gate Claude text features on this."""
    return bool(settings.anthropic_api_key)


def _make_client() -> AsyncAnthropic:
    global _client
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    if _client is None:
        kwargs: dict = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url.rstrip("/")
        _client = AsyncAnthropic(**kwargs)
    return _client


async def claude_complete(
    prompt: str,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 4096,
    thinking: bool = False,
) -> str:
    """One-shot Claude text completion -> concatenated text blocks.

    Defaults to settings.anthropic_model (claude-opus-4-8). `thinking=True`
    enables adaptive thinking for harder reasoning tasks — costs more, use
    sparingly. For cheap/high-volume text, pass model="claude-haiku-4-5-20251001".
    """
    client = _make_client()
    kwargs: dict = {
        "model": model or settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    msg = await client.messages.create(**kwargs)
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

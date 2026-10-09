"""
Single source of truth for the hosted AI model IDs the application offers.

Model IDs go stale quickly, so:

* every module (database defaults, settings pages, providers) reads from here;
* administrators can replace a provider's list without a code change through the
  ``OPENAI_MODELS``, ``CLAUDE_MODELS`` and ``GEMINI_MODELS`` environment variables
  (comma-separated, first entry becomes the default);
* settings that still reference a retired model are transparently resolved to a
  supported one at read time via :func:`resolve_model`.

This module intentionally has no third-party imports so it can be used from the
ORM models and tests without loading any provider SDK.
"""

import os
from typing import Dict, List, Optional

# Catalog verified against the official SDK model lists (openai-python
# ``ChatModel``, anthropic-sdk-python ``ModelParam``) and Google's Gemini model
# documentation. The first entry of each list is the default for new users.
_BUILTIN_MODELS: Dict[str, List[str]] = {
    "openai": [
        "gpt-5.6-terra",   # balanced cost / capability
        "gpt-6.1-sol",     # most capable reasoning model
        "gpt-6-luna",      # lower-cost reasoning
        "gpt-5.5",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
    ],
    "claude": [
        "claude-sonnet-5-5",
        "claude-opus-5-5",
        "claude-fable-5-1",
        "claude-haiku-5-5",
    ],
    "gemini": [
        "gemini-3.8-flash",        # stable
        "gemini-3.5-flash-lite",   # stable, lowest cost
        "gemini-3.1-pro-preview",  # preview: not recommended for production
    ],
}

_ENV_OVERRIDES = {
    "openai": "OPENAI_MODELS",
    "claude": "CLAUDE_MODELS",
    "gemini": "GEMINI_MODELS",
}


def get_hosted_models() -> Dict[str, List[str]]:
    """Return the hosted model list per provider, honouring environment overrides."""
    models: Dict[str, List[str]] = {}
    for provider, builtin in _BUILTIN_MODELS.items():
        override = os.environ.get(_ENV_OVERRIDES[provider], "")
        configured = [item.strip() for item in override.split(",") if item.strip()]
        models[provider] = configured or list(builtin)
    return models


def default_model(provider: str) -> str:
    """Default model ID for a hosted provider."""
    return get_hosted_models()[provider][0]


def resolve_model(provider: str, model: Optional[str]) -> Optional[str]:
    """
    Map a stored model ID to one that is currently offered.

    Retired IDs (for example ``gpt-4o`` or ``claude-3-5-sonnet-20241022`` saved by
    earlier versions) fall back to the provider default instead of failing every
    request with "model not found". Providers without a catalog (``local``) are
    returned unchanged.
    """
    models = get_hosted_models().get(provider)
    if models is None:
        return model
    return model if model in models else models[0]


# Defaults used for new database rows. Computed at import time on purpose: column
# defaults must be plain values.
DEFAULT_OPENAI_MODEL = _BUILTIN_MODELS["openai"][0]
DEFAULT_CLAUDE_MODEL = _BUILTIN_MODELS["claude"][0]
DEFAULT_GEMINI_MODEL = _BUILTIN_MODELS["gemini"][0]

"""
Cliente LLM unificado — cada agente llama al LLM a través de este módulo.
Soporta Anthropic (Claude) y OpenAI como fallback.
"""

from __future__ import annotations

import logging
from typing import Optional

from family_office.config.settings import settings

logger = logging.getLogger(__name__)


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Envía un prompt al LLM configurado y devuelve la respuesta como texto.
    """
    cfg = settings.llm
    model = model or cfg.model
    max_tokens = max_tokens or cfg.max_tokens
    temperature = temperature if temperature is not None else cfg.temperature

    if cfg.provider == "anthropic" and cfg.anthropic_api_key:
        return await _call_anthropic(system_prompt, user_prompt, model, max_tokens, temperature)
    elif cfg.provider == "openai" and cfg.openai_api_key:
        return await _call_openai(system_prompt, user_prompt, model, max_tokens, temperature)
    else:
        # Modo sin LLM — devuelve análisis estático basado en el prompt
        logger.warning("No LLM API key configured — returning static analysis placeholder")
        return _static_fallback(system_prompt, user_prompt)


async def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.llm.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


async def _call_openai(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.llm.openai_api_key)
    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _static_fallback(system_prompt: str, user_prompt: str) -> str:
    """Fallback cuando no hay API key — útil para testing y desarrollo."""
    return (
        f"[STATIC ANALYSIS — No LLM configured]\n"
        f"Agent context: {system_prompt[:200]}...\n"
        f"Query: {user_prompt[:200]}...\n"
        f"Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in .env for live analysis."
    )

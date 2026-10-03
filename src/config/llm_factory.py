"""
Local Ollama chat LLM factory (replaces OpenAI ChatOpenAI for text generation).
"""

from typing import Optional

from langchain_ollama import ChatOllama

from config.settings import (
    get_llm_max_tokens,
    get_llm_model,
    get_llm_temperature,
    get_ollama_base_url,
)

# from langchain_openai import ChatOpenAI


def create_chat_llm(
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = False,
    reasoning: bool = False,
    base_url: Optional[str] = None,
) -> ChatOllama:
    """Create a ChatOllama instance with thinking/reasoning disabled by default."""
    kwargs = {
        "model": model or get_llm_model(),
        "temperature": get_llm_temperature() if temperature is None else temperature,
        "num_predict": get_llm_max_tokens() if max_tokens is None else max_tokens,
        "reasoning": reasoning,
        "base_url": base_url or get_ollama_base_url(),
    }
    if streaming:
        kwargs["streaming"] = True
    return ChatOllama(**kwargs)

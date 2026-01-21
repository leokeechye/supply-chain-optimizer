"""Supply Chain Optimizer - Base Agent Class with Open Source LLM Support."""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel

from src.config import get_settings


class BaseAgent(ABC):
    """Base class for all Supply Chain Optimizer agents."""

    def __init__(
        self,
        name: str,
        description: str,
        llm_provider: str | None = None,
        model: str | None = None,
    ):
        self.name = name
        self.description = description
        self.settings = get_settings()
        self.logger = structlog.get_logger(self.__class__.__name__)
        
        # Initialize LLM with open source support
        provider = llm_provider or self.settings.llm_provider
        self.llm = self._create_llm(provider, model)
        
        self.logger.info(
            "Agent initialized",
            name=self.name,
            provider=provider,
        )

    def _create_llm(self, provider: str, model: str | None = None) -> BaseChatModel:
        """
        Create LLM instance based on provider.
        
        Supports:
        - ollama: Local open-source LLMs (default)
        - openai: OpenAI API
        - anthropic: Anthropic API
        """
        if provider == "ollama":
            # Open source: Ollama for local LLM inference
            from langchain_community.chat_models import ChatOllama
            
            return ChatOllama(
                base_url=self.settings.ollama_base_url,
                model=model or self.settings.ollama_model,
                temperature=0.7,
            )
        
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY required for OpenAI provider")
            
            return ChatOpenAI(
                model=model or self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0.7,
            )
        
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            
            if not self.settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
            
            return ChatAnthropic(
                model=model or self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key,
                temperature=0.7,
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> dict:
        """Execute the agent's main logic."""
        pass

    def get_system_prompt(self) -> str:
        """Get the agent's system prompt."""
        return f"""You are {self.name}, {self.description}.

You are part of the Supply Chain Optimizer system, designed to optimize 
global logistics, demand forecasting, and inventory management.

Be analytical, data-driven, and provide actionable recommendations.
Always consider cost, efficiency, and risk in your analysis.
"""

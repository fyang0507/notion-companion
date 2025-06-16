"""
Model Configuration Manager for Notion Companion

Centralized management of AI model configurations, providing a single source of truth
for model selection, parameters, and cost optimization settings.
"""

import os
import tomllib
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    dimensions: Optional[int] = None
    max_input_tokens: Optional[int] = None
    batch_size: Optional[int] = None

@dataclass
class LimitsConfig:
    """Token and processing limits."""
    max_embedding_tokens: int
    max_summary_input_tokens: int
    max_chat_context_tokens: int
    chunk_size_tokens: int
    chunk_overlap_tokens: int

@dataclass
class PerformanceConfig:
    """Performance and rate limiting settings."""
    embedding_batch_size: int
    embedding_delay_seconds: float
    chat_delay_seconds: float
    summarization_delay_seconds: float
    max_retries: int
    retry_delay_seconds: float

class ModelConfigManager:
    """Manages model configurations with environment-specific overrides."""
    
    def __init__(self, config_path: Optional[str] = None, environment: Optional[str] = None):
        """
        Initialize the model configuration manager.
        
        Args:
            config_path: Path to the models.toml file
            environment: Environment name (development, production, testing)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "models.toml"
        
        self.config_path = config_path
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self._config = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from TOML file."""
        try:
            with open(self.config_path, 'rb') as f:
                self._config = tomllib.load(f)
            logger.info(f"Loaded model configuration from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Model configuration file not found: {self.config_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading model configuration: {e}")
            raise
    
    def _get_config_value(self, path: str, default: Any = None) -> Any:
        """Get configuration value with environment override support."""
        # Try environment-specific override first
        env_path = f"environment.{self.environment}.{path}"
        env_value = self._get_nested_value(env_path)
        if env_value is not None:
            return env_value
        
        # Fall back to default configuration
        return self._get_nested_value(path, default)
    
    def _get_nested_value(self, path: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation."""
        keys = path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_embedding_config(self) -> ModelConfig:
        """Get embedding model configuration."""
        model = self._get_config_value("embedding_model", "text-embedding-3-small")
        if model == "text-embedding-3-small":
            config_section = self._config.get("models", {}).get("embedding", {})
        else:
            # Handle alternative models
            config_section = self._config.get("models", {}).get("embedding", {})
        
        return ModelConfig(
            model=model,
            dimensions=config_section.get("dimensions", 1536),
            max_input_tokens=config_section.get("max_input_tokens", 8191),
            batch_size=self._get_config_value("embedding_batch_size", config_section.get("batch_size", 100))
        )
    
    def get_chat_config(self) -> ModelConfig:
        """Get chat model configuration."""
        model = self._get_config_value("chat_model", "gpt-4o")
        config_section = self._config.get("models", {}).get("chat", {})
        
        return ModelConfig(
            model=model,
            max_tokens=config_section.get("max_tokens", 4096),
            temperature=config_section.get("temperature", 0.7)
        )
    
    def get_summarization_config(self) -> ModelConfig:
        """Get summarization model configuration."""
        model = self._get_config_value("summarization_model", "gpt-4o-mini")
        config_section = self._config.get("models", {}).get("summarization", {})
        
        return ModelConfig(
            model=model,
            max_tokens=config_section.get("max_tokens", 800),
            temperature=config_section.get("temperature", 0.3)
        )
    
    # Analysis config not currently used
    # def get_analysis_config(self) -> ModelConfig:
    #     """Get analysis model configuration."""
    #     config_section = self._config.get("models", {}).get("analysis", {})
    #     
    #     return ModelConfig(
    #         model=config_section.get("model", "gpt-4o-mini"),
    #         max_tokens=config_section.get("max_tokens", 1000),
    #         temperature=config_section.get("temperature", 0.2)
    #     )
    
    def get_limits_config(self) -> LimitsConfig:
        """Get processing limits configuration."""
        limits = self._config.get("limits", {})
        
        return LimitsConfig(
            max_embedding_tokens=limits.get("max_embedding_tokens", 8000),
            max_summary_input_tokens=limits.get("max_summary_input_tokens", 20000),
            max_chat_context_tokens=limits.get("max_chat_context_tokens", 15000),
            chunk_size_tokens=limits.get("chunk_size_tokens", 1000),
            chunk_overlap_tokens=limits.get("chunk_overlap_tokens", 100)
        )
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance and rate limiting configuration."""
        perf = self._config.get("performance", {})
        
        return PerformanceConfig(
            embedding_batch_size=self._get_config_value("embedding_batch_size", perf.get("embedding_batch_size", 100)),
            embedding_delay_seconds=perf.get("embedding_delay_seconds", 0.1),
            chat_delay_seconds=perf.get("chat_delay_seconds", 0.5),
            summarization_delay_seconds=perf.get("summarization_delay_seconds", 1.0),
            max_retries=self._get_config_value("max_retries", perf.get("max_retries", 3)),
            retry_delay_seconds=perf.get("retry_delay_seconds", 2.0)
        )
    
    # Alternative model methods not currently used
    # def get_alternative_model(self, model_type: str, alternative: str) -> Optional[str]:
    #     """Get alternative model for a given type."""
    #     try:
    #         alternatives = self._config["models"][model_type]["alternatives"]
    #         return alternatives.get(alternative)
    #     except KeyError:
    #         return None
    # 
    # def list_available_models(self) -> Dict[str, Dict[str, str]]:
    #     """List all available models by type."""
    #     models = {}
    #     for model_type in ["embedding", "chat", "summarization"]:
    #         models[model_type] = {
    #             "primary": self._config.get("models", {}).get(model_type, {}).get("model", "unknown"),
    #             "alternatives": self._config.get("models", {}).get(model_type, {}).get("alternatives", {})
    #         }
    #     return models
    
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        logger.info("Model configuration reloaded")

# Global instance
_model_config_manager = None

def get_model_config() -> ModelConfigManager:
    """Get the global model configuration manager instance."""
    global _model_config_manager
    if _model_config_manager is None:
        _model_config_manager = ModelConfigManager()
    return _model_config_manager

def set_model_config(config_manager: ModelConfigManager) -> None:
    """Set the global model configuration manager instance."""
    global _model_config_manager
    _model_config_manager = config_manager
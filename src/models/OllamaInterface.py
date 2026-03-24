from src.models.BaseModelInterface import BaseModelInterface
from src.utils.logger import logger
from src.core.types import BaseTestConfig

import ollama
from typing import Dict, Optional, Tuple

class OllamaInterface(BaseModelInterface):
    """Enhanced interface for communicating with Ollama with better error handling"""

    def __init__(self, config: BaseTestConfig):
        super().__init__(config)
        self.client = ollama.Client()

        # Test connection
        try:
            self.client.list()
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise RuntimeError("Ollama server not running. Start with 'ollama serve'") from e

    def preload_models(self) -> None:
        """Preload models to reduce latency"""
        pass  # Placeholder for potential future implementation

    def supports_reasoning(self, model: str) -> bool:
        """Check if the model supports reasoning based on its name"""
        try:
            model_info = self.client.show(model)
            capabilities = model_info.capabilities
            return 'thinking' in capabilities
        except Exception as e:
            logger.warning(f"Could not retrieve model info for {model}: {e}")
            return False

    def query_model(self, model: str, prompt: str, system: str) -> Tuple[str, Dict[str, int]]:
        """Send prompt to Ollama with comprehensive error handling"""
        for retry in range(3):
            try:
                response = self.client.generate(
                    model=model,
                    system=system,
                    prompt=prompt,
                    think=None if self.config.no_think is None else True if self.supports_reasoning(model) and not self.config.no_think else False,
                    options={
                        'temperature': self.config.temperature,
                        'seed': self.config.seed,
                        'top_k': self.config.top_k,
                        'min_k': self.config.min_k,
                        'min_p': self.config.min_p,
                        'num_ctx': self.config.ctx_len,
                        'num_predict': self.config.num_predict,
                        "num_keep": 20,
                        "use_mmap": True,
                        "num_thread": 8
                    }
                )
                
                stats = {
                    'total_duration':  response['total_duration'],
                    'load_duration': response['load_duration'],
                    'prompt_eval_count': response['prompt_eval_count'],
                    'prompt_eval_duration': response['prompt_eval_duration'],
                    'eval_count': response['eval_count'],
                    'eval_duration': response['eval_duration'],
                }
                
                return response['response'].strip(), stats

            except ollama.ResponseError as e:
                error_msg = f"Ollama API error for model {model}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
                # continue
            except RuntimeError as e:
                error_msg = f"Unexpected error querying model {model}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
                # continue

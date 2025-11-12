from src.BaseModelInterface import BaseModelInterface
from src.utils.logger import logger
from src.types import TestConfig

import requests
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from typing import Dict, Tuple



class HuggingFaceInterface(BaseModelInterface):
    """Interface for HuggingFace transformers with MPS backend support"""

    def __init__(self, config: TestConfig):
        super().__init__(config)

        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available. Install with: pip install transformers torch")

        # Set up device - prefer MPS for Apple Silicon, fallback to CPU
        if torch.backends.cuda.is_available():
            self.device = "cuda"
            logger.info("Using CUDA backend for acceleration")
        elif torch.backends.mps.is_available():
            self.device = "mps"
            logger.info("Using MPS backend for acceleration")
        else:
            self.device = "cpu"
            logger.info("MPS not available, using CPU backend")

        self.loaded_models = {}  # Cache for loaded models
        self.loaded_tokenizers = {}  # Cache for loaded tokenizers

    def preload_models(self) -> None:
        """Preload models to reduce latency"""
        # This could be implemented to preload specific models
        # For now, models are loaded on-demand
        pass

    def supports_reasoning(self, model: str) -> bool:
        """Check if the model supports reasoning - placeholder for now"""

        model_card = requests.get(f"https://huggingface.co/api/models/{model}").json()
        if 'config' in model_card and 'tokenizer_config' in model_card['config']:
            chat_template = model_card['config']['tokenizer_config'].get('chat_template', '')
            return '<think>' in chat_template and '</think>' in chat_template

        return False

    def _load_model_and_tokenizer(self, model_name: str) -> Tuple[object, object]:
        """Load and cache model and tokenizer"""
        if model_name not in self.loaded_models:
            try:
                logger.info(f"Loading model {model_name} on {self.device}")

                # Load tokenizer
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token

                # Load model with appropriate settings for the device
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if self.device == "mps" else torch.float32,
                    device_map=None,  # We'll manually move to device
                    low_cpu_mem_usage=True
                )

                # Move to device
                model = model.to(self.device)
                model.eval()  # Set to evaluation mode

                # Cache the models
                self.loaded_models[model_name] = model
                self.loaded_tokenizers[model_name] = tokenizer

                logger.info(f"Successfully loaded {model_name}")

            except Exception as e:
                error_msg = f"Failed to load model {model_name}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        return self.loaded_models[model_name], self.loaded_tokenizers[model_name]

    def query_model(self, model: str, prompt: str, system: str) -> Tuple[str, Dict[str, int]]:
        """Send prompt to HuggingFace model with comprehensive error handling"""
        try:
            model_obj, tokenizer = self._load_model_and_tokenizer(model)

            # Tokenize input
            inputs = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=self.config.ctx_len)
            inputs = inputs.to(self.device)

            # Generate response
            with torch.no_grad():
                outputs = model_obj.generate(
                    inputs,
                    max_new_tokens=self.config.num_predict,
                    temperature=self.config.temperature,
                    do_sample=True if self.config.temperature > 0 else False,
                    top_k=self.config.top_k if hasattr(self.config, 'top_k') else 50,
                    top_p=getattr(self.config, 'min_p', 0.9),
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    repetition_penalty=1.1,
                    length_penalty=1.0,
                )

            # Decode response (exclude the input prompt)
            response_tokens = outputs[0][len(inputs[0]):]
            response = tokenizer.decode(response_tokens, skip_special_tokens=True)

            return response.strip()

        except torch.cuda.OutOfMemoryError as e:
            error_msg = f"Out of memory error for model {model}. Try reducing context length or batch size."
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error querying HuggingFace model {model}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def clear_cache(self):
        """Clear model cache to free up memory"""
        for model_name, model in self.loaded_models.items():
            del model
            logger.info(f"Cleared {model_name} from cache")

        self.loaded_models.clear()
        self.loaded_tokenizers.clear()

        # Clear PyTorch cache if using MPS
        if self.device == "mps":
            torch.mps.empty_cache()

        logger.info("Cleared all models from cache")
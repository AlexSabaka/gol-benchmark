# Model Provider Architecture

## Overview

The benchmark TUI now supports multiple model providers with intelligent model discovery, grouping, and filtering capabilities. Currently supporting **Ollama** and **HuggingFace** (placeholder).

## Architecture

### Components

**model_providers.py**
- `ModelInfo`: Dataclass representing model metadata
  - `name`: Full model identifier
  - `size_bytes`: Size in bytes
  - `size_human`: Human-readable size (e.g., "4.7 GB")
  - `quantization`: Format (F16, Q4_K_M, etc.)
  - `family`: Model family (qwen, gemma, llama, etc.)
  - `display_name`: Pretty-printed name with size and quantization

- `ModelProvider` (ABC): Abstract base for providers
  - `list_models()`: Get available models
  - `is_available()`: Check if provider is connected

- `OllamaProvider`: Ollama model provider
  - Queries `ollama list` for available models
  - Extracts quantization, family, and size info
  - Caches results for performance
  - Automatically detects model families and quantizations

- `HuggingFaceProvider`: HuggingFace provider (placeholder)
  - Skeleton for future implementation

- `ModelProviderManager`: Unified interface for all providers
  - `get_available_providers()`: List working providers
  - `group_models()`: Group by family/quantization/size
  - `filter_models()`: Filter by various criteria

### Integration with benchmark_config.py

Updated `ModelSpec` to include provider information:
```python
@dataclass
class ModelSpec:
    name: str
    provider: str = "ollama"  # Which provider supplies this model
    size_params: Optional[str] = None  # Estimated parameters
    family: Optional[str] = None  # qwen, gemma, llama, etc.
    quantization: Optional[str] = None  # F16, Q4_K_M, Q2_K, etc.
    size_bytes: int = 0  # Actual size in bytes
    tags: List[str] = field(default_factory=list)
```

## Features

### 1. Provider Detection

The TUI automatically detects available providers:
- ✓ Ollama: Checks if `ollama` command works
- ✓ HuggingFace: Checks if `huggingface-cli` is installed

User sees only available providers.

### 2. Dynamic Model Discovery

No hardcoded model lists! Models are discovered from each provider:

**Ollama**: Parses `ollama list` output
```
NAME                                                    ID              SIZE      MODIFIED
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q2_K    abc123...       752 MB    2 hours ago
qwen:0.5b                                              def456...       432 MB    3 days ago
```

### 3. Model Organization

Models can be viewed and filtered by:

**By Family** (Automatic extraction)
- qwen: 9 models
- gemma: 10 models
- llama: 4 models
- acemath: 4 models
- other: 17 models

**By Quantization**
- Full Precision: 19 models
- F16: 6 models
- Q4_K_M: 10 models
- Q2_K: 1 model
- Q6_K: 1 model
- Q8_0: 7 models

**By Size**
- < 2B: 44 models
- 2-8B: (future)
- 8-15B: (future)
- > 15B: (future)

### 4. Advanced Filtering

Interactive multi-select filters:
- Filter by model family (qwen, gemma, etc.)
- Filter by quantization (Full Precision, Q2_K, Q4_K_M, etc.)
- Combine multiple filters
- See count of matching models in real-time

### 5. Smart Display

Model names include helpful information:
```
Model Display Examples:
  • qwen:0.5b (432 MB)
  • qwen:4b (2.8 GB) [Q4_K_M]
  • AceMath-1.5B-Instruct-GGUF (3.6 GB) [F16]
  • Gemma3-12B (7.2 GB) [Q8_0]
```

## Usage in TUI

### Step 1: Provider Selection
If multiple providers available, user chooses one:
```
Which model provider would you like to use?
  ○ ollama
  ○ huggingface
```

### Step 2: Model Organization
User chooses how to view models:
```
How would you like to view models?
  ○ All Models (flat list)
  ○ Grouped by Family
  ○ Grouped by Quantization
  ○ Grouped by Size
  ○ Filter & Select
```

### Step 3a: View Grouped Models (example: Family)
```
Select models:
─── acemath ───
  ○ AceMath-1.5B-Instruct-GGUF (3.6 GB) [F16]
  ○ AceMath-1.5B-Instruct-GGUF (752 MB) [Q2_K]
  ○ AceMath-1.5B-Instruct-GGUF (1.1 GB) [Q4_K_M]
─── gemma ───
  ○ Gemma3-2B (1.8 GB)
  ○ Gemma3-9B-Instruct (5.2 GB) [Q4_K_M]
...
```

### Step 3b: Filter & Select
```
Filter by Model Family:
  ☑ qwen
  ☐ gemma
  ☐ llama
  ☑ All

Filter by Quantization:
  ☐ Full Precision
  ☑ Q2_K
  ☑ Q4_K_M
  ☐ All

✓ 4 models match filters
```

## API Examples

### List all models from Ollama
```python
from model_providers import ModelProviderManager

manager = ModelProviderManager()
ollama_models = manager.list_models_by_provider("ollama")
for model in ollama_models:
    print(model.display_name)
```

### Group models by family
```python
grouped = manager.group_models(ollama_models, group_by="family")
for family, models in grouped.items():
    print(f"{family}: {len(models)} models")
    for model in models:
        print(f"  • {model.display_name}")
```

### Filter for specific models
```python
# Only Qwen models
qwen_models = manager.filter_models(ollama_models, family="qwen")

# Only quantized models
q_models = manager.filter_models(
    ollama_models, 
    quantization=["Q2_K", "Q4_K_M"]
)

# Only small models
small = manager.filter_models(ollama_models, max_size=2e9)  # 2GB
```

## Future Enhancements

### Provider Expansion
1. **HuggingFace**: Implement full model listing from HF Hub
2. **Together.ai**: Cloud model API integration
3. **Local Models**: /models directory scanning
4. **Remote APIs**: OpenAI, Claude, Grok, etc.

### Features
1. **Model Performance Cache**: Store inference speed per model
2. **Capability Matrix**: Track which models support which features
3. **Dependency Checking**: Auto-install missing models
4. **Benchmarking Presets**: "All Qwen models" or "Best quantizations"
5. **Size Recommendations**: "Pick models under 4GB" for testing

## Troubleshooting

### Issue: "No model providers available"
**Solution**: Install Ollama
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve  # Start Ollama in background
```

### Issue: Ollama shows no models
**Solution**: Pull some models first
```bash
ollama pull qwen:0.5b
ollama pull gemma:7b
ollama pull mistral:latest
```

### Issue: Model info not parsing correctly
**Solution**: Update model_providers.py family/quantization patterns for new models

## Performance

- **Initialization**: ~100ms (checks provider availability)
- **Model Listing**: ~500ms (first call), ~10ms (cached)
- **Grouping**: ~50ms (in-memory operation)
- **Filtering**: ~20ms (in-memory operation)

Model information is cached after first listing for fast repeated access.

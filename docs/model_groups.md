# Model Grouping Reference

Complete classification of 41 available models for testing and benchmarking.

---

## By Parameter Size

### Under 1B Parameters

```text
smollm2:135m
hf.co/unsloth/gemma-3-270m-it-qat-GGUF:F16
hf.co/unsloth/gemma-3-270m-it-GGUF:F16
mollysama/rwkv-7-g1:0.1B
granite-embedding:278m
```

### 1B to 2B Parameters

```text
mollysama/rwkv-7-g1:0.4b
qwen3:0.6b
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:F16
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q2_K
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q8_0
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M
hf.co/mradermacher/ARWKV-R1-1B5-GGUF:F16
gemma3:1b
hf.co/lmstudio-community/Falcon3-1B-Instruct-GGUF:Q8_0
```

### 2B to 4B Parameters

```text
hf.co/bartowski/Qwen2-VL-2B-Instruct-GGUF:F16
qwen3:1.7b
hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:F16
hf.co/ApatheticWithoutTheA/Qwen-2.5-3B-Reasoning:latest
hf.co/unsloth/medgemma-4b-it-GGUF:Q8_0
gemma3:4b
hf.co/mradermacher/Fathom-Search-4B-GGUF:Q4_K_M
hf.co/lmstudio-community/gemma-3-4b-it-GGUF:Q8_0
hf.co/unsloth/Qwen3-4B-Thinking-2507-GGUF:Q8_0
```

### 7B to 9B Parameters

```text
hf.co/mradermacher/deepseek-math-7b-instruct-GGUF:Q4_K_M
hf.co/mradermacher/Thinking-Camel-7b-GGUF:Q4_K_M
hf.co/mradermacher/WhiteRabbitNeo-V3-7B-GGUF:Q4_K_M
hf.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF:Q8_0
qwen3:8b
hf.co/lmstudio-community/txgemma-9b-chat-GGUF:Q6_K
Qwen2.5-Coder-7B-Instruct-Q4_K_M-1739364715670:latest
llama3.2_3b_122824_uncensored.Q8_0-1739364637622:latest
```

### 12B+ Parameters

```text
hf.co/mradermacher/Fathom-R1-14B-GGUF:Q4_K_M
hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-1M-GGUF:IQ2_M
hf.co/DavidAU/Llama-3.2-8X3B-MOE-Dark-Champion-Instruct-uncensored-abliterated-18.4B-GGUF:Q4_K_M
gemma3:12b
hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q4_K_M
hf.co/DavidAU/Qwen3-8B-64k-Josiefied-Uncensored-NEO-Max-GGUF:latest
```

---

## By Model Family

### RWKV Series (mollysama/rwkv-7-g1)

```text
mollysama/rwkv-7-g1:0.1B    (0.1B - under 1B)
mollysama/rwkv-7-g1:0.4b    (0.4B - 1-2B)
mollysama/rwkv-7-g1:1.5b    (1.5B - 1-2B)
mollysama/rwkv-7-g1:2.9b    (2.9B - 2-4B)
```

### Qwen Series

#### Qwen3

```text
qwen3:0.6b                   (0.6B - under 1B)
qwen3:1.7b                   (1.7B - 2-4B)
qwen3:8b                     (8B - 7-9B)
```

#### Qwen3 Special

```text
hf.co/unsloth/Qwen3-4B-Thinking-2507-GGUF:Q8_0              (4B - reasoning)
hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-1M-GGUF:IQ2_M    (30B - coding)
hf.co/ApatheticWithoutTheA/Qwen-2.5-3B-Reasoning:latest     (3B - reasoning)
Qwen2.5-Coder-7B-Instruct-Q4_K_M-1739364715670:latest       (7B - coding)
```

### Gemma Series

#### Gemma3

```text
hf.co/unsloth/gemma-3-270m-it-qat-GGUF:F16                  (270M - quantized)
hf.co/unsloth/gemma-3-270m-it-GGUF:F16                       (270M - full precision)
gemma3:1b                                                     (1B)
gemma3:4b                                                     (4B)
gemma3:12b                                                    (12B)
```

#### Gemma3 Special

```text
hf.co/lmstudio-community/gemma-3-4b-it-GGUF:Q8_0            (4B - Q8_0)
hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q4_K_M         (12B - Q4_K_M)
hf.co/lmstudio-community/txgemma-9b-chat-GGUF:Q6_K          (9B - TX variant)
hf.co/unsloth/medgemma-4b-it-GGUF:Q8_0                       (4B - medical)
```

### Llama Series

```text
hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:F16              (3.2 - 3B)
hf.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF:Q8_0        (3.1 - 8B)
hf.co/DavidAU/Llama-3.2-8X3B-MOE-Dark-Champion-...           (3.2 MOE - 18.4B)
llama3.2_3b_122824_uncensored.Q8_0-1739364637622:latest     (3.2 - local variant)
```

### Falcon Series

```text
hf.co/lmstudio-community/Falcon3-1B-Instruct-GGUF:Q8_0      (Falcon3 - 1B)
```

### Math-Specialized Models

```text
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:F16           (AceMath - 1.5B)
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q2_K          (AceMath Q2_K)
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q8_0          (AceMath Q8_0)
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M        (AceMath Q4_K_M)
hf.co/mradermacher/deepseek-math-7b-instruct-GGUF:Q4_K_M    (DeepSeek Math - 7B)
```

### Reasoning-Specialized Models

```text
hf.co/mradermacher/Thinking-Camel-7b-GGUF:Q4_K_M            (Thinking Camel - 7B)
hf.co/mradermacher/ARWKV-R1-1B5-GGUF:F16                     (ARWKV-R1 - 1.5B)
hf.co/mradermacher/Fathom-R1-14B-GGUF:Q4_K_M                (Fathom-R1 - 14B)
hf.co/mradermacher/WhiteRabbitNeo-V3-7B-GGUF:Q4_K_M         (WhiteRabbit - 7B)
hf.co/mradermacher/Fathom-Search-4B-GGUF:Q4_K_M             (Fathom-Search - 4B)
```

### Other

```text
hf.co/bartowski/Qwen2-VL-2B-Instruct-GGUF:F16               (Qwen2-VL - vision)
hf.co/DavidAU/Qwen3-8B-64k-Josiefied-Uncensored-NEO-Max-GGUF (Qwen3 - 8B special)
smollm2:135m                                                  (SmoLLM2)
```

---

## By Quantization Type

### F16 (Full Precision - Larger Size, Better Quality)

```text
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:F16
hf.co/bartowski/Qwen2-VL-2B-Instruct-GGUF:F16
hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:F16
hf.co/unsloth/gemma-3-270m-it-GGUF:F16
hf.co/unsloth/gemma-3-270m-it-qat-GGUF:F16
hf.co/mradermacher/ARWKV-R1-1B5-GGUF:F16
```

### Q8_0 (8-bit - Good Quality, Moderate Size)

```text
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q8_0
hf.co/lmstudio-community/Falcon3-1B-Instruct-GGUF:Q8_0
hf.co/unsloth/Qwen3-4B-Thinking-2507-GGUF:Q8_0
hf.co/unsloth/medgemma-4b-it-GGUF:Q8_0
hf.co/lmstudio-community/gemma-3-4b-it-GGUF:Q8_0
hf.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF:Q8_0
```

### Q4_K_M (4-bit - Smaller Size, Faster)

```text
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M
hf.co/mradermacher/deepseek-math-7b-instruct-GGUF:Q4_K_M
hf.co/mradermacher/Thinking-Camel-7b-GGUF:Q4_K_M
hf.co/mradermacher/Fathom-R1-14B-GGUF:Q4_K_M
hf.co/mradermacher/WhiteRabbitNeo-V3-7B-GGUF:Q4_K_M
hf.co/mradermacher/Fathom-Search-4B-GGUF:Q4_K_M
hf.co/lmstudio-community/gemma-3-12b-it-GGUF:Q4_K_M
```

### Q2_K (2-bit - Ultra Compact, Potential Quality Loss)

```text
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q2_K
```

### Q6_K (6-bit - Medium Compression)

```text
hf.co/lmstudio-community/txgemma-9b-chat-GGUF:Q6_K
```

### IQ2_M (Intermediate 2-bit)

```text
hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-1M-GGUF:IQ2_M
```

### Latest (Ollama Native)

```
qwen3:0.6b
qwen3:1.7b
qwen3:8b
gemma3:1b
gemma3:4b
gemma3:12b
smollm2:135m
hf.co/ApatheticWithoutTheA/Qwen-2.5-3B-Reasoning:latest
hf.co/DavidAU/Qwen3-8B-64k-Josiefied-Uncensored-NEO-Max-GGUF:latest
Qwen2.5-Coder-7B-Instruct-Q4_K_M-1739364715670:latest
llama3.2_3b_122824_uncensored.Q8_0-1739364637622:latest
```

---

## Embedding Models (Non-LLM)

```
linux6200/bge-reranker-v2-m3:latest
snowflake-arctic-embed:latest
granite-embedding:278m
mxbai-embed-large:335m
nomic-embed-text:latest
```

---

## Recommended Test Sets

### Quick Benchmark (5 models, ~10 min total)

```
qwen3:0.6b                                                     (baseline - fast)
gemma3:1b                                                      (baseline - quality)
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M         (math-specialized)
hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:F16               (general-purpose)
qwen3:8b                                                       (larger model)
```

### Math Focus (6 models, ~15 min total)

```
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:F16            (AceMath full)
hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M         (AceMath compressed)
hf.co/mradermacher/deepseek-math-7b-instruct-GGUF:Q4_K_M     (DeepSeek Math)
hf.co/mradermacher/Thinking-Camel-7b-GGUF:Q4_K_M             (Thinking Camel)
hf.co/mradermacher/ARWKV-R1-1B5-GGUF:F16                      (ARWKV-R1)
hf.co/mradermacher/Fathom-R1-14B-GGUF:Q4_K_M                 (Fathom-R1)
```

### Reasoning Focus (5 models, ~12 min total)

```
hf.co/unsloth/Qwen3-4B-Thinking-2507-GGUF:Q8_0               (Qwen thinking)
hf.co/ApatheticWithoutTheA/Qwen-2.5-3B-Reasoning:latest       (Qwen reasoning)
hf.co/mradermacher/Thinking-Camel-7b-GGUF:Q4_K_M             (Thinking Camel)
hf.co/mradermacher/ARWKV-R1-1B5-GGUF:F16                      (ARWKV-R1)
hf.co/mradermacher/Fathom-R1-14B-GGUF:Q4_K_M                 (Fathom-R1)
```

### Efficiency Focus (7 models, ~15 min total - small models only)

```
smollm2:135m
hf.co/unsloth/gemma-3-270m-it-GGUF:F16
mollysama/rwkv-7-g1:0.1B
mollysama/rwkv-7-g1:0.4b
qwen3:0.6b
hf.co/lmstudio-community/Falcon3-1B-Instruct-GGUF:Q8_0
gemma3:1b
```

---

## Summary Statistics

- **Total Models:** 41 (36 LLMs + 5 embedding models)
- **Total LLMs:** 36
- **Average Model Size:** ~5B parameters
- **Median Model Size:** ~1.5B parameters
- **Smallest:** smollm2:135m
- **Largest:** hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-1M-GGUF:IQ2_M
- **Most Represented Family:** Gemma3 (6 variants) and Qwen (7 variants including Qwen3)

---

## Notes for Testing

1. **Math-specialized models** are excellent for arithmetic expression evaluation
2. **Reasoning models** (R1, Thinking variants) may have different prompt requirements
3. **Quantization matters:** F16 is highest quality, Q2_K is most compressed
4. **RWKV series** uses different architecture (RNN-based, not transformer)
5. **Embedding models** won't work for text generation tasks


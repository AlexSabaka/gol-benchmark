# Encoding & Cipher Decoding

> **Task type:** `encoding_cipher` | **Answer type:** Decoded text / response word

Tests LLM ability to decode encoded messages and follow embedded instructions. Two task modes: decode-only (return the plaintext) and decode-and-act (decode an instruction and reply with a single word). Covers Base64, Caesar cipher (configurable shifts), and Morse code. Detects hallucinated execution where models produce the right response word without actually decoding.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Message encoding with 3 schemes, 2 task modes, configurable message lengths |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Response parsing with refusal detection and multi-strategy extraction |
| `evaluator.py` | 5-type failure taxonomy with hallucination detection |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `count` | number | 30 | Total test cases |
| `task_modes` | multi-select | both | `decode_only`, `decode_and_act` |
| `encoding_types` | multi-select | all | `base64`, `caesar`, `morse` |
| `caesar_shifts` | multi-select | [3, 7, 13] | Caesar cipher shift values |
| `message_length` | select | medium | `short` (3-8 words), `medium` (8-20), `long` (20-40) |
| `mode_weights` | weight_map | equal | Distribution across task modes |

## Parsing Strategies

1. **refusal_detection** — checks for refusal patterns before extraction
2. **boxed** — `{answer}` or `\boxed{answer}`
3. **labelled_answer** — "The answer is X"
4. **equals_pattern** — "= X" patterns
5. **bold** — `**answer**`
6. **last_symbol** — last word/symbol in response
7. **encoding-type-specific** — specialized patterns per encoding scheme

Returns decoded plaintext or `REFUSAL_SENTINEL`.

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention). Unicode whitespace normalization and punctuation-stripped comparison applied (v2.10.6).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Exact match (case-insensitive, whitespace-trimmed) |
| `hallucinated_execution` | Right response word but no evidence of actual decoding (decode_and_act only) |
| `paranoid_refusal` | Model refused to decode the message |
| `wrong_decode` | Answer extracted but incorrect |
| `parse_error` | Could not extract an answer |

**Hallucination detection** (decode_and_act): checks if >= 40% of plaintext words appear in the raw response. If the model produces the correct response word without showing decoding work, it's flagged as hallucinated execution.

**Scoring:** 1.0 for `correct`, 0.0 for everything else.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context

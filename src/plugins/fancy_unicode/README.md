# fancy_unicode — Fancy Unicode Normalization

> **Task type:** `fancy_unicode` | **Answer type:** decoded plaintext / single response word

Tests LLM ability to recognise and normalise decorative Unicode encodings back to
standard ASCII, and to follow instructions embedded in the decoded text.  Covers
math-script fonts, small caps, fullwidth, enclosed/squared alphanumerics,
superscript/subscript, and combining-dot variants.

Unlike `encoding_cipher` (which explicitly labels the encoding type), this plugin
presents decorated text as-is — the model must identify the Unicode style on its
own.  This surfaces failure modes that are specific to each family and reveals
world-knowledge bypass behaviours.

---

## Module Structure

| File | Purpose |
|------|---------|
| `families.py` | Per-family codepoint mapping tables; `encode_text()`, `decode_to_ascii()`, coverage metadata |
| `generator.py` | Test-case generation; coverage filtering; `decode_only` and `decode_and_act` routing |
| `parser.py` | Multi-strategy end-first parsing; refusal and runaway detection |
| `evaluator.py` | 7-type failure taxonomy; per-family aggregate metrics |
| `i18n.yaml` | User prompt templates (EN, 3 styles) |

---

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `count` | number | 30 | Total test cases |
| `task_modes` | multi-select | both | `decode_only`, `decode_and_act` |
| `encoding_families` | multi-select | `tier_1` | Family names or tier shortcuts (`tier_1`–`tier_3`, `all`) |
| `message_length` | select | medium | `short` (3–8 w), `medium` (8–20 w), `long` (20–40 w) — decode_only only |
| `mode_weights` | weight_map | equal | Sampling distribution across task modes |

---

## Encoding Families

### Tier 1 — full A–Z a–z

| Family | Example | Unicode block |
|--------|---------|--------------|
| `math_script_bold` | `𝓼𝓽𝓻𝓪𝔀𝓫𝓮𝓻𝓻𝔂` | Mathematical Bold Script (U+1D4D0) |
| `math_italic` | `𝘴𝘵𝘳𝘢𝘸𝘣𝘦𝘳𝘳𝘺` | Mathematical Sans-Serif Italic (U+1D608) |
| `math_monospace` | `𝚜𝚝𝚛𝚊𝚠𝚋𝚎𝚛𝚛𝚢` | Mathematical Monospace (U+1D670) |
| `fullwidth` | `ｓｔｒａｗｂｅｒｒｙ` | Halfwidth and Fullwidth Forms (U+FF41) |

### Tier 2 — partial coverage

| Family | Example | Coverage |
|--------|---------|---------|
| `small_caps` | `ꜱᴛʀᴀᴡʙᴇʀʀʏ` | 24/26 — missing q, x |
| `superscript` | `ˢᵗʳᵃʷᵇᵉʳʳʸ` | 21/26 — missing c, f, q, x, z |
| `subscript` | `ₛₜᵣₐwbₑᵣᵣy` | 17/26 — missing b, c, d, f, g, q, w, y, z |
| `circled` | `Ⓢⓣⓡⓐⓦⓑⓔⓡⓡⓨ` | Full A–Z a–z (U+24B6 / U+24D0) |

Word and sentence pools are filtered per family at generation time to ensure
every alphabetic character has a defined codepoint.

### Tier 3 — uppercase only / combining

| Family | Example | Notes |
|--------|---------|-------|
| `squared` | `🅂🅃🅁🄰🅆🄱🄴🅁🅁🅈` | A–Z (U+1F130); input uppercased before encoding |
| `negative_squared` | `🅳🅴🅲🅾🅳🅴` | A–Z (U+1F170) |
| `negative_circled` | `🅓🅔🅒🅞🅓🅔` | A–Z (U+1F150) |
| `dotted_script` | `𝓼̇𝓽̇𝓻̇𝓪̇𝔀̇` | Math Bold Script + U+0307 combining dot above |

---

## Task Modes

### `decode_only`
Present a sentence encoded in a given family.  Model must recognise the style,
decode, and return the plain text.

**Prompt (casual):**
> Hey, quick one — got this funky text, what does it say?
>
> `𝓣𝓱𝓮 𝓻𝓲𝓿𝓮𝓻 𝓻𝓪𝓷 𝓼𝓲𝓵𝓮𝓷𝓽𝓵𝔂 𝓹𝓪𝓼𝓽 𝓽𝓱𝓮 𝓸𝓵𝓭 𝓼𝓽𝓸𝓷𝓮 𝓶𝓲𝓵𝓵.`

**Ground truth:** `The river ran silently past the old stone mill.`

### `decode_and_act`
Present an action instruction encoded in a given family.  Model must decode the
instruction and comply — returning a single response word.

**Prompt (casual):**
> Hey, quick one — got this funky message. Decode it and do what it says.
>
> `𝓣𝓱𝓮 𝓼𝓮𝓬𝓻𝓮𝓽 𝔀𝓸𝓻𝓭 𝓲𝓼: 𝓪𝓵𝓬𝓱𝓮𝓶𝔂. 𝓡𝓮𝓹𝓵𝔂 𝔀𝓲𝓽𝓱 𝓸𝓷𝓵𝔂 𝓽𝓱𝓪𝓽 𝔀𝓸𝓻𝓭.`

**Ground truth:** `alchemy`

---

## Parsing Strategies

Applied in order (end-first convention); first match wins.

**decode_and_act:**
`single_word` → `normalized_first_line` → `boxed` → `labelled_answer` → `labelled_word` → `quoted_word` → `bold_word` → `last_word`

`normalized_first_line` decodes any fancy Unicode in the first response line and
checks whether it is a single alphabetic word — handles models that echo the
encoded answer verbatim before explaining.

**decode_only:**
`boxed` → `labelled_answer` → `bold` → `last_line`

---

## Failure Taxonomy

| Match type | Meaning |
|------------|---------|
| `correct` | Exact match after NFKD + reverse-map normalisation |
| `bypassed_decode` | decode_and_act: correct word, but <40 % of plaintext words in response (world-knowledge bypass) |
| `hallucinated_decode` | decode_and_act: wrong word, confident decode claim that doesn't match real plaintext |
| `paranoid_refusal` | Model refused to process the text |
| `runaway_refusal` | Response hit max_tokens without a parseable answer |
| `wrong_decode` | Answer extracted but incorrect |
| `parse_error` | Could not extract any usable response |

---

## Key Metrics

`aggregate_results()` returns:

- **`by_family`** — per-family accuracy, bypassed_decode_rate, paranoid_refusal_rate, runaway_refusal_rate ← *primary research output*
- **`by_mode`** — accuracy per task mode
- **`by_match_type`** — counts of all 7 taxonomy types
- Suite-level rate fields: `bypassed_decode_rate`, `hallucinated_decode_rate`, `paranoid_refusal_rate`, `runaway_refusal_rate`, `wrong_decode_rate`, `parse_error_rate`

The capability cliff between families on the same model (e.g. `math_script_bold`
correct, `negative_squared` catastrophic) is the primary research finding.
Cross-model comparison of which family each model "understands" correlates with
training data frequency of that Unicode block.

---

## Notes

- **Language:** EN only. Unicode decoration is language-agnostic at the codepoint
  level; multilingual extension is possible but non-trivial due to coverage gaps in
  non-Latin scripts.
- **max_tokens guard:** Tier-3 families can trigger token-loop behaviour in small
  models.  Set per-test `max_tokens` conservatively and flag responses that hit
  the limit (`hit_max_tokens` in `task_params`) — the evaluator classifies these
  as `runaway_refusal`.
- **Decode normalisation:** The evaluator applies a full reverse-map lookup
  (covering all 12 families) before NFKD, so models that echo the answer still
  encoded are credited correctly.

---

## Relation to Other Plugins

| Plugin | Overlap | Distinction |
|--------|---------|------------|
| `encoding_cipher` | Both test decoding; share `decode_and_act` mode | `encoding_cipher` labels the encoding type explicitly. `fancy_unicode` does not — the model must identify the style. |
| `strawberry` | Both touch character-level reasoning | `strawberry` reasons *about* characters. `fancy_unicode` normalises *away* from non-standard codepoints before any reasoning. |

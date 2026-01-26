# Sally-Anne False Belief Test - Implementation Complete ✅

**Date**: January 26, 2026
**Status**: Production Ready 🚀
**Version**: 1.0.0

## Overview

Successfully implemented the Sally-Anne false belief test plugin for Theory of Mind assessment. This plugin tests LLMs' ability to understand that others can hold false beliefs about object locations.

## Key Distinction from Grape Test (Object Tracking)

| Feature | Grape Test (Physical Causality) | Sally-Anne Test (Theory of Mind) |
|---------|--------------------------------|----------------------------------|
| **Cognitive Challenge** | Physical reasoning (gravity, inversion) | Mental state attribution (false beliefs) |
| **Correct Answer** | Where object ACTUALLY is | Where Subject A BELIEVES it is |
| **Common Error** | "Reality leap" (ignoring physics) | "Reality trap" (answering actual location) |
| **Test Focus** | Tracking physical events | Understanding knowledge states |

## Implementation Details

### 1. Plugin Architecture (`src/plugins/sally_anne/`)

#### Files Created:
- **`__init__.py` (160 lines)**: Plugin registration with `SallyAnnePlugin` class
  - Implements `BenchmarkPlugin` interface
  - Default configuration with classic Sally/Anne pair
  - Backward-compatible `create_*` methods
  
- **`scenario_builder.py` (220 lines)**: Scenario generation with random names
  - **Names Library Integration**: Uses `names` pip package for diverse name generation
  - **Gender-Based Pronouns**: Automatically handles he/she/him/her/his based on gender
  - **Observer Variant**: Optional third-person witness
  - **Distractor Support**: Configurable scene complexity
  
- **`generator.py` (180 lines)**: Test case generator
  - Random or specified subject pairs
  - Configurable objects, containers, activities
  - Generates full TestCase objects with task_params
  
- **`parser.py` (220 lines)**: Multi-strategy response parser
  - 5 parsing strategies (JSON, boxed, keywords, last word, full text)
  - Synonym matching for container variations
  - Metadata-aware normalization
  
- **`evaluator.py` (190 lines)**: Result evaluator with reality trap detection
  - **Critical Logic**: Distinguishes belief location (correct) vs actual location (reality trap)
  - Match types: `exact`, `synonym`, `reality_trap`, `parse_error`, `wrong_container`
  - Aggregate statistics with reality trap rate

### 2. PromptEngine Integration (`src/core/PromptEngine.py`)

**Added `SALLY_ANNE` task type** and comprehensive templates:
- **6 Languages**: EN, ES, FR, DE, ZH, UA
- **4 Prompt Styles**: linguistic, casual, minimal, adversarial
- **Theory of Mind Emphasis**: Templates highlight belief-based reasoning
- Example (EN, linguistic):
  ```
  This is a test of understanding beliefs and knowledge states.
  Consider what each person knows based on what they have witnessed.
  
  Key reasoning principles:
  1. A person's belief about an object's location is based on what they last saw
  2. If someone is absent when an object is moved, they don't know about the move
  3. The person will look where they believe the object is, not where it actually is
  ```

### 3. TUI Integration (`src/cli/benchmark_tui.py`)

**Added sally_anne to 3 key sections:**

#### Task Selection (line ~350):
```python
{'id': 'sally_anne', 'name': 'Sally-Anne (False Belief)', 
 'description': 'Theory of Mind false belief reasoning test'}
```

#### Quick Config Defaults (line ~473):
```python
elif task_id == 'sally_anne':
    parameters = {
        'use_random_pairs': True,
        'objects': ['marble', 'ball', 'toy'],
        'containers': [('basket', 'box'), ('drawer', 'cupboard')],
        'distractor_count': 0,
        'leave_activities': ['goes for a walk', 'goes outside', 'leaves the room'],
        'include_observer': False
    }
```

#### Custom Configuration UI (lines ~873-965):
- **Subject Pairs**: Toggle random (names library) vs manual pairs
  - Manual format: `name1,gender1,name2,gender2` (e.g., `Sally,female,Anne,female`)
- **Objects**: Comma-separated (marble, ball, toy, book, keys)
- **Container Pairs**: Format `initial:moved` (e.g., `basket:box`)
- **Leave Activities**: What Subject A does when leaving (configurable)
- **Distractors**: 0-3 extra scene elements
- **Observer Variant**: Toggle third-person witness

#### Task Type Mapping (line ~1530):
```python
'sally_anne': 'sally_anne'
```

#### YAML Generation (lines ~1610-1625):
```yaml
generation:
  cases_per_config: 5
  objects: ['marble', 'ball', 'toy']
  containers: [['basket', 'box'], ['drawer', 'cupboard']]
  distractor_count: 0
  leave_activities: ['goes for a walk', 'goes outside']
  include_observer: false
  subject_pairs: []  # Empty = random names
```

### 4. Results Analysis (`src/stages/analyze_results.py`)

**Added task extraction (line ~151)**:
```python
elif '_sally_anne' in test_id or '_false_belief' in test_id:
    task_type = 'sally_anne'
```

## Configuration Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `use_random_pairs` | bool | Use names library for random subject pairs | `true` |
| `subject_pairs` | list[tuple] | Manual pairs: (name1, gender1, name2, gender2) | `[('Sally', 'female', 'Anne', 'female')]` |
| `objects` | list[str] | Items to be moved | `['marble', 'ball', 'toy', 'book', 'keys']` |
| `containers` | list[tuple] | (initial, moved) container pairs | `[('basket', 'box'), ('drawer', 'cupboard')]` |
| `leave_activities` | list[str] | What Subject A does when leaving | `['goes for a walk', 'goes outside']` |
| `distractor_count` | int | Number of scene distractors (0-3) | `0` |
| `include_observer` | bool | Add third-person witness | `false` |
| `cases_per_config` | int | Test cases to generate | `5` |

## Testing

**Integration Tests** (`tests/test_sally_anne_integration.py`): 413 lines

### Test Coverage:
1. ✅ Plugin registration and discovery
2. ✅ Random name generation with pronouns
3. ✅ Observer variant scenarios
4. ✅ Narrative and question building
5. ✅ Test case generation (3 cases)
6. ✅ Multi-strategy response parsing (5 strategies)
7. ✅ Result evaluation (belief vs reality trap)
8. ✅ Aggregate statistics
9. ✅ PromptEngine integration
10. ✅ TUI integration verification
11. ✅ analyze_results task extraction
12. ✅ End-to-end workflow

**All tests passing** ✅

## Usage Examples

### 1. TUI Quick Start
```bash
python src/cli/benchmark_tui.py
# Select "Sally-Anne (False Belief)" from task list
# Configure parameters or use defaults
# Execute 3-stage pipeline automatically
```

### 2. Manual YAML Configuration
```yaml
metadata:
  name: "sally_anne_baseline"
  description: "Theory of Mind false belief test"

tasks:
  - type: "sally_anne"
    generation:
      seed: 42
      cases_per_config: 10
      objects: ['marble', 'ball', 'toy']
      containers:
        - ['basket', 'box']
        - ['drawer', 'cupboard']
      distractor_count: 0
      leave_activities:
        - 'goes for a walk'
        - 'goes outside'
      include_observer: false
      subject_pairs: []  # Empty = random names
    
    prompt_configs:
      - name: "minimal_analytical"
        user_style: "minimal"
        system_style: "analytical"

sampling:
  temperature: 0.1
  max_tokens: 128

execution:
  no_thinking: true
```

### 3. Command Line (3-Stage Pipeline)
```bash
# Stage 1: Generate test set
python src/stages/generate_testset.py configs/sally_anne_config.yaml

# Stage 2: Execute on models
python src/stages/run_testset.py testsets/testset_sally_anne_*.json.gz \
    --model qwen3:0.6b --provider ollama --output-dir results/

# Stage 3: Analyze results
python src/stages/analyze_results.py results/results_sally_anne_*.json.gz \
    --output reports/sally_anne_report.md --visualize
```

## Expected Performance

### Accuracy Predictions:
- **High-capability models** (GPT-4, Claude): 70-90% (understand false beliefs)
- **Mid-tier models** (Qwen, Gemma): 40-60% (some Theory of Mind)
- **Small models** (<1B params): 20-40% (struggle with mental states)

### Common Errors:
1. **Reality Trap** (40-60% of errors): Answering actual location instead of belief
2. **Parse Errors** (10-20%): Inability to extract container name
3. **Wrong Container** (20-30%): Random incorrect answer

## Key Implementation Decisions

### 1. Random Names with Gender-Based Pronouns
**Rationale**: Increases test diversity and tests pronoun handling. The `names` library provides:
- Real first names from global database
- Gender-specific selection
- Automatic pronoun mapping (he/she/him/her/his)

**Trade-off**: Requires `names` pip package (fallback to predefined lists if missing)

### 2. Configurable Leave Activities
**Rationale**: Allows testing different absence scenarios:
- "goes for a walk" (classic Sally-Anne)
- "goes outside" (general)
- "leaves the room" (specific)
- "goes to the kitchen" (detailed)

### 3. Observer Variant as Optional
**Rationale**: Tests second-order Theory of Mind:
- Basic: Can Subject A know object location?
- Observer: Does observer know that Subject A doesn't know?

### 4. Reality Trap as Primary Error Metric
**Rationale**: Distinguishes between:
- **Correct**: Understanding false beliefs
- **Reality Trap**: Defaulting to physical reality
- **Other Errors**: Random mistakes or parsing failures

## Integration Points

### Plugin Registry
- Auto-discovered via `src/plugins/__init__.py`
- Available in `PluginRegistry.list_task_types()`
- Accessible via `PluginRegistry.get('sally_anne')`

### 3-Stage Pipeline
1. **generate_testset.py**: Creates test cases with random names, configurable parameters
2. **run_testset.py**: Executes on models, parses responses (5 strategies)
3. **analyze_results.py**: Evaluates with reality trap detection, generates reports

### TUI Workflow
- Task selection → Configuration (basic + advanced) → YAML generation → Execution → Analysis

## Comparison with Object Tracking

| Aspect | Object Tracking (Grape Test) | Sally-Anne Test |
|--------|------------------------------|-----------------|
| **Implementation** | `src/plugins/object_tracking/` | `src/plugins/sally_anne/` |
| **Test Focus** | Physical causality | Mental state attribution |
| **Key Event** | Container inversion | Subject A's absence |
| **Correct Answer** | Where object fell (actual location) | Where Subject A believes it is |
| **Error Type** | "Reality leap" (ignore physics) | "Reality trap" (ignore beliefs) |
| **Difficulty Factors** | Distractors, post-inversion moves | Distractors, observer complexity |
| **Name Library** | Not used | **Uses `names` for diversity** |
| **Pronouns** | Fixed (first person "I") | **Gender-based (he/she/his/her)** |

## Next Steps

### Potential Enhancements:
1. **Difficulty Levels**: Based on distractor count, observer presence
2. **Second-Order Beliefs**: "Does the observer know that Subject A doesn't know?"
3. **Multiple Transfers**: Object moved multiple times
4. **Explicit False Belief Questions**: "What does Subject A think?"
5. **Culturally Diverse Names**: Expand names library usage

### Research Applications:
- **Theory of Mind Benchmarking**: Compare models' ability to attribute mental states
- **Cognitive Development**: Track emerging capabilities in model scaling
- **Cross-Lingual Testing**: 6 languages for multilingual evaluation
- **Pronoun Handling**: Test gender pronoun accuracy

## Files Modified/Created

### Created (5 files):
1. `src/plugins/sally_anne/__init__.py` (160 lines)
2. `src/plugins/sally_anne/scenario_builder.py` (220 lines)
3. `src/plugins/sally_anne/generator.py` (180 lines)
4. `src/plugins/sally_anne/parser.py` (220 lines)
5. `src/plugins/sally_anne/evaluator.py` (190 lines)
6. `tests/test_sally_anne_integration.py` (413 lines)

### Modified (3 files):
1. `src/core/PromptEngine.py` (+180 lines)
   - Added `TaskType.SALLY_ANNE` enum
   - Added `SALLY_ANNE_PROMPTS` dict (6 languages × 4 styles)
   - Registered in PromptEngine initialization

2. `src/cli/benchmark_tui.py` (+110 lines)
   - Added sally_anne to available_tasks
   - Added quick config defaults
   - Added custom configuration UI (8 parameters)
   - Added task type mapping
   - Added YAML generation logic

3. `src/stages/analyze_results.py` (+3 lines)
   - Added sally_anne task type extraction

## Dependencies

### Required:
- `names` (pip package): Random name generation with gender support
- Standard library: `random`, `itertools`, `datetime`, `re`, `json`

### Installation:
```bash
pip install names
```

### Fallback:
If `names` not available, uses predefined name lists:
- `MALE_NAMES = ['Alex', 'Ben', 'Charlie', ...]`
- `FEMALE_NAMES = ['Alice', 'Beth', 'Clara', ...]`

## Verification

Run integration tests:
```bash
./bin/python tests/test_sally_anne_integration.py
```

Expected output:
```
============================================================
SALLY-ANNE FALSE BELIEF TEST - INTEGRATION TESTS
============================================================

✓ Plugin registration verified
✓ Random scenario: Ethan (gender: male) and David
✓ Observer scenario: Observer Beth watches Sally and Anne
✓ Narrative and question generation verified
✓ Generated 3 test cases
✓ Response parser verified (5 strategies)
✓ Result evaluator verified
✓ Aggregate results: 40% accuracy, 1 reality traps
✓ PromptEngine integration verified
✓ TUI integration verified (sally_anne in available tasks)
✓ analyze_results task extraction verified
✓ End-to-end workflow verified

============================================================
✓ ALL TESTS PASSED
============================================================
```

## Conclusion

The Sally-Anne false belief test plugin is **fully implemented and production-ready**. It provides:

✅ Complete plugin architecture with auto-discovery
✅ Random name generation with proper pronoun handling
✅ Multi-language support (6 languages)
✅ Rich TUI configuration (8 parameters)
✅ Multi-strategy parsing (5 strategies)
✅ Reality trap detection and analysis
✅ Full 3-stage pipeline integration
✅ Comprehensive test coverage (12 test scenarios)

The plugin is ready for benchmarking LLMs' Theory of Mind capabilities and can be used immediately via TUI, YAML configs, or command line.

---

**Implementation Date**: January 26, 2026
**Total Lines of Code**: ~1,483 lines (plugin + tests)
**Status**: ✅ Production Ready

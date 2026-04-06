# LLM Judge Report

**Judge model:** gpt-oss:120b-cloud
**Provider:** ollama
**Date:** 2026-04-06T11:20:59
**Duration:** 156.9s
**Source files:** results_google_gemma-2-27b-it_20260406_105956.json.gz, results_google_gemma-4-26b-a4b-it_20260406_110315.json.gz, results_google_gemma-3-27b-it_20260406_110431.json.gz

## Summary

| Verdict | Count | % |
|---------|------:|--:|
| True Incorrect | 50 | 87.7% |
| False Negative | 0 | 0.0% |
| Parser Failure | 7 | 12.3% |
| **Total** | **57** | |

### Parser Issue Breakdown

| Issue Type | Count |
|-----------|------:|
| format mismatch | 7 |

### Key Findings

- **7/7 parser failures** are `carwash` (lang: ua, issues: format_mismatch)


## Parser Failures (7)

The model gave a correct answer but the parser failed to extract it.

### Task: `carwash` (7 failures)

| Test ID | Model | Lang | Issue | Parsed | Expected | Notes |
|---------|-------|------|-------|--------|----------|-------|
| carwash_42_0000 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Correct answer present as Ukrainian phrase, not extracted as expected token |
| carwash_42_0004 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Correct answer given in Ukrainian phrase, not the expected English token |
| carwash_42_0009 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Model says "Їхати на машині" but parser didn't capture it |
| carwash_42_0003 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Correct answer present in Ukrainian, parser expected English token |
| carwash_42_0004 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Model answered correctly in Ukrainian, parser expected English token 'drive' |
| carwash_42_0005 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Correct recommendation given, but not in expected 'drive' token format |
| carwash_42_0008 | google/gemma-4-26b-a4b-it | ua | format mismatch | (no extraction) | `drive` | Model answered in Ukrainian phrase, not the expected token 'drive' |

<details><summary>Response samples (5 of 7)</summary>

**carwash_42_0000** (google/gemma-4-26b-a4b-it, ua):
```
Для надання максимально точної та логічно обґрунтованої відповіді, я проаналізую цю ситуацію через призму декількох аналітичних параметрів: логістики, економічної доцільності, енерговитрат та операційної ефективності.

### 1. Аналіз вхідних даних
*   **Об'єкт:** Брудна автомобільна одиниця.
*   **Ціль:** Доставити автомобіль на мийку.
*   **Відстань/Час:** 2 хвилини пішки.
*   **Варіанти дії:**
  
...
```

**carwash_42_0004** (google/gemma-4-26b-a4b-it, ua):
```
Для надання максимально точної та логічно обґрунтованої відповіді, я проаналізую ситуацію за допомогою декількох критичних параметрів: логіки процесу, фізичних факторів та операційної ефективності.

### 1. Аналіз вхідних даних
*   **Об'єкт:** Автомобіль, що забруднений багнюкою.
*   **Мета:** Доставити автомобіль на мийку.
*   **Відстань:** 100 метрів.
*   **Варіанти дії:** 
    1.  Їхати на машин
...
```

**carwash_42_0009** (google/gemma-4-26b-a4b-it, ua):
```
Прийнято. Переходжу в режим експертного аналізу.

Для розв'язання цієї задачі я застосую метод багатофакторного порівняння, де буду оцінювати обидва варіанти (піша прогулянка проти поїздки на автомобілі) за декількома критичними параметрами: часовими витратами, логістичною доцільністю, ресурсами та контекстуальними факторами.

### 1. Декомпозиція вхідних даних
*   **Об'єкт:** Брудна машина.
*   **
...
```

**carwash_42_0003** (google/gemma-4-26b-a4b-it, ua):
```
Привіт! Однозначно **їхати на машині**.

Ось чому це логічніше:
1. **Чистота:** Якщо машина в багнюці, ви просто забрудните одяг і взуття, поки йтимете пішки.
2. **Ефективність:** 200 метрів на авто — це зайва хвилина, але це позбавить вас необхідності потім відмивати себе.
3. **Зручність:** Ви одразу опинитеся на місці з машиною, яку потрібно мити.

Їдьте і мийте!
```

**carwash_42_0004** (google/gemma-4-26b-a4b-it, ua):
```
Привіт! У цій ситуації я обираю **їхати на машині**.

Це логічно: машина вже брудна, і їхати на ній 100 метрів — це швидше і зручніше, ніж йти пішки, особливо якщо ви хочете одразу заїхати на мийку. До того ж, це мінімізує ваші зусилля.
```

</details>


## True Incorrect (50)

Genuinely wrong model responses — no parser fix needed.

| Test ID | Model | Lang | Confidence | Notes |
|---------|-------|------|-----------|-------|
| carwash_42_0000 | google/gemma-2-27b-it | ua | high | Model recommends walking, but expected answer is drive |
| carwash_42_0001 | google/gemma-2-27b-it | ua | high | Model recommends walking, but expected answer is drive |
| carwash_42_0002 | google/gemma-2-27b-it | ua | high | Model gave indecisive discussion, not the expected 'drive' answer |
| carwash_42_0003 | google/gemma-2-27b-it | ua | high | Model gave balanced analysis, no clear 'drive' recommendation |
| carwash_42_0004 | google/gemma-2-27b-it | ua | high | Model recommends walking, but expected answer is to drive the car to the wash |
| carwash_42_0005 | google/gemma-2-27b-it | ua | high | Model recommends walking, expected recommendation is to drive |
| carwash_42_0006 | google/gemma-2-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0007 | google/gemma-2-27b-it | ua | high | Model concludes walking is best, but expected answer is to drive |
| carwash_42_0008 | google/gemma-2-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0009 | google/gemma-2-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0000 | google/gemma-2-27b-it | ua | high | Model chose walking, expected drive |
| carwash_42_0001 | google/gemma-2-27b-it | ua | high | Model says walk, expected drive |
| carwash_42_0002 | google/gemma-2-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0003 | google/gemma-2-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0004 | google/gemma-2-27b-it | ua | high | Model chose walking; expected driving to bring car to wash |
| carwash_42_0005 | google/gemma-2-27b-it | ua | high | Model advises walking; expected recommendation is to drive |
| carwash_42_0006 | google/gemma-2-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0007 | google/gemma-2-27b-it | ua | high | Model says walk, expected drive |
| carwash_42_0008 | google/gemma-2-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0009 | google/gemma-2-27b-it | ua | high | Model chose walking, but expected answer is to drive |
| carwash_42_0002 | google/gemma-4-26b-a4b-it | ua | high | Model recommends walking, but expected answer is drive |
| carwash_42_0003 | google/gemma-4-26b-a4b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0006 | google/gemma-4-26b-a4b-it | ua | high | Model recommends walking, but car must be driven to wash |
| carwash_42_0008 | google/gemma-4-26b-a4b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0000 | google/gemma-4-26b-a4b-it | ua | high | Model chose walking, but expected answer is drive |
| carwash_42_0001 | google/gemma-4-26b-a4b-it | ua | high | Model chose walking, but expected answer is to drive the car |
| carwash_42_0002 | google/gemma-4-26b-a4b-it | ua | high | Model advises walking, but expected answer is drive |
| carwash_42_0006 | google/gemma-4-26b-a4b-it | ua | high | Model says walk; expected drive |
| carwash_42_0007 | google/gemma-4-26b-a4b-it | ua | high | Model says walking, expected driving |
| carwash_42_0009 | google/gemma-4-26b-a4b-it | ua | high | Model chose walking, but expected answer is drive |
| carwash_42_0000 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0001 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0002 | google/gemma-3-27b-it | ua | high | Model advised walking, but expected answer is to drive |
| carwash_42_0003 | google/gemma-3-27b-it | ua | high | Model recommended walking, but expected answer is to drive |
| carwash_42_0004 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0005 | google/gemma-3-27b-it | ua | high | Model advises walking, but expected answer is drive |
| carwash_42_0006 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0007 | google/gemma-3-27b-it | ua | high | Model chose walking, but expected answer is drive |
| carwash_42_0008 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0009 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is drive |
| carwash_42_0000 | google/gemma-3-27b-it | ua | high | Model chose walking, expected drive |
| carwash_42_0001 | google/gemma-3-27b-it | ua | high | Model recommended walking, but expected answer is to drive |
| carwash_42_0002 | google/gemma-3-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0003 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected answer is to drive |
| carwash_42_0004 | google/gemma-3-27b-it | ua | high | Model returned timeout message, no answer provided |
| carwash_42_0005 | google/gemma-3-27b-it | ua | high | Model recommends walking, but expected recommendation is to drive |
| carwash_42_0006 | google/gemma-3-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0007 | google/gemma-3-27b-it | ua | high | Model says walk, but expected answer is drive |
| carwash_42_0008 | google/gemma-3-27b-it | ua | high | Model advises walking, but expected answer is to drive |
| carwash_42_0009 | google/gemma-3-27b-it | ua | high | Model chose walking, but expected answer is drive |

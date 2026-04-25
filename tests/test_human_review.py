"""Tests for the Human Review annotation feature.

Covers:
  * `_auto_regex` in the aggregator (anchor, disjunction, empty-safety)
  * `build_report` section shape on a synthetic annotation set
  * Router invariants (`POST /annotate` 400s on bad invariants)
  * End-to-end sidecar round-trip
  * Mixed-plugin `/cases` flag
"""
from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.web.app import app
from src.web import annotation_store as annotation_store_module
from src.web import human_review_aggregator as agg
from src.web import translation as trans
from src.web.api import analysis, human_review


# TestClient as a context manager so FastAPI's lifespan runs — the lifespan
# is what initializes the SQLite-backed AnnotationStore singleton. In older
# starlette versions ``client = TestClient(app)`` skipped lifespan entirely.
_client_ctx = TestClient(app)
_client_ctx.__enter__()
client = _client_ctx


def _clear_annotations() -> None:
    """Wipe all annotation rows — tests share the app-scope singleton."""
    try:
        store = annotation_store_module.get_store()
    except RuntimeError:
        return
    store._conn.execute("DELETE FROM annotations")


# ---------------------------------------------------------------------------
# _auto_regex
# ---------------------------------------------------------------------------


class TestAutoRegex:
    def test_empty_examples_returns_empty(self):
        assert agg._auto_regex([]) == []
        assert agg._auto_regex(["", "   "]) == []

    def test_common_anchor(self):
        out = agg._auto_regex(
            ["you should drive", "you should walk", "you should fly"]
        )
        assert out, "expected at least one regex candidate"
        assert out[0] == r"you\s+should\s+(\w+)"

    def test_disjunction_fallback_no_anchor(self):
        out = agg._auto_regex(
            [
                "i recommend drive",
                "i recommend walk",
                "you should run",
                "you should fly",
            ]
        )
        # Two distinct 2-word prefixes → disjunction.
        assert any("(?:" in c and "|" in c for c in out), f"expected disjunction, got {out}"

    def test_caps_at_three_candidates(self):
        examples = [f"some phrase_{i} answer" for i in range(10)]
        out = agg._auto_regex(examples)
        assert len(out) <= 3

    def test_ignores_single_char_anchor(self):
        # "a" alone is not a useful anchor, should fall through.
        out = agg._auto_regex(["a dog", "a cat"])
        # Either produces no anchor-form candidate, or picks the bigram fallback.
        # Crucially: no lone `a\s+(\w+)` pattern.
        assert all(c != r"a\s+(\w+)" for c in out)


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def _ann_case(
    case_id: str,
    spans: List[Dict[str, Any]] = None,
    response_class: str = None,
    parser_match_type: str = "parse_error",
    parser_extracted=None,
) -> Dict[str, Any]:
    # v3: response_class → response_classes array. Apply renames + drop parser_ok.
    _RENAME = {"verbose_correct": "verbose", "parser_false_positive": "false_positive"}
    rcs: list[str] = []
    if response_class and response_class != "parser_ok":
        rcs = [_RENAME.get(response_class, response_class)]
    return {
        "case_id": case_id,
        "response_length": 200,
        "parser_match_type": parser_match_type,
        "parser_extracted": parser_extracted,
        "expected": "drive",
        "annotation": {
            "spans": spans or [],
            "response_classes": rcs,
            "annotator_note": "",
            "timestamp": "2026-04-15T12:00:00Z",
        },
    }


def _span(text: str, position: str = "end", fmt: str = "plain") -> Dict[str, Any]:
    return {
        "text": text,
        "char_start": 0,
        "char_end": len(text),
        "position": position,
        "format": fmt,
    }


def test_build_report_produces_four_sections():
    af = {
        "meta": {"annotated_count": 6, "skipped_count": 1, "plugin": "carwash"},
        "cases": {
            "a": _ann_case("a", spans=[_span("you should drive")]),
            "b": _ann_case("b", spans=[_span("you should walk")]),
            "c": _ann_case("c", spans=[_span("you should fly")]),
            "d": _ann_case("d", spans=[_span("you should drive")]),
            "e": _ann_case("e", spans=[_span("drive")], parser_match_type="correct", parser_extracted="drive"),
            "f": _ann_case("f", response_class="hedge"),
        },
    }

    report = agg.build_report([af], source_files=["results_carwash.json.gz"])

    # Section 1: summary
    s = report["summary"]
    assert s["total_cases"] == 6
    assert s["parser_was_correct"] == 1
    # Cases a,b,c,d have spans but no parser_extracted → missed
    assert s["parser_missed_extractable"] == 4
    assert s["true_unparseable"] == 1

    # Section 2: one span group at (end, plain) with count=5 (a,b,c,d + e)
    groups = report["span_groups"]
    assert len(groups) == 1
    g = groups[0]
    assert (g["position"], g["format"]) == ("end", "plain")
    assert g["count"] == 5
    assert g["suggested_strategy"] == "last_sentences"
    assert g["missed_by_existing"] is True
    # v2.2: with no `before` context in these synthetic spans, the text-pattern
    # fallback kicks in (legacy behavior) and still produces candidates.
    assert g["suggested_regex"], "expected at least one regex candidate (text_pattern fallback)"
    assert any(r["kind"] == "text_pattern" for r in g["suggested_regex"])

    # Section 3: ordering hint fires for ≥4 end/plain + missed
    assert len(report["ordering_hints"]) == 1
    assert "end_sentences" in report["ordering_hints"][0]["recommendation"]

    # Section 4: response classes folded into summary (v2.5)
    c = report["summary"]["response_class_counts"]
    assert c["hedge"] == 1
    # parser_ok is auto-inferred at aggregation time, no longer stored as a class
    assert c["parser_missed"] == 5  # all 5 span-bearing cases (a,b,c,d,e)


def test_build_report_handles_empty_inputs():
    report = agg.build_report([], source_files=[])
    assert report["summary"]["total_cases"] == 0
    assert report["span_groups"] == []
    # v2.5 — empty ordering_hints / annotator_notes are omitted entirely.
    assert "ordering_hints" not in report
    assert "annotator_notes" not in report


# ---------------------------------------------------------------------------
# Router invariants + sidecar round-trip
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_result(tmp_path: Path, monkeypatch):
    """Write a tiny result file into a sandboxed results dir."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    data = {
        "metadata": {},
        "model_info": {"model_name": "test-model", "provider": "ollama"},
        "testset_metadata": {"name": "hr_test"},
        "execution_info": {"duration_seconds": 1.0},
        "summary_statistics": {},
        "results": [
            {
                "test_id": "carwash_0001",
                "status": "success",
                "input": {
                    "user_prompt": "Walk or drive?",
                    "system_prompt": "You are pragmatic.",
                    "task_params": {"task_type": "carwash", "expected_answer": "drive"},
                    "prompt_metadata": {"language": "en", "user_style": "casual"},
                },
                "output": {
                    "raw_response": "After some thought, you should drive.",
                    "parsed_answer": None,
                },
                "evaluation": {"correct": False, "match_type": "parse_error"},
            },
            {
                "test_id": "carwash_0002",
                "status": "success",
                "input": {
                    "user_prompt": "Walk or drive?",
                    "system_prompt": "You are pragmatic.",
                    "task_params": {"task_type": "carwash", "expected_answer": "drive"},
                    "prompt_metadata": {"language": "en", "user_style": "casual"},
                },
                "output": {"raw_response": "", "parsed_answer": None},
                "evaluation": {"correct": False, "match_type": "parse_error"},
            },
        ],
    }
    rf = results_dir / "results_test-model_2026-04-15T12-00-00.json.gz"
    with gzip.open(rf, "wt", encoding="utf-8") as f:
        json.dump(data, f)

    # Patch results-dir lookup for both routers.
    monkeypatch.setattr(analysis, "_results_dirs", lambda: [results_dir])

    # Annotations now live in the shared SQLite singleton (sandboxed under
    # GOL_DATA_ROOT via conftest.py). Wipe rows before and after so tests
    # don't leak state into each other.
    # The TestClient has to trigger at least one request to fire lifespan
    # and instantiate the store, but the /cases endpoint below handles that.
    # We defer the clear until after the yield so lifespan has definitely run.
    _clear_annotations()

    yield rf

    _clear_annotations()
    shutil.rmtree(results_dir, ignore_errors=True)


def test_cases_endpoint_returns_non_empty_filters_empty(fake_result: Path):
    res = client.get(
        f"/api/human-review/cases?file_ids={fake_result.name}&skip_empty=true"
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1  # empty response skipped
    assert body["mixed_plugins"] is False
    assert body["plugin"] == "carwash"
    assert body["cases"][0]["case_id"] == "carwash_0001"
    assert body["cases"][0]["expected"] == "drive"


def test_cases_endpoint_can_disable_skip_empty(fake_result: Path):
    res = client.get(
        f"/api/human-review/cases?file_ids={fake_result.name}&skip_empty=false"
    )
    assert res.status_code == 200
    assert res.json()["total"] == 2


def test_phase2_parser_offsets_pass_through_api(tmp_path: Path, monkeypatch):
    """Phase 2: when a result entry carries `parsed_char_start` /
    `parsed_char_end`, the `/cases` endpoint projects them onto the
    ReviewCase payload so the frontend can paint parser-highlight without
    a client-side substring search."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    raw = "After thought, you should drive."
    data = {
        "metadata": {},
        "model_info": {"model_name": "test-model", "provider": "ollama"},
        "testset_metadata": {"name": "phase2_offsets"},
        "execution_info": {"duration_seconds": 1.0},
        "summary_statistics": {},
        "results": [
            {
                "test_id": "carwash_offset",
                "status": "success",
                "input": {
                    "user_prompt": "Walk or drive?",
                    "system_prompt": "You are pragmatic.",
                    "task_params": {"task_type": "carwash", "expected_answer": "drive"},
                    "prompt_metadata": {"language": "en"},
                },
                "output": {
                    "raw_response": raw,
                    "parsed_answer": "drive",
                    "parsed_char_start": 26,
                    "parsed_char_end": 31,
                },
                "evaluation": {"correct": True, "match_type": "correct"},
            },
        ],
    }
    rf = results_dir / "results_offsets.json.gz"
    with gzip.open(rf, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    monkeypatch.setattr(analysis, "_results_dirs", lambda: [results_dir])
    _clear_annotations()

    res = client.get(
        f"/api/human-review/cases?file_ids={rf.name}&skip_correct=false&skip_empty=false"
    )
    assert res.status_code == 200
    cases = res.json()["cases"]
    assert len(cases) == 1
    c = cases[0]
    assert c["parsed_char_start"] == 26
    assert c["parsed_char_end"] == 31
    # The offsets slice back to the extracted value.
    assert raw[c["parsed_char_start"]:c["parsed_char_end"]] == "drive"


def test_phase2_parser_offsets_absent_on_legacy_files(fake_result: Path):
    """Legacy result files (pre-Phase-2) have no offset fields. The API
    must still project the case cleanly — absent offsets surface as null
    and the frontend falls back to client-side substring search."""
    res = client.get(
        f"/api/human-review/cases?file_ids={fake_result.name}&skip_empty=true"
    )
    assert res.status_code == 200
    c = res.json()["cases"][0]
    assert c.get("parsed_char_start") is None
    assert c.get("parsed_char_end") is None


def test_phase3_was_truncated_passes_through_api(tmp_path: Path, monkeypatch):
    """Phase 3: when a result entry carries `output.was_truncated == true`,
    the /cases endpoint projects it onto the ReviewCase payload so the
    frontend can pre-toggle the Truncated chip on case load."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    data = {
        "metadata": {},
        "model_info": {"model_name": "test-model", "provider": "ollama"},
        "testset_metadata": {"name": "phase3_truncated"},
        "execution_info": {"duration_seconds": 1.0},
        "summary_statistics": {},
        "results": [
            {
                "test_id": "carwash_trunc",
                "status": "success",
                "input": {
                    "user_prompt": "Walk or drive?",
                    "system_prompt": "You are pragmatic.",
                    "task_params": {"task_type": "carwash", "expected_answer": "drive"},
                    "prompt_metadata": {"language": "en"},
                },
                "output": {
                    "raw_response": "I'll think step by step. First we need to...",
                    "parsed_answer": None,
                    "parse_strategy": "fallback",
                    "tokens_generated": 2048,
                    "was_truncated": True,
                    "finish_reason": "length",
                },
                "evaluation": {"correct": False, "match_type": "parse_error"},
            },
        ],
    }
    rf = results_dir / "results_phase3.json.gz"
    with gzip.open(rf, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    monkeypatch.setattr(analysis, "_results_dirs", lambda: [results_dir])
    _clear_annotations()

    res = client.get(
        f"/api/human-review/cases?file_ids={rf.name}&skip_correct=false&skip_empty=false"
    )
    assert res.status_code == 200
    cases = res.json()["cases"]
    assert len(cases) == 1
    assert cases[0]["was_truncated"] is True


def test_phase3_was_truncated_absent_on_legacy_files(fake_result: Path):
    """Legacy result files (pre-Phase-3) have no `was_truncated` field. The
    API surfaces it as `None` and the frontend leaves the chip inactive."""
    res = client.get(
        f"/api/human-review/cases?file_ids={fake_result.name}&skip_empty=true"
    )
    assert res.status_code == 200
    c = res.json()["cases"][0]
    assert c.get("was_truncated") is None


def test_annotate_roundtrip(fake_result: Path):
    body = {
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {
            "spans": [
                {
                    "text": "you should drive",
                    "char_start": 20,
                    "char_end": 36,
                    "position": "end",
                    "format": "plain",
                }
            ],
            "response_class": None,
            "annotator_note": "",
        },
    }
    res = client.post("/api/human-review/annotate", json=body)
    assert res.status_code == 200

    # Round-trip via the API (storage-agnostic).
    res2 = client.get(f"/api/human-review/annotations/{fake_result.name}")
    assert res2.status_code == 200
    payload = res2.json()
    assert payload["meta"]["plugin"] == "carwash"
    assert payload["meta"]["annotated_count"] == 1
    # v2.6+: key is `case_id::response_hash`
    cases = payload["cases"]
    matching = [v for k, v in cases.items() if k.startswith("carwash_0001::")]
    assert matching, "No annotation entry found for carwash_0001"
    assert matching[0]["annotation"]["spans"][0]["text"] == "you should drive"


def test_annotate_parser_false_positive_with_span_allowed(fake_result: Path):
    """v3 — spans may coexist with response_classes (esp. false_positive)."""
    body = {
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {
            "spans": [
                {
                    "text": "choose walking",
                    "char_start": 5,
                    "char_end": 19,
                    "position": "end",
                    "format": "plain",
                }
            ],
            "response_classes": ["false_positive"],
            "annotator_note": "",
        },
    }
    res = client.post("/api/human-review/annotate", json=body)
    assert res.status_code == 200

    # Round-trip the case back out.
    res2 = client.get(f"/api/human-review/annotations/{fake_result.name}")
    # v2.6+: sidecar key is `case_id::response_hash`
    cases = res2.json()["cases"]
    entry = next((v for k, v in cases.items() if k.startswith("carwash_0001::")), None)
    assert entry, "No sidecar entry found for carwash_0001"
    case = entry["annotation"]
    assert "false_positive" in case["response_classes"]
    assert len(case["spans"]) == 1


def test_annotate_invariant_neither_populated_rejected(fake_result: Path):
    body = {
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {"spans": [], "response_class": None, "annotator_note": ""},
    }
    res = client.post("/api/human-review/annotate", json=body)
    assert res.status_code == 400


def test_annotate_unknown_response_class_rejected(fake_result: Path):
    body = {
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {"spans": [], "response_class": "totally_fake", "annotator_note": ""},
    }
    res = client.post("/api/human-review/annotate", json=body)
    assert res.status_code == 400


def test_annotate_rejects_dropped_v3_classes(fake_result: Path):
    """v4: the narrowed allow-set rejects classes that used to be valid —
    `verbose` is dropped in migration, so POSTing it (after migration)
    results in an empty response_classes list which fails the invariant."""
    body = {
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {
            "spans": [],
            "response_classes": ["verbose"],  # dropped in v4
            "annotator_note": "",
        },
    }
    res = client.post("/api/human-review/annotate", json=body)
    # verbose is silently dropped, leaving [] → invariant violation.
    assert res.status_code == 400


def test_annotate_migrates_legacy_refusal_to_unrecoverable(fake_result: Path):
    """POSTing a legacy class code goes through the rename map on the write
    path, so the stored value is the v4 canonical code."""
    body = {
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {
            "spans": [],
            "response_classes": ["refusal"],  # legacy code
            "annotator_note": "",
        },
    }
    res = client.post("/api/human-review/annotate", json=body)
    assert res.status_code == 200

    res2 = client.get(f"/api/human-review/annotations/{fake_result.name}")
    cases = res2.json()["cases"]
    entry = next((v for k, v in cases.items() if k.startswith("carwash_0001::")), None)
    assert entry is not None
    assert entry["annotation"]["response_classes"] == ["unrecoverable"]


def test_report_endpoint(fake_result: Path):
    # Create an annotation first.
    client.post(
        "/api/human-review/annotate",
        json={
            "result_file_id": fake_result.name,
            "case_id": "carwash_0001",
            "annotation": {
                "spans": [
                    {
                        "text": "you should drive",
                        "char_start": 20,
                        "char_end": 36,
                        "position": "end",
                        "format": "plain",
                    }
                ],
                "response_class": None,
                "annotator_note": "",
            },
        },
    )

    res = client.post(
        "/api/human-review/report",
        json={"result_file_ids": [fake_result.name]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["total_cases"] == 1
    assert body["summary"]["parser_missed_extractable"] == 1
    assert len(body["span_groups"]) == 1


def test_cases_endpoint_match_types_filter(fake_result: Path):
    """`match_types` query param restricts cases to the requested parser verdicts."""
    # Both cases have match_type=parse_error, so asking for "mismatch" → 0 results.
    res = client.get(
        f"/api/human-review/cases?file_ids={fake_result.name}&skip_empty=false&match_types=mismatch"
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0

    # Requesting "parse_error" returns the expected cases.
    res2 = client.get(
        f"/api/human-review/cases?file_ids={fake_result.name}&skip_empty=false&match_types=parse_error"
    )
    assert res2.status_code == 200
    assert res2.json()["total"] == 2


def test_build_report_parser_false_positive_counts_as_missed():
    af = {
        "meta": {"annotated_count": 1, "skipped_count": 0},
        "cases": {
            "a": {
                "case_id": "a",
                "response_length": 200,
                "parser_match_type": "correct",  # parser thought it was right
                "parser_extracted": "drive",
                "expected": "drive",
                "annotation": {
                    "spans": [
                        {"text": "choose walking", "char_start": 5, "char_end": 19,
                         "position": "end", "format": "plain"}
                    ],
                    "response_class": "parser_false_positive",
                    "annotator_note": "",
                    "timestamp": "2026-04-15T12:00:00Z",
                },
            },
        },
    }
    report = agg.build_report([af])
    assert report["summary"]["parser_missed_extractable"] == 1
    assert report["summary"]["parser_was_correct"] == 0
    assert report["summary"]["response_class_counts"].get("false_positive") == 1


def test_delete_annotations_is_idempotent(fake_result: Path):
    """DELETE /annotations works whether or not any annotations exist."""
    # With nothing stored yet.
    res = client.delete(f"/api/human-review/annotations/{fake_result.name}")
    assert res.status_code == 200
    assert res.json()["deleted"] is False

    # After writing an annotation via /annotate.
    client.post(
        "/api/human-review/annotate",
        json={
            "result_file_id": fake_result.name,
            "case_id": "carwash_0001",
            "annotation": {"spans": [], "response_classes": ["hedge"], "annotator_note": ""},
        },
    )
    # Sanity: GET returns the row we just wrote.
    assert client.get(
        f"/api/human-review/annotations/{fake_result.name}"
    ).json()["cases"], "annotation not persisted"

    res2 = client.delete(f"/api/human-review/annotations/{fake_result.name}")
    assert res2.status_code == 200
    assert res2.json()["deleted"] is True

    # After delete: GET returns an empty shape.
    res3 = client.get(f"/api/human-review/annotations/{fake_result.name}")
    assert res3.status_code == 200
    assert res3.json() == {"meta": {}, "cases": {}}


def test_delete_annotations_unknown_file_404(fake_result: Path):
    res = client.delete("/api/human-review/annotations/not-a-real-file.json.gz")
    assert res.status_code == 404


def test_translate_endpoint_uses_stub(monkeypatch):
    """`POST /translate` delegates to `src.web.translation.translate`; we stub it
    to avoid any real network calls during CI."""
    def fake_translate(text, source_lang=None, target_lang="en"):
        return trans.TranslationResult(
            translated=f"[{target_lang}] {text}",
            provider="test",
            source_lang=source_lang or "auto",
            target_lang=target_lang,
        )

    monkeypatch.setattr(human_review, "translate_text", fake_translate)

    res = client.post(
        "/api/human-review/translate",
        json={"text": "hola mundo", "source_lang": "es", "target_lang": "en"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["translated"] == "[en] hola mundo"
    assert body["provider"] == "test"


def test_translate_rejects_empty(fake_result: Path):
    res = client.post("/api/human-review/translate", json={"text": "   "})
    assert res.status_code == 400


def test_translation_noop_on_same_lang():
    """Short-circuit: source == target returns the original text with provider `noop`."""
    trans.clear_cache()
    out = trans.translate("hello", source_lang="en", target_lang="en")
    assert out.translated == "hello"
    assert out.provider == "noop"


def test_has_annotations_flag_on_results_summary(fake_result: Path):
    # Before any annotation.
    res = client.get("/api/results")
    assert res.status_code == 200
    matching = [r for r in res.json() if r["filename"] == fake_result.name]
    assert matching and matching[0]["has_annotations"] is False

    # After annotating.
    client.post(
        "/api/human-review/annotate",
        json={
            "result_file_id": fake_result.name,
            "case_id": "carwash_0001",
            "annotation": {"spans": [], "response_classes": ["hedge"], "annotator_note": ""},
        },
    )
    res2 = client.get("/api/results")
    matching2 = [r for r in res2.json() if r["filename"] == fake_result.name]
    assert matching2 and matching2[0]["has_annotations"] is True


# ---------------------------------------------------------------------------
# v2 enrichment tests (false_positive_rate, breakdowns, confidence, …)
# ---------------------------------------------------------------------------


def _enriched_case(
    case_id: str,
    *,
    spans=None,
    response_class=None,
    parser_match_type="parse_error",
    parser_extracted=None,
    expected="drive",
    language="en",
    user_style=None,
    system_style=None,
    parse_strategy="unknown",
    note="",
):
    """Build a v2-shape annotation case record (with enrichment fields)."""
    # v3: response_class → response_classes array. Apply renames + drop parser_ok.
    _RENAME = {"verbose_correct": "verbose", "parser_false_positive": "false_positive"}
    rcs: list[str] = []
    if response_class and response_class != "parser_ok":
        rcs = [_RENAME.get(response_class, response_class)]
    return {
        "case_id": case_id,
        "response_length": 200,
        "parser_match_type": parser_match_type,
        "parser_extracted": parser_extracted,
        "expected": expected,
        "language": language,
        "user_style": user_style,
        "system_style": system_style,
        "parse_strategy": parse_strategy,
        "context_windows": [],
        "annotation": {
            "spans": spans or [],
            "response_classes": rcs,
            "annotator_note": note,
            "timestamp": "2026-04-15T12:00:00Z",
        },
    }


def test_v2_format_version_and_top_level_fpr():
    af = {"meta": {}, "cases": {
        # parser_ok is auto-inferred: spans match parser_extracted
        "ok": _enriched_case("ok", parser_match_type="correct",
                             spans=[_span("drive")], parser_extracted="drive"),
        "fp": _enriched_case("fp", response_class="parser_false_positive",
                             spans=[_span("walking")], parser_match_type="correct",
                             parser_extracted="drive", expected="walking"),
    }}
    report = agg.build_report([af])
    assert report["format_version"].startswith("2")
    # Top-level mirrored — agent sees it without drilling into summary
    assert report["false_positive_rate"] == 0.5  # 1 fp / (1 ok + 1 fp)
    assert report["summary"]["false_positive_rate"] == 0.5
    assert report["summary"]["parser_false_positive"] == 1
    assert report["summary"]["parser_was_correct"] == 1


def test_v2_language_breakdown_and_miss_rate():
    af = {"meta": {}, "cases": {
        "ua1": _enriched_case("ua1", language="ua", spans=[_span("прав")], parser_match_type="parse_error"),
        "ua2": _enriched_case("ua2", language="ua", spans=[_span("прав")], parser_match_type="parse_error"),
        # parser_ok is auto-inferred: spans match parser_extracted
        "ua3": _enriched_case("ua3", language="ua", spans=[_span("drive")],
                              parser_match_type="correct", parser_extracted="drive"),
        "en1": _enriched_case("en1", language="en", spans=[_span("drive")],
                              parser_match_type="correct", parser_extracted="drive"),
    }}
    lb = agg.build_report([af])["language_breakdown"]
    assert lb["ua"]["total"] == 3
    assert lb["ua"]["miss_rate"] == round(2 / 3, 4)
    assert lb["en"]["miss_rate"] == 0.0


def test_v2_strategy_breakdown_attributes_false_positives():
    af = {"meta": {}, "cases": {
        "fs1": _enriched_case("fs1", parse_strategy="first_sentence",
                              response_class="parser_false_positive",
                              spans=[_span("walking")], parser_match_type="correct"),
        "fs2": _enriched_case("fs2", parse_strategy="first_sentence",
                              response_class="parser_false_positive",
                              spans=[_span("stay")], parser_match_type="correct"),
        # parser_ok auto-inferred via span-parser alignment
        "fs3": _enriched_case("fs3", parse_strategy="first_sentence",
                              spans=[_span("drive")], parser_match_type="correct",
                              parser_extracted="drive"),
        "bx1": _enriched_case("bx1", parse_strategy="boxed",
                              spans=[_span("drive")], parser_match_type="correct",
                              parser_extracted="drive"),
    }}
    sb = agg.build_report([af])["strategy_breakdown"]
    assert sb["first_sentence"]["parser_false_positive"] == 2
    # parser_ok is auto-inferred at aggregation time, strategy_breakdown
    # no longer counts it (field is 0).
    assert sb["first_sentence"]["parser_ok"] == 0
    # false_positive_rate = fp / (ok + fp); with ok=0, rate = 1.0
    # But the test cases fs3 contributes a recoverable_miss (span present, not FP)
    assert sb["first_sentence"]["false_positive_rate"] == 1.0
    assert sb["boxed"]["parser_ok"] == 0
    assert sb["boxed"]["false_positive_rate"] == 0.0


def test_v2_answer_when_missed_pairs():
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", response_class="parser_false_positive",
                            spans=[_span("walking")], parser_match_type="correct",
                            parser_extracted="drive", expected="walking"),
        "b": _enriched_case("b", response_class="parser_false_positive",
                            spans=[_span("walking")], parser_match_type="correct",
                            parser_extracted="drive", expected="walking"),
        "c": _enriched_case("c", spans=[_span("you should drive")],
                            parser_match_type="parse_error", expected="drive"),
    }}
    awm = agg.build_report([af])["answer_when_missed"]
    # by_expected: drive (from c), walking ×2 (from a, b)
    assert awm["by_expected"].get("walking") == 2
    assert awm["by_expected"].get("drive") == 1
    # distractor table only populated for false-positives
    assert awm["by_extracted_distractor"].get("drive") == 2
    pairs = awm["expected_distractor_pairs"]
    assert pairs and pairs[0]["expected"] == "walking"
    assert pairs[0]["parser_extracted"] == "drive"
    assert pairs[0]["count"] == 2
    assert "a" in pairs[0]["example_case_ids"]


def test_v2_span_group_confidence_levels():
    # v2.2: confidence is driven by the top prefix anchor's coverage ratio.
    # Synthetic spans with no `before` context fall back to text-pattern
    # candidates — no prefix anchors → low confidence.
    consistent_anchor = {"meta": {}, "cases": {
        "a": _enriched_case("a", spans=[_span("you should drive")]),
        "b": _enriched_case("b", spans=[_span("you should walk")]),
        "c": _enriched_case("c", spans=[_span("you should fly")]),
    }}
    g = agg.build_report([consistent_anchor])["span_groups"][0]
    # No `before` context means no prefix anchors; but the text-pattern
    # fallback still produces regex candidates with the expected weighted shape.
    assert all("pattern" in r and "kind" in r and "support" in r for r in g["suggested_regex"])
    assert any(r["kind"] == "text_pattern" for r in g["suggested_regex"])

    # Single-span group → low confidence regardless of anchor
    single = {"meta": {}, "cases": {
        "a": _enriched_case("a", spans=[_span("you should drive")]),
    }}
    g_single = agg.build_report([single])["span_groups"][0]
    assert g_single["confidence"] == "low"


def test_v2_annotator_notes_surfaced():
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", response_class="hedge",
                            note="Model translated to UA before answering"),
        "b": _enriched_case("b", response_class="parser_ok", note=""),  # empty filtered out
    }}
    notes = agg.build_report([af])["annotator_notes"]
    assert len(notes) == 1
    assert notes[0]["case_id"] == "a"
    assert "translated" in notes[0]["note"]
    assert notes[0]["verdict"] == "hedge"


def test_v2_legacy_sidecar_backfilled_from_result_payload(fake_result):
    """A legacy case dict with no language/strategy fields should pick those up
    from the source result payload via `result_payloads_by_file`."""
    legacy_af = {"meta": {"result_file": fake_result.name}, "cases": {
        "carwash_0001": {
            "case_id": "carwash_0001",
            "parser_match_type": "parse_error",
            "parser_extracted": None,
            "expected": "drive",
            # No language/parse_strategy/context_windows — pre-v2.20.1 sidecar
            "annotation": {
                "spans": [{"text": "drive", "char_start": 30, "char_end": 35,
                           "position": "end", "format": "plain"}],
                "response_class": None,
                "annotator_note": "",
            },
        },
    }}
    # Load the source result so we can supply it for back-fill
    import gzip as _gz
    with _gz.open(fake_result, "rt", encoding="utf-8") as f:
        src_payload = json.load(f)
    report = agg.build_report(
        [legacy_af],
        result_payloads_by_file={fake_result.name: src_payload},
    )
    # Language back-filled from prompt_metadata in the result file. In v2.3 a
    # single-bucket axis gets suppressed via data_quality, so verify that
    # path instead of inspecting the (now absent) language_breakdown.
    assert "language_breakdown" not in report
    assert "language_breakdown" in (report["data_quality"]["suppressed_sections"] or [])


def test_v2_endpoint_returns_format_version_2(fake_result):
    """End-to-end: POST /report returns v2 shape when annotations exist."""
    client.post("/api/human-review/annotate", json={
        "result_file_id": fake_result.name,
        "case_id": "carwash_0001",
        "annotation": {"spans": [], "response_classes": ["hedge"], "annotator_note": ""},
    })
    res = client.post("/api/human-review/report",
                      json={"result_file_ids": [fake_result.name]})
    assert res.status_code == 200
    body = res.json()
    assert body["format_version"].startswith("2")
    # Core v2.5 sections that must always be present. Axis breakdowns +
    # `answer_when_missed` + `strategy_breakdown` + `annotator_notes` /
    # `ordering_hints` may be omitted — data_quality.suppressed_sections
    # or empty-omit logic explains why (see test_v2_5_* for specifics).
    for key in ("summary", "false_positive_rate",
                "data_quality", "parser_span_alignment",
                "span_groups", "model_answer_distribution"):
        assert key in body, f"missing v2.5 section: {key}"
    # v2.5 — the three dropped sections must NOT appear at top level.
    for deleted in ("confusion_matrix", "anchor_frequency", "response_classes"):
        assert deleted not in body, f"{deleted} should be deleted in v2.5"


# ---------------------------------------------------------------------------
# v2.1 — prefix anchors, structural ratios, sentence capture, regex harness
# ---------------------------------------------------------------------------


def _case_with_before(case_id: str, *, before: str, text: str = "drive", after: str = ".",
                      language: str = "en", position: str = "end", fmt: str = "plain",
                      sentence: str = "") -> Dict[str, Any]:
    """Build an enriched case with a pre-baked context window so tests can
    target the structural-signal / prefix-anchor logic directly."""
    return {
        "case_id": case_id,
        "parser_match_type": "parse_error",
        "parser_extracted": None,
        "expected": "drive",
        "language": language,
        "parse_strategy": "unknown",
        "context_windows": [{
            "text": text, "char_start": 0, "char_end": len(text),
            "before": before, "after": after, "sentence": sentence,
        }],
        "annotation": {
            "spans": [{
                "text": text, "char_start": 0, "char_end": len(text),
                "position": position, "format": fmt,
            }],
            "response_class": None,
            "annotator_note": "",
        },
    }


def test_v2_1_format_version_is_2_1():
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", response_class="parser_ok", parser_match_type="correct"),
    }}
    report = agg.build_report([af])
    # Format version may advance over time (2.1 → 2.2 → …); we just assert
    # we're still on the v2 family.
    assert report["format_version"].startswith("2")


def test_v2_1_prefix_anchors_per_group():
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="Final answer: ")
        for i in range(5)
    }
    af = {"meta": {}, "cases": cases}
    g = agg.build_report([af])["span_groups"][0]
    assert g["prefix_anchors"], "expected prefix_anchors populated"
    top = g["prefix_anchors"][0]
    # The trailing colon stays attached because `_tokenize` is
    # whitespace-split — useful, because it preserves the label shape.
    assert top["phrase"].startswith("final answer")
    assert top["count"] == 5
    assert top["ratio"] == 1.0


def test_v2_1_structural_ratios_line_start():
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="Some thought.\n")
        for i in range(3)
    }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    assert g["structural_ratios"]["line_start"] == 1.0


def test_v2_1_structural_ratios_bold_wrap():
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="Answer is **", after="**.")
        for i in range(3)
    }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    assert g["structural_ratios"]["bold_wrap"] == 1.0


def test_v2_1_structural_ratios_label_colon():
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="Answer: ")
        for i in range(3)
    }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    assert g["structural_ratios"]["label_colon"] == 1.0
    # "answer" is also a known English answer-label
    assert g["structural_ratios"]["answer_label_match"] == 1.0


def test_v2_1_structural_ratios_answer_label_match_es():
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="La respuesta: ", language="es")
        for i in range(3)
    }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    assert g["structural_ratios"]["answer_label_match"] == 1.0


def test_v2_1_sentence_captured_from_raw_response():
    raw = "Some preamble. The answer is walking. Other stuff follows."
    start = raw.index("walking")
    end = start + len("walking")
    spans = [{"text": "walking", "char_start": start, "char_end": end,
              "position": "end", "format": "plain"}]
    windows = human_review._extract_context_windows(raw, {"spans": spans})
    assert len(windows) == 1
    # Sentence boundaries are consumed, not included — so the trailing `.`
    # is NOT part of the captured sentence.
    assert windows[0]["sentence"] == "The answer is walking"


def test_v2_1_regex_test_harness_match_rate():
    # v2.2: regex now anchors on `before` context. With `before="Therefore "`
    # repeated across 5 cases, the top prefix anchor becomes "therefore" and
    # the context-anchored regex captures the first word after it.
    cases = {}
    for i, verb in enumerate(["drive", "walk", "fly", "run", "stay"]):
        text = verb
        cases[f"c{i}"] = {
            "case_id": f"c{i}",
            "parser_match_type": "parse_error",
            "parser_extracted": None,
            "expected": "drive",
            "language": "en",
            "parse_strategy": "unknown",
            "context_windows": [{
                "text": text, "char_start": 0, "char_end": len(text),
                "before": "Therefore ", "after": ".",
                "sentence": f"Therefore {text}.",
            }],
            "annotation": {
                "spans": [{"text": text, "char_start": 0, "char_end": len(text),
                           "position": "end", "format": "plain"}],
                "response_class": None,
                "annotator_note": "",
            },
        }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    harness = g["regex_test"]
    assert harness, "expected at least one harness entry"
    # Context-anchored regex should match all 5 examples via the `therefore`
    # anchor.
    ctx_row = next((r for r in harness if r["kind"] == "context_anchor"), None)
    assert ctx_row is not None
    assert ctx_row["match_rate"] == 1.0
    assert ctx_row["matched_count"] == 5
    assert ctx_row["total"] == 5


def test_v2_1_regex_test_harness_handles_bad_regex():
    # Inject a malformed pattern directly into the harness and verify it emits
    # -1.0 instead of crashing.
    examples = [{"text": "drive", "before": "you should ", "after": ".", "sentence": ""}]
    out = agg._regex_test_harness(
        examples,
        [{"pattern": "(unclosed", "kind": "anchor", "support": 1, "anchor_words": None}],
    )
    assert len(out) == 1
    assert out[0]["match_rate"] == -1.0
    assert out[0]["matched_count"] == 0


def test_v2_1_context_window_widened_to_120_chars():
    raw = "x" * 200 + "drive" + "y" * 200
    start = raw.index("drive")
    end = start + len("drive")
    windows = human_review._extract_context_windows(
        raw,
        {"spans": [{"text": "drive", "char_start": start, "char_end": end,
                     "position": "middle", "format": "plain"}]},
    )
    assert len(windows) == 1
    assert len(windows[0]["before"]) == 120
    assert len(windows[0]["after"]) == 120


# ---------------------------------------------------------------------------
# v2.2 — context-anchored regex, label taxonomy, model answer distribution,
# stop-word filter, parser_extracted surfacing
# ---------------------------------------------------------------------------


def test_v2_2_format_version():
    # Format version is now on a rolling 2.x track — just assert family.
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", response_class="parser_ok", parser_match_type="correct"),
    }}
    assert agg.build_report([af])["format_version"].startswith("2.")


def test_v2_2_model_answer_distribution_strips_markdown():
    # Annotations mix bare / bold / italic / strikethrough markers around the
    # same underlying answer ("walk" vs "drive") — the distribution should
    # collapse them.
    cases = {}
    for i, text in enumerate(["Walk", "**walk**", "_Walk_", "~~walk~~", "Drive"]):
        cases[f"c{i}"] = _case_with_before(f"c{i}", before="So: ", text=text)
    af = {"meta": {}, "cases": cases}
    dist = agg.build_report([af])["model_answer_distribution"]
    assert dist.get("walk") == 4
    assert dist.get("drive") == 1


def test_v2_2_context_anchor_regex_beats_text_pattern():
    # Ideal scenario for the new generator: a consistent `**Answer:**` prefix
    # before varying bold-wrapped answers. Context_anchor should emit first
    # and match 100%.
    cases = {}
    for i, verb in enumerate(["walk", "drive", "run", "walk", "fly"]):
        raw_before = "Some reasoning.\n\n**Answer:** **"
        raw_after = "**"
        cases[f"c{i}"] = {
            "case_id": f"c{i}",
            "parser_match_type": "parse_error",
            "parser_extracted": None,
            "expected": "drive",
            "language": "en",
            "parse_strategy": "unknown",
            "context_windows": [{
                "text": verb, "char_start": 0, "char_end": len(verb),
                "before": raw_before, "after": raw_after,
                "sentence": f"**Answer:** **{verb}**",
            }],
            "annotation": {
                "spans": [{"text": verb, "char_start": 0, "char_end": len(verb),
                           "position": "end", "format": "bold"}],
                "response_class": None,
                "annotator_note": "",
            },
        }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    # First candidate should be the context_anchor with format-aware capture.
    ctx = next((r for r in g["regex_test"] if r["kind"] == "context_anchor"), None)
    assert ctx is not None
    assert ctx["match_rate"] == 1.0
    # Pattern uses case-insensitive inline flag + bold wrapper around the capture.
    assert ctx["pattern"].startswith("(?i)")
    assert r"\*\*" in ctx["pattern"] and "([^*" in ctx["pattern"]


def test_v2_2_format_only_safety_net_for_distinctive_formats():
    # When `before` context is empty but format is bold, we should still emit
    # a format_only candidate so the parser has *something* to try.
    cases = {}
    for i, verb in enumerate(["walk", "drive", "run"]):
        cases[f"c{i}"] = {
            "case_id": f"c{i}",
            "parser_match_type": "parse_error",
            "parser_extracted": None,
            "expected": "drive",
            "language": "en",
            "parse_strategy": "unknown",
            "context_windows": [{
                "text": verb, "char_start": 0, "char_end": len(verb),
                "before": "", "after": "", "sentence": verb,
            }],
            "annotation": {
                "spans": [{"text": verb, "char_start": 0, "char_end": len(verb),
                           "position": "end", "format": "bold"}],
                "response_class": None,
                "annotator_note": "",
            },
        }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    format_only = next((r for r in g["suggested_regex"] if r["kind"] == "format_only"), None)
    assert format_only is not None
    # Format-only bold capture
    assert r"\*\*" in format_only["pattern"]


def test_v2_2_label_taxonomy_breaks_down_labels():
    cases = {}
    for i, before in enumerate([
        "**Answer:** ",
        "**Answer:** ",
        "**Recommendation:** ",
        "**Conclusion:** ",
    ]):
        cases[f"c{i}"] = _case_with_before(f"c{i}", before=before)
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    tax = g["label_taxonomy"]
    labels = {row["label"]: row["count"] for row in tax}
    assert labels.get("answer") == 2
    assert labels.get("recommendation") == 1
    assert labels.get("conclusion") == 1


def test_v2_2_stop_word_filter_drops_noise_prefix_anchors():
    # 4 cases with `before="to "` — "to" is a stop-word and should NOT appear
    # in prefix_anchors even though it hits the count threshold.
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="better to ")
        for i in range(4)
    }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    phrases = [a["phrase"] for a in g["prefix_anchors"]]
    # Multi-word "better to" is OK; bare "to" is filtered.
    assert "to" not in phrases
    assert "better to" in phrases


def test_v2_2_parser_extracted_surfaced_in_example_spans():
    # Case where parser said "drive" but annotator marked "walk" — the report
    # should surface `parser_extracted` on the example so the agent sees the
    # disagreement inline.
    case = _enriched_case(
        "c1",
        spans=[_span("walk", position="end", fmt="plain")],
        parser_extracted="drive",
        parser_match_type="naive_trap",
    )
    af = {"meta": {}, "cases": {"c1": case}}
    g = agg.build_report([af])["span_groups"][0]
    example = g["example_spans"][0]
    assert example["parser_extracted"] == "drive"
    assert example["parser_match_type"] == "naive_trap"


def test_v2_2_autoformat_italic_detection_via_underscores():
    # Simulate the annotator marking `_Walk_` — no frontend needed here, but
    # assert that backend validation treats "italic" as a valid format string.
    # (Backend takes whatever string; we just sanity-check that FORMAT_TO_STRATEGY
    # maps it to a new strategy.)
    assert agg.FORMAT_TO_STRATEGY.get("italic") == "italic_keyword"
    assert agg.FORMAT_TO_STRATEGY.get("strikethrough") == "strikethrough_keyword"
    assert agg.FORMAT_TO_STRATEGY.get("header") == "header_line"


# ---------------------------------------------------------------------------
# v2.3 — parser-span alignment, capture quality, data quality
# ---------------------------------------------------------------------------


def test_v2_3_is_aligned_semantics():
    # exact match (case + markdown stripped)
    assert agg._is_aligned("walk", "Walk")
    assert agg._is_aligned("**walk**", "walk")
    # parser captured a single word that appears in the multi-word span
    assert agg._is_aligned("walk", "Walk to the carwash")
    # parser captured a multi-word phrase that contains the single-word span
    assert agg._is_aligned("walk or drive", "walk")
    # different stems → misaligned (surfacing this is the whole point)
    assert not agg._is_aligned("walking", "walk")
    # totally different → misaligned
    assert not agg._is_aligned("determine", "walk")
    # empty → False
    assert not agg._is_aligned(None, "walk")
    assert not agg._is_aligned("walk", "")


def test_v2_3_parser_span_alignment_aligned_and_misaligned():
    # Two aligned (parser==span), one misaligned (parser latched onto a
    # distractor), one no_parser_output.
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", spans=[_span("walk")],
                            parser_extracted="walk", parser_match_type="naive_trap"),
        "b": _enriched_case("b", spans=[_span("walk")],
                            parser_extracted="Walk", parser_match_type="naive_trap"),
        "c": _enriched_case("c", spans=[_span("walk")],
                            parser_extracted="determine", parser_match_type="mismatch"),
        "d": _enriched_case("d", spans=[_span("walk")],
                            parser_extracted=None, parser_match_type="parse_error"),
    }}
    report = agg.build_report([af])
    alignment = report["parser_span_alignment"]
    assert alignment["aligned_with_parser"] == 2
    assert alignment["misaligned_with_parser"] == 1
    assert alignment["no_parser_output"] == 1
    assert alignment["total_comparable"] == 4
    assert alignment["alignment_ratio"] == 0.5
    # The misaligned case must surface in sample_misaligned for the agent
    samples = alignment["sample_misaligned"]
    assert len(samples) == 1
    assert samples[0]["case_id"] == "c"
    assert samples[0]["parser_extracted"] == "determine"


def test_v2_3_summary_splits_parser_missed_into_aligned_and_misaligned():
    af = {"meta": {}, "cases": {
        # a, b: parser_extracted aligns with span → auto-inferred parser_was_correct
        # c: misaligned → parser_missed_extractable
        # d: no parser output → parser_missed_extractable
        "a": _enriched_case("a", spans=[_span("walk")], parser_extracted="walk"),
        "b": _enriched_case("b", spans=[_span("walk")], parser_extracted="Walk"),
        "c": _enriched_case("c", spans=[_span("walk")], parser_extracted="determine"),
        "d": _enriched_case("d", spans=[_span("walk")], parser_extracted=None),
    }}
    s = agg.build_report([af])["summary"]
    # v3: aligned cases are auto-inferred as parser_was_correct, not missed.
    assert s["parser_was_correct"] == 2
    assert s["parser_missed_misaligned"] == 1
    assert s["parser_missed_no_output"] == 1
    # Only truly missed cases (misaligned + no_output) remain.
    assert s["parser_missed_extractable"] == 2


def test_v2_3_regex_harness_capture_quality():
    # Setup: spans with `Recommendation:` label; regex captures everything
    # up to the next period. Some captures equal the span exactly (high
    # capture_exact_rate), others capture more ("Definitively walk to the
    # carwash") so only capture_contains_rate is high.
    cases = {}
    for i, (before, text, after) in enumerate([
        ("Recommendation: ", "walk", "."),
        ("Recommendation: ", "walk", "."),
        ("Recommendation: Definitively ", "walk", " to the carwash."),
    ]):
        cases[f"c{i}"] = {
            "case_id": f"c{i}",
            "parser_match_type": "parse_error",
            "parser_extracted": None,
            "expected": "walk",
            "language": "en",
            "parse_strategy": "unknown",
            "context_windows": [{
                "text": text, "char_start": 0, "char_end": len(text),
                "before": before, "after": after,
                "sentence": f"{before}{text}{after}".strip(),
            }],
            "annotation": {
                "spans": [{"text": text, "char_start": 0, "char_end": len(text),
                           "position": "end", "format": "label"}],
                "response_class": None,
                "annotator_note": "",
            },
        }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    harness = g["regex_test"]
    assert harness
    # Labelled-answer regex captures everything until `.` or `\n`.
    top = harness[0]
    assert top["match_rate"] == 1.0
    # All 3 captures contain the annotated span (`walk` is in each).
    assert top["capture_contains_rate"] == 1.0
    # Only 2 of 3 are exact — the "Definitively walk to the carwash" capture
    # is a superset, so capture_exact_rate drops.
    assert top["capture_exact_rate"] < 1.0
    assert top["sample_captures"], "expected sample_captures populated"
    # sample_captures schema
    sc = top["sample_captures"][0]
    for key in ("case_id", "captured", "annotated", "exact_match", "aligned"):
        assert key in sc


def test_v2_3_data_quality_warns_when_parse_strategy_unknown():
    # All cases have parse_strategy='unknown' (the default in _enriched_case).
    af = {"meta": {}, "cases": {
        f"c{i}": _enriched_case(f"c{i}", spans=[_span("walk")]) for i in range(10)
    }}
    dq = agg.build_report([af])["data_quality"]
    codes = {w["code"] for w in dq["warnings"]}
    assert "no_parse_strategy" in codes


def test_v2_3_data_quality_suppresses_single_bucket_axes():
    af = {"meta": {}, "cases": {
        # All English, all unspecified styles → three axes all single-bucket
        f"c{i}": _enriched_case(f"c{i}", language="en", spans=[_span("walk")])
        for i in range(5)
    }}
    report = agg.build_report([af])
    # Suppressed sections don't appear in the payload
    assert "language_breakdown" not in report
    assert "config_breakdown" not in report
    assert "user_style_breakdown" not in report
    # data_quality has the warnings + suppressed list
    dq = report["data_quality"]
    codes = {w["code"] for w in dq["warnings"]}
    assert {"uniform_language", "uniform_system_style", "uniform_user_style"}.issubset(codes)
    # v2.5 also suppresses `strategy_breakdown` (all parse_strategy='unknown')
    # and `answer_when_missed.by_expected` (uniform expected). Assert the
    # axis suppressions are present rather than exact-match.
    assert {
        "language_breakdown", "config_breakdown", "user_style_breakdown",
    }.issubset(set(dq["suppressed_sections"]))


def test_v2_3_data_quality_keeps_axis_with_multiple_buckets():
    # Two languages → language_breakdown preserved; single-bucket axes still
    # suppressed.
    af = {"meta": {}, "cases": {
        "en1": _enriched_case("en1", language="en", spans=[_span("walk")]),
        "ua1": _enriched_case("ua1", language="ua", spans=[_span("прав")]),
    }}
    report = agg.build_report([af])
    assert "language_breakdown" in report
    assert set(report["language_breakdown"].keys()) == {"en", "ua"}
    # No uniform_language warning when axis has variety.
    codes = {w["code"] for w in report["data_quality"]["warnings"]}
    assert "uniform_language" not in codes


def test_v2_3_data_quality_flags_uniform_expected():
    af = {"meta": {}, "cases": {
        f"c{i}": _enriched_case(f"c{i}", expected="drive", spans=[_span("walk")])
        for i in range(5)
    }}
    codes = {
        w["code"]
        for w in agg.build_report([af])["data_quality"]["warnings"]
    }
    assert "uniform_expected" in codes


def test_v2_3_regex_harness_bad_regex_includes_new_fields():
    # A compile-error regex must still populate the new capture-quality fields
    # (as zeros), not raise KeyError on the frontend.
    out = agg._regex_test_harness(
        [{"text": "walk", "before": "", "after": "", "sentence": "", "case_id": "c1"}],
        [{"pattern": "(unclosed", "kind": "context_anchor", "support": 1, "anchor_words": None}],
    )
    assert out[0]["match_rate"] == -1.0
    assert out[0]["capture_exact_rate"] == 0.0
    assert out[0]["capture_contains_rate"] == 0.0
    assert out[0]["sample_captures"] == []


# ---------------------------------------------------------------------------
# v2.4 — anchor type classification, merged disjunction, low-support filter,
# model-answer variants
# ---------------------------------------------------------------------------


def test_v2_4_classify_anchor_all_types():
    # label (colon-terminated)
    assert agg._classify_anchor("recommendation:") == "label"
    assert agg._classify_anchor("conclusion：") == "label"  # fullwidth colon
    # format (markdown / emoji markers)
    assert agg._classify_anchor("**") == "format"
    assert agg._classify_anchor("i'd **") == "format"
    assert agg._classify_anchor("recommendation ✅") == "format"
    assert agg._classify_anchor("answer →") == "format"
    # phrase (flowing text)
    assert agg._classify_anchor("you should") == "phrase"
    assert agg._classify_anchor("is to") == "phrase"
    # empty / missing
    assert agg._classify_anchor("") == "phrase"


def test_v2_4_prefix_anchors_carry_type():
    # Build a group where the `before` context yields a label anchor.
    cases = {
        f"c{i}": _case_with_before(f"c{i}", before="Recommendation: ")
        for i in range(4)
    }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    assert g["prefix_anchors"], "expected prefix_anchors populated"
    # The top anchor `recommendation:` is classified as `label`.
    top = g["prefix_anchors"][0]
    assert top["type"] == "label"


def test_v2_4_prefix_anchors_sort_label_before_phrase_at_equal_count():
    # Hand-craft cases where a label anchor and a phrase anchor would tie on
    # count. Stable sort + secondary type-rank should put label first.
    cases = {}
    # 3 cases with `Conclusion: ` before → label anchor count=3
    for i in range(3):
        cases[f"l{i}"] = _case_with_before(f"l{i}", before="Conclusion: ")
    # 3 cases with `it is ` before → phrase anchor (`is`) is filtered as
    # stop-word, so craft a phrase that sticks: `clearly go `.
    for i in range(3):
        cases[f"p{i}"] = _case_with_before(f"p{i}", before="clearly go ")
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    # Both anchors should appear; the label anchor should come first.
    phrases = [(r["phrase"], r["type"]) for r in g["prefix_anchors"]]
    assert ("conclusion:", "label") in phrases
    # Find label and phrase indices.
    label_idx = next(i for i, r in enumerate(g["prefix_anchors"]) if r["type"] == "label")
    phrase_idx = next(
        (i for i, r in enumerate(g["prefix_anchors"]) if r["type"] == "phrase"),
        None,
    )
    if phrase_idx is not None:
        assert label_idx < phrase_idx, f"expected label before phrase in {phrases}"


def test_v2_4_merged_disjunction_across_two_labels():
    # The canonical carwash case: `Recommendation:` and `Conclusion:` split
    # the group evenly. The merged disjunction should cover both.
    cases = {}
    for i in range(3):
        cases[f"r{i}"] = _case_with_before(f"r{i}", before="Recommendation: ")
    for i in range(3):
        cases[f"c{i}"] = _case_with_before(f"c{i}", before="Conclusion: ")
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    merged = next(
        (r for r in g["regex_test"] if r["kind"] == "merged_label_disjunction"),
        None,
    )
    assert merged is not None, "expected merged_label_disjunction emitted"
    # Both atoms should appear in participating_atoms.
    assert set(merged["participating_atoms"]) == {"recommendation", "conclusion"}
    # Pattern uses the expected disjunction shape.
    assert "(?:" in merged["pattern"]
    assert "recommendation" in merged["pattern"].lower()
    assert "conclusion" in merged["pattern"].lower()
    # Runs at 100% match rate across the 6 cases.
    assert merged["match_rate"] == 1.0


def test_v2_4_merged_disjunction_skipped_when_single_atom():
    # Multiple anchor phrases collapse to the same atom → no disjunction.
    cases = {}
    for i in range(3):
        cases[f"a{i}"] = _case_with_before(f"a{i}", before="Recommendation: ")
    # A second anchor shape that also resolves to atom `recommendation`.
    for i in range(3):
        cases[f"b{i}"] = _case_with_before(
            f"b{i}", before="Best choice. Recommendation: "
        )
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    merged = [r for r in g["regex_test"] if r["kind"] == "merged_label_disjunction"]
    assert merged == [], "single-atom groups should not emit disjunction"


def test_v2_4_low_support_filter_drops_useless_candidate_keeps_format_only():
    # Construct a group where the text_pattern fallback would produce a
    # candidate that matches 0 examples — the filter should drop it.
    cases = {}
    for i, (before, text) in enumerate([
        ("Walking is the right call. So: ", "walking"),
        ("Doing my best. So: ", "drive"),
        ("Right. So: ", "fly"),
    ]):
        cases[f"c{i}"] = {
            "case_id": f"c{i}",
            "parser_match_type": "parse_error",
            "parser_extracted": None,
            "expected": "drive",
            "language": "en",
            "parse_strategy": "unknown",
            "context_windows": [{
                "text": text, "char_start": 0, "char_end": len(text),
                "before": before, "after": ".", "sentence": f"{before}{text}.",
            }],
            "annotation": {
                "spans": [{"text": text, "char_start": 0, "char_end": len(text),
                           "position": "end", "format": "bold"}],
                "response_class": None,
                "annotator_note": "",
            },
        }
    g = agg.build_report([{"meta": {}, "cases": cases}])["span_groups"][0]
    # format_only should survive even if its match_rate is low (safety net).
    assert any(r["kind"] == "format_only" for r in g["regex_test"])
    # Any candidate kept must satisfy the thresholds.
    for r in g["regex_test"]:
        if r["kind"] in {"format_only"} or r["match_rate"] == -1.0:
            continue
        assert (
            r["match_rate"] >= 0.1 or r.get("capture_contains_rate", 0.0) >= 0.1
        ), f"candidate with no signal slipped through: {r}"


def test_v2_4_model_answer_variants_preserves_raw_text():
    # Same normalized bucket (`walk`) receives multiple raw variants.
    cases = {}
    for i, text in enumerate(["Walk", "walk", "WALK", "**Walk**", "Walk to the carwash"]):
        cases[f"c{i}"] = _case_with_before(f"c{i}", before="So: ", text=text)
    report = agg.build_report([{"meta": {}, "cases": cases}])
    variants = report["model_answer_variants"]
    walk_bucket = variants.get("walk")
    assert walk_bucket is not None
    # Raw variants preserve case + markdown.
    texts = {v["text"]: v["count"] for v in walk_bucket["variants"]}
    # `**Walk**` and `Walk to the carwash` normalize to different buckets ONLY
    # if strip_markdown differs — here `**Walk**` strips to "walk" so it
    # lands in the same bucket, while "Walk to the carwash" is a different
    # normalized form.
    assert "Walk" in texts
    assert "WALK" in texts
    assert "**Walk**" in texts
    assert walk_bucket["total"] == sum(texts.values())
    # Backwards-compat: flat distribution still emits the same counts.
    assert report["model_answer_distribution"]["walk"] == walk_bucket["total"]


def test_v2_4_model_answer_variants_top_limit():
    # A bucket with >10 distinct raw variants gets capped.
    cases = {}
    for i in range(15):
        variant = "Walk" if i % 2 == 0 else "walk"  # alternate 2 distinct variants
        cases[f"c{i}"] = _case_with_before(f"c{i}", before="So: ", text=variant + str(i))
    # Each `variant + str(i)` is a unique raw text, normalized to unique form
    # too. So this test also confirms variants ≤ 10 cap by truncation when the
    # bucket shape has many variants. Let me use non-unique normalized form:
    cases = {}
    for i in range(15):
        raw = f"Walk{'!' * (i % 12)}"  # 12 distinct raw forms, all normalize to "walk!..."
        cases[f"c{i}"] = _case_with_before(f"c{i}", before="So: ", text=raw)
    variants = agg.build_report([{"meta": {}, "cases": cases}])["model_answer_variants"]
    # Each normalized bucket's variants list is capped at 10.
    for bucket in variants.values():
        assert len(bucket["variants"]) <= 10


def test_v2_4_format_version():
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", response_class="parser_ok", parser_match_type="correct"),
    }}
    # v2.5 bumped the version — keep the test as a floor (`2.x` family).
    assert agg.build_report([af])["format_version"].startswith("2.")


# ---------------------------------------------------------------------------
# v2.5 — suppressions, deletions, long-tail collapse
# ---------------------------------------------------------------------------


def test_v2_5_format_version_is_2_5():
    af = {"meta": {}, "cases": {
        "a": _enriched_case("a", response_class="parser_ok", parser_match_type="correct"),
    }}
    # Format version advances with each schema change; v2.7 = Phase 1 collapse
    # of negative_keywords → negative_spans + four-class response taxonomy.
    assert agg.build_report([af])["format_version"] == "2.7"


def test_v2_7_negative_group_omits_mark_type():
    """v2.7: the `mark_type` field is gone from `negative_span_groups[]`."""
    af = {"meta": {}, "cases": {
        "a": {
            "case_id": "a",
            "parser_match_type": "mismatch",
            "parser_extracted": "drive",
            "expected": "walk",
            "language": "en",
            "parse_strategy": "unknown",
            "annotation": {
                "spans": [{"text": "walk", "char_start": 0, "char_end": 4,
                           "position": "end", "format": "plain"}],
                "response_classes": [],
                "annotator_note": "",
                "negative_spans": [
                    {"text": "or drive", "char_start": 10, "char_end": 18},
                ],
            },
        },
    }}
    report = agg.build_report([af])
    groups = report.get("negative_span_groups") or []
    assert groups, "expected at least one negative_span_group"
    assert "mark_type" not in groups[0]


def test_phase2_auto_inferred_negative_preserves_source_in_report():
    """Phase 2: auto-inferred negatives carry `source: "auto_inferred"` and
    the aggregator merges them with manual ones in the SAME group (keyed on
    normalized text) while preserving the source tag on each example record
    for downstream filtering."""
    af = {"meta": {}, "cases": {
        "manual": {
            "case_id": "manual",
            "parser_match_type": "mismatch",
            "parser_extracted": "drive",
            "expected": "walk",
            "language": "en",
            "parse_strategy": "first_sentence",
            "annotation": {
                "spans": [{"text": "walk", "char_start": 0, "char_end": 4,
                           "position": "end", "format": "plain"}],
                "response_classes": [],
                "annotator_note": "",
                "negative_spans": [
                    {"text": "drive", "char_start": 10, "char_end": 15,
                     "source": "manual"},
                ],
            },
        },
        "auto": {
            "case_id": "auto",
            "parser_match_type": "mismatch",
            "parser_extracted": "drive",
            "expected": "walk",
            "language": "en",
            "parse_strategy": "first_sentence",
            "annotation": {
                "spans": [{"text": "walk", "char_start": 0, "char_end": 4,
                           "position": "end", "format": "plain"}],
                "response_classes": [],
                "annotator_note": "",
                "negative_spans": [
                    {"text": "drive", "char_start": 10, "char_end": 15,
                     "source": "auto_inferred"},
                ],
            },
        },
    }}
    report = agg.build_report([af])
    groups = report.get("negative_span_groups") or []
    assert len(groups) == 1, "manual + auto should merge in one group (same normalized text)"
    g = groups[0]
    assert g["count"] == 2
    sources = sorted(ex["source"] for ex in g["example_negatives"])
    assert sources == ["auto_inferred", "manual"]


def test_phase2_legacy_negatives_default_source_manual():
    """Pre-Phase-2 sidecars have no `source` field on their marks — the
    aggregator must default them to `"manual"` for the report."""
    af = {"meta": {}, "cases": {
        "a": {
            "case_id": "a",
            "parser_match_type": "mismatch",
            "parser_extracted": "drive",
            "expected": "walk",
            "language": "en",
            "parse_strategy": "first_sentence",
            "annotation": {
                "spans": [{"text": "walk", "char_start": 0, "char_end": 4,
                           "position": "end", "format": "plain"}],
                "response_classes": [],
                "annotator_note": "",
                "negative_spans": [
                    # No `source` field — legacy shape.
                    {"text": "drive", "char_start": 10, "char_end": 15},
                ],
            },
        },
    }}
    report = agg.build_report([af])
    g = (report.get("negative_span_groups") or [])[0]
    assert g["example_negatives"][0]["source"] == "manual"


def test_v2_7_legacy_negative_keywords_fold_into_negative_spans_at_report_time():
    """A legacy annotation still carrying `negative_keywords` entries should
    produce a unified negative group (the aggregator folds on the fly)."""
    af = {"meta": {}, "cases": {
        "a": {
            "case_id": "a",
            "parser_match_type": "mismatch",
            "parser_extracted": "drive",
            "expected": "walk",
            "language": "en",
            "parse_strategy": "unknown",
            "annotation": {
                "spans": [{"text": "walk", "char_start": 0, "char_end": 4,
                           "position": "end", "format": "plain"}],
                "response_classes": [],
                "annotator_note": "",
                "negative_spans": [],
                # Legacy: pre-v2.7 sidecar still populated both arrays.
                "negative_keywords": [
                    {"text": "drive", "char_start": 10, "char_end": 15},
                ],
            },
        },
    }}
    report = agg.build_report([af])
    groups = report.get("negative_span_groups") or []
    assert groups, "expected the legacy keyword to surface as a negative group"
    assert groups[0]["text"] == "drive"
    assert groups[0]["count"] == 1
    assert "mark_type" not in groups[0]


def test_v2_5_suppresses_strategy_breakdown_under_no_parse_strategy():
    # All cases parse_strategy='unknown' (the default) → no_parse_strategy fires.
    af = {"meta": {}, "cases": {
        f"c{i}": _enriched_case(f"c{i}", spans=[_span("walk")], parser_match_type="parse_error")
        for i in range(10)
    }}
    report = agg.build_report([af])
    assert "strategy_breakdown" not in report
    warnings = [w["code"] for w in report["data_quality"]["warnings"]]
    assert "no_parse_strategy" in warnings
    assert "strategy_breakdown" in report["data_quality"]["suppressed_sections"]


def test_v2_5_suppresses_answer_when_missed_by_expected_under_uniform_expected():
    # All cases share expected="drive" → uniform_expected fires.
    af = {"meta": {}, "cases": {
        f"c{i}": _enriched_case(f"c{i}", expected="drive", spans=[_span("walk")])
        for i in range(4)
    }}
    report = agg.build_report([af])
    assert "answer_when_missed" not in report
    warnings = [w["code"] for w in report["data_quality"]["warnings"]]
    assert "uniform_expected" in warnings
    assert "answer_when_missed.by_expected" in report["data_quality"]["suppressed_sections"]


def test_v2_5_drops_anchor_frequency_top_level():
    af = {"meta": {}, "cases": {
        f"c{i}": _enriched_case(f"c{i}", spans=[_span("walk")]) for i in range(4)
    }}
    report = agg.build_report([af])
    assert "anchor_frequency" not in report


def test_v2_5_drops_confusion_matrix_top_level():
    af = {"meta": {}, "cases": {
        "tp": _enriched_case("tp", response_class="parser_ok", parser_match_type="correct"),
        "fp": _enriched_case("fp", response_class="parser_false_positive",
                             spans=[_span("walking")], parser_match_type="correct"),
    }}
    report = agg.build_report([af])
    assert "confusion_matrix" not in report


def test_v2_5_response_class_counts_moved_to_summary():
    af = {"meta": {}, "cases": {
        "ok": _enriched_case("ok", response_class="parser_ok", parser_match_type="correct"),
        "fp": _enriched_case("fp", response_class="parser_false_positive",
                             spans=[_span("walking")], parser_match_type="correct"),
        "h":  _enriched_case("h", response_class="hedge"),
    }}
    report = agg.build_report([af])
    # v2.5 — top-level section is gone.
    assert "response_classes" not in report
    # Folded into summary, only non-zero buckets emitted.
    counts = report["summary"]["response_class_counts"]
    # parser_ok is auto-inferred, not stored as a class anymore
    assert counts["false_positive"] == 1
    assert counts["hedge"] == 1
    assert counts["parser_missed"] == 1  # span-bearing case
    # Zero-valued classes absent from the folded dict.
    assert "gibberish" not in counts
    assert "refusal" not in counts


def test_v2_5_long_tail_groups_collapse_under_count_4():
    # Build 4 distinct (position, format) groups: two rich (4 & 6 cases) and
    # two long-tail (3 & 1 cases).
    cases = {}
    # Rich group 1: 6 cases at (end, plain)
    for i in range(6):
        cases[f"rich1_{i}"] = _case_with_before(
            f"rich1_{i}", before="Answer: ", text="walk",
        )
    # Rich group 2: 4 cases at (end, bold)
    for i in range(4):
        cases[f"rich2_{i}"] = _case_with_before(
            f"rich2_{i}", before="Conclusion: ", text=f"drive{i}", fmt="bold",
        )
    # Long-tail 1: 3 cases at (middle, italic)
    for i in range(3):
        cases[f"tail1_{i}"] = _case_with_before(
            f"tail1_{i}", before="x ", text=f"hop{i}", position="middle", fmt="italic",
        )
    # Long-tail 2: 1 case at (start, header)
    cases["tail2_0"] = _case_with_before(
        "tail2_0", before="", text="fly", position="start", fmt="header",
    )
    report = agg.build_report([{"meta": {}, "cases": cases}])
    # Rich groups retain full structure.
    assert len(report["span_groups"]) == 2
    for g in report["span_groups"]:
        assert g["count"] >= 4
        assert "structural_ratios" in g
        assert "prefix_anchors" in g
        assert "regex_test" in g
    # Long-tail groups collapsed, preserve only position/format/count + 1 example.
    assert "long_tail_groups" in report
    ltg = report["long_tail_groups"]
    assert len(ltg) == 2
    for g in ltg:
        assert set(g.keys()) == {"position", "format", "count", "example"}
        assert g["count"] < 4
        # structural_ratios / prefix_anchors / regex_test NOT carried through.
        assert "structural_ratios" not in g
        assert "prefix_anchors" not in g
        assert "regex_test" not in g


def test_v2_5_empty_ordering_hints_and_annotator_notes_omitted():
    af = {"meta": {}, "cases": {
        # parser_ok case — no spans, no notes, no ordering hint triggers.
        "a": _enriched_case("a", response_class="parser_ok", parser_match_type="correct"),
    }}
    report = agg.build_report([af])
    assert "ordering_hints" not in report
    assert "annotator_notes" not in report


def test_v2_5_non_empty_ordering_and_notes_are_preserved():
    # 4 end-plain missed spans trigger the ordering-hint rule; one note present.
    af = {"meta": {}, "cases": {}}
    for i in range(4):
        af["cases"][f"c{i}"] = _enriched_case(
            f"c{i}", spans=[_span("you should drive")], parser_match_type="parse_error",
        )
    af["cases"]["n"] = _enriched_case(
        "n", response_class="hedge", note="annotator saw weird framing",
    )
    report = agg.build_report([af])
    assert "ordering_hints" in report
    assert len(report["ordering_hints"]) >= 1
    assert "annotator_notes" in report
    assert any("weird framing" in n["note"] for n in report["annotator_notes"])

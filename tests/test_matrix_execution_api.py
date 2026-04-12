import gzip
import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.stages.generate_testset import _finalize_testset
from src.web.app import app
from src.web.api import analysis, testsets
from src.web.api import matrix


client = TestClient(app)


def test_matrix_run_expands_cells_and_jobs(monkeypatch):
    generated_requests = []
    submitted_requests = []

    async def fake_generate(req):
        generated_requests.append(req)
        return {
            "status": "ok",
            "testset_path": f"/tmp/{req.name}.json.gz",
            "filename": f"{req.name}.json.gz",
        }

    async def fake_submit(req):
        submitted_requests.append(req)
        return {
            "run_group_id": f"run_{len(submitted_requests)}",
            "jobs": [
                {"job_id": f"job_{len(submitted_requests)}_{index}", "model": model}
                for index, model in enumerate(req.models, start=1)
            ]
        }

    monkeypatch.setattr(matrix, "generate_testset", fake_generate)
    monkeypatch.setattr(matrix, "submit_run", fake_submit)

    response = client.post(
        "/api/matrix/run",
        json={
            "plugin_type": "picross",
            "name_prefix": "picross_matrix",
            "seed": 7,
            "temperature": 0.2,
            "max_tokens": 768,
            "no_think": True,
            "base_generation": {
                "puzzles_per_difficulty": 2,
                "density": 0.5,
            },
            "prompt_axes": {
                "user_styles": ["minimal"],
                "system_styles": ["analytical", "adversarial"],
                "languages": ["en"],
            },
            "field_axes": [
                {"field_name": "clue_format", "values": ["inline", "grid_header"]},
            ],
            "model_groups": [
                {"provider": "ollama", "models": ["qwen3:0.6b", "gemma3:1b"]},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_cells"] == 4
    assert body["total_jobs"] == 8
    assert len(body["generated_testsets"]) == 4
    assert len(body["jobs"]) == 8
    assert all(job["run_group_id"].startswith("run_") for job in body["jobs"])

    assert len(generated_requests) == 4
    assert len(submitted_requests) == 4
    for generated in generated_requests:
        assert generated.metadata_extra["matrix_batch_id"]
        assert generated.metadata_extra["matrix_cell_id"]
        assert generated.metadata_extra["matrix_label"]
        assert generated.tasks[0].type == "picross"
        assert len(generated.tasks[0].prompt_configs) == 1


def test_matrix_run_generate_only_skips_jobs(monkeypatch):
    generated_requests = []

    async def fake_generate(req):
        generated_requests.append(req)
        return {
            "status": "ok",
            "testset_path": f"/tmp/{req.name}.json.gz",
            "filename": f"{req.name}.json.gz",
        }

    async def fake_submit(_req):
        raise AssertionError("submit_run should not be called for generate_only")

    monkeypatch.setattr(matrix, "generate_testset", fake_generate)
    monkeypatch.setattr(matrix, "submit_run", fake_submit)

    response = client.post(
        "/api/matrix/run",
        json={
            "plugin_type": "picross",
            "name_prefix": "picross_generate_only",
            "generate_only": True,
            "seed": 7,
            "temperature": 0.2,
            "max_tokens": 768,
            "no_think": True,
            "base_generation": {
                "puzzles_per_difficulty": 2,
                "density": 0.5,
            },
            "prompt_axes": {
                "user_styles": ["minimal"],
                "system_styles": ["analytical"],
                "languages": ["en", "de"],
            },
            "field_axes": [],
            "model_groups": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["generate_only"] is True
    assert body["total_cells"] == 2
    assert body["total_jobs"] == 0
    assert body["jobs"] == []
    assert len(generated_requests) == 2


def test_matrix_run_rejects_unsupported_field_type():
    response = client.post(
        "/api/matrix/run",
        json={
            "plugin_type": "picross",
            "name_prefix": "picross_matrix",
            "seed": 7,
            "temperature": 0.1,
            "max_tokens": 256,
            "no_think": True,
            "base_generation": {},
            "prompt_axes": {
                "user_styles": ["minimal"],
                "system_styles": ["analytical"],
                "languages": ["en"],
            },
            "field_axes": [
                {"field_name": "cell_markers", "values": ["1,0"]},
            ],
            "model_groups": [
                {"provider": "ollama", "models": ["qwen3:0.6b"]},
            ],
        },
    )

    assert response.status_code == 400
    assert "unsupported type" in response.text


def test_finalize_testset_preserves_extra_metadata(tmp_path):
    config = {
        "metadata": {
            "name": "matrix_meta",
            "description": "metadata preservation",
            "task_type": "picross",
            "matrix_batch_id": "batch123",
            "matrix_cell_id": "batch123_cell_001",
            "matrix_label": "user=minimal | system=analytical | lang=en",
        },
        "task": {
            "type": "picross",
            "generation": {},
            "prompt_configs": [
                {
                    "name": "minimal_analytical",
                    "user_style": "minimal",
                    "system_style": "analytical",
                    "language": "en",
                }
            ],
        },
        "sampling": {"temperature": 0.1, "max_tokens": 256},
        "execution": {"no_thinking": True, "cell_markers": ["1", "0"]},
    }
    test_cases = [
        {
            "test_id": "picross_0000",
            "task_type": "picross",
            "config_name": "minimal_analytical",
            "prompts": {"system": "", "user": "", "full": ""},
            "task_params": {"expected_grid": [[1]]},
            "prompt_metadata": {"user_style": "minimal", "system_style": "analytical", "language": "en"},
            "generation_metadata": {"seed": 1},
        }
    ]

    path = _finalize_testset(config, "matrix_meta.yaml", str(tmp_path), test_cases, "picross")
    assert Path(path).exists()

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["metadata"]["matrix_batch_id"] == "batch123"
    assert payload["metadata"]["matrix_cell_id"] == "batch123_cell_001"
    assert payload["metadata"]["matrix_label"] == "user=minimal | system=analytical | lang=en"


def test_summaries_expose_matrix_and_run_metadata(tmp_path):
    testset_path = tmp_path / "testset_matrix_meta.json.gz"
    result_path = tmp_path / "results_matrix_meta.json.gz"

    testset_payload = {
        "metadata": {
            "name": "matrix_meta",
            "matrix_batch_id": "batch123",
            "matrix_cell_id": "batch123_cell_001",
            "matrix_label": "user=minimal | system=analytical | lang=en",
            "matrix_plugin": "picross",
            "matrix_axes": {"user_style": "minimal", "system_style": "analytical", "language": "en"},
        },
        "generation_params": {},
        "statistics": {},
        "test_cases": [
            {
                "test_id": "picross_0001",
                "task_type": "picross",
                "prompt_metadata": {"language": "en", "user_style": "minimal", "system_style": "analytical"},
            }
        ],
    }
    with gzip.open(testset_path, "wt", encoding="utf-8") as handle:
        json.dump(testset_payload, handle)

    result_payload = {
        "metadata": {"run_group_id": "run123"},
        "summary_statistics": {
            "accuracy": 1.0,
            "correct_responses": 1,
            "parse_error_rate": 0.0,
            "total_input_tokens": 10,
            "total_output_tokens": 5,
        },
        "model_info": {"model_name": "qwen3:0.6b", "provider": "ollama"},
        "execution_info": {"duration_seconds": 1.25},
        "testset_metadata": testset_payload["metadata"],
        "results": [
            {
                "status": "success",
                "test_id": "picross_0001",
                "input": {
                    "prompt_metadata": {"language": "en", "user_style": "minimal", "system_style": "analytical"},
                    "task_params": {"task_type": "picross"},
                },
            }
        ],
    }
    with gzip.open(result_path, "wt", encoding="utf-8") as handle:
        json.dump(result_payload, handle)

    testset_summary = testsets._peek_testset(testset_path)
    result_summary = analysis._summarize_result(result_path)

    assert testset_summary["matrix_batch_id"] == "batch123"
    assert testset_summary["matrix_cell_id"] == "batch123_cell_001"
    assert testset_summary["matrix_plugin"] == "picross"
    assert testset_summary["matrix_axes"] == {"user_style": "minimal", "system_style": "analytical", "language": "en"}

    assert result_summary["run_group_id"] == "run123"
    assert result_summary["matrix_batch_id"] == "batch123"
    assert result_summary["matrix_cell_id"] == "batch123_cell_001"
    assert result_summary["matrix_plugin"] == "picross"
    assert result_summary["matrix_axes"] == {"user_style": "minimal", "system_style": "analytical", "language": "en"}
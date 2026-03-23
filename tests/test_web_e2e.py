#!/usr/bin/env python3
"""End-to-end test for the web UI API: generate → execute → poll → analyze.

IMPORTANT: The web server must be running WITHOUT --reload flag, otherwise
file changes (including creating this test) will restart the server and kill
the worker processes.

    python -m src.web  # no --reload
"""
import os
import sys
import time
import requests

BASE = "http://127.0.0.1:8000"

def main():
    # Step 1: Generate
    print("Step 1: Generate testset...")
    resp = requests.post(f"{BASE}/api/testsets/generate", json={
        "name": "e2e_test",
        "tasks": [{"type": "arithmetic", "generation": {"complexity": [1], "target_values": "1", "expressions_per_target": 2}}],
        "temperature": 0.1, "no_thinking": True, "seed": 99
    })
    assert resp.ok, f"Generate failed: {resp.text}"
    ts_fn = resp.json()["filename"]
    ts_path = resp.json()["testset_path"]
    print(f"  Generated: {ts_fn}")

    # Step 2: Execute
    print("Step 2: Submit execution job...")
    resp = requests.post(f"{BASE}/api/jobs/run", json={
        "testset_path": ts_path,
        "models": ["qwen3:0.6b"],
        "no_think": True,
    })
    assert resp.ok, f"Execute failed: {resp.text}"
    job_id = resp.json()["jobs"][0]["job_id"]
    print(f"  Job: {job_id}")

    # Step 3: Wait for completion
    print("Step 3: Waiting for job...", end="", flush=True)
    state = "unknown"
    for _ in range(60):
        time.sleep(3)
        status = requests.get(f"{BASE}/api/jobs/{job_id}/status").json()
        state = status.get("state", "unknown")
        prog = f'{status.get("progress_current", "?")}/{status.get("progress_total", "?")}'
        print(f" {state}({prog})", end="", flush=True)
        if state in ("completed", "failed"):
            break
    print()

    if state == "completed":
        result_path = status.get("result_path", "")
        result_fn = os.path.basename(result_path)
        print(f"  Result: {result_fn}")

        # Step 4: Analyze
        print("Step 4: Analyze...")
        resp = requests.post(f"{BASE}/api/results/analyze", json={
            "result_filenames": [result_fn],
        })
        if resp.ok:
            data = resp.json()
            for model, stats in data.get("models", {}).items():
                acc = stats["accuracy"]
                print(f"  {model}: accuracy={acc:.1%}, correct={stats['correct']}/{stats['total_tests']}")
        else:
            print(f"  Analyze failed: {resp.text}")

        print("\n✅ End-to-end test PASSED!")
    elif state == "failed":
        print(f"  Error: {status.get('error')}")
        print("\n❌ End-to-end test FAILED!")
        sys.exit(1)
    else:
        print(f"  Timed out (last state: {state})")
        print("\n❌ End-to-end test TIMED OUT!")
        sys.exit(1)


if __name__ == "__main__":
    main()

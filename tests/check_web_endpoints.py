#!/usr/bin/env python3
"""Quick endpoint status check for the web UI."""
import requests

BASE = "http://127.0.0.1:8000"

endpoints = [
    ("GET", "/"),
    ("GET", "/configure"),
    ("GET", "/testsets"),
    ("GET", "/execute"),
    ("GET", "/results"),
    ("GET", "/static/css/style.css"),
    ("GET", "/static/js/app.js"),
    ("GET", "/api/plugins"),
    ("GET", "/api/models"),
    ("GET", "/api/testsets"),
    ("GET", "/api/jobs"),
    ("GET", "/api/results"),
    ("GET", "/api/dashboard-summary"),
    ("GET", "/partials/recent-testsets"),
    ("GET", "/partials/recent-results"),
    ("GET", "/partials/active-jobs"),
    ("GET", "/partials/testsets-table"),
    ("GET", "/partials/results-table"),
]

print("Endpoint Status:")
all_ok = True
for method, path in endpoints:
    try:
        r = requests.get(f"{BASE}{path}", timeout=5)
        status = "OK" if r.ok else "FAIL"
        if not r.ok:
            all_ok = False
        print(f"  {r.status_code} {status:4s} {method} {path}")
    except Exception as e:
        all_ok = False
        print(f"  ERR  FAIL {method} {path} ({e})")

print(f"\n{'All endpoints OK!' if all_ok else 'Some endpoints failed.'}")

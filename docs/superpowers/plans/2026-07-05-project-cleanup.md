# Arduino Raspberry Pi Sensor Hub Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the educational Arduino/Raspberry Pi/Flask sensor pipeline reproducible, safer by default, and accurately documented.

**Architecture:** Preserve the existing serial gateway and Flask/SQLite server. Move runtime secrets to required environment variables, keep storage replaceable in tests, and validate the key HTTP security boundaries with Flask’s test client.

**Tech Stack:** Arduino C++, Python 3.10+, Flask, Flask-HTTPAuth, Requests, pySerial, RPi.GPIO, SQLite, pytest.

---

### Task 1: Write failing server security tests

**Files:**
- Create: `tests/test_server.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create isolated application configuration**

```python
import importlib

import pytest


@pytest.fixture()
def server_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_USERNAME", "tester")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "test-password")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setenv("IOT_DB_PATH", str(tmp_path / "test.db"))

    import serveur.server as server

    server = importlib.reload(server)
    server.init_db()
    server.app.config.update(TESTING=True)
    return server


@pytest.fixture()
def client(server_module):
    return server_module.app.test_client()
```

- [ ] **Step 2: Test authentication and validation boundaries**

```python
import base64


def basic_auth(username="tester", password="test-password"):
    value = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {value}"}


def test_data_ingestion_requires_gateway_key(client):
    response = client.post("/api/data", json={"arduino_id": "arduino1", "valeur": "42"})
    assert response.status_code == 401


def test_data_ingestion_accepts_valid_gateway_key(client):
    response = client.post(
        "/api/data",
        json={"arduino_id": "arduino1", "valeur": "42"},
        headers={"X-API-Key": "test-gateway-key"},
    )
    assert response.status_code == 201


def test_command_rejects_invalid_value(client):
    response = client.post(
        "/api/consignes",
        json={"arduino_id": "arduino1", "valeur": "INVALID"},
        headers=basic_auth(),
    )
    assert response.status_code == 400


def test_history_reset_requires_dashboard_auth(client):
    response = client.post("/reset-historique")
    assert response.status_code == 401


def test_history_reset_accepts_dashboard_auth(client):
    response = client.post("/reset-historique", headers=basic_auth())
    assert response.status_code == 302
```

- [ ] **Step 3: Run tests and confirm the security regression**

Run: `python -m pytest -q`

Expected: reset authentication/redirect assertions fail against the current implementation.

### Task 2: Require runtime configuration and protect deletion

**Files:**
- Modify: `serveur/server.py`
- Modify: `raspberry/gateway.py`
- Modify: `serveur/generate_random_measures.py`

- [ ] **Step 1: Centralize required environment values**

Implement in `serveur/server.py`:

```python
def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


DB_PATH = os.environ.get(
    "IOT_DB_PATH", os.path.join(os.path.dirname(__file__), "iot_data.db")
)
UTILISATEURS = {
    required_env("DASHBOARD_USERNAME"): required_env("DASHBOARD_PASSWORD")
}
GATEWAY_API_KEY = required_env("GATEWAY_API_KEY")
```

Use the same required `GATEWAY_API_KEY` behavior in the gateway and simulator.

- [ ] **Step 2: Protect and redirect history deletion**

```python
from flask import redirect, url_for


@app.route("/reset-historique", methods=["POST"])
@auth.login_required
def reset_historique():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mesures")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='mesures'")
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))
```

- [ ] **Step 3: Run focused tests**

Run: `python -m pytest -q`

Expected: five tests pass.

- [ ] **Step 4: Verify missing-secret failure**

Run:

```powershell
Remove-Item Env:DASHBOARD_USERNAME -ErrorAction SilentlyContinue
Remove-Item Env:DASHBOARD_PASSWORD -ErrorAction SilentlyContinue
Remove-Item Env:GATEWAY_API_KEY -ErrorAction SilentlyContinue
python -c "import serveur.server"
```

Expected: non-zero exit with a named missing environment variable.

### Task 3: Remove artifacts and declare dependencies

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `LICENSE`
- Delete: `serveur/iot_data.db`
- Delete: `serveur/__pycache__/server.cpython-313.pyc`
- Delete: `serveur/__pycache__/generate_random_measures.cpython-313.pyc`
- Delete: `raspberry/__pycache__/gateway.cpython-313.pyc`
- Delete: `code_temperature`
- Delete: `code_lumiere`

- [ ] **Step 1: Add ignore and environment templates**

`.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.venv/
venv/
.env
*.db
.pytest_cache/
.coverage
htmlcov/
```

`.env.example`:

```dotenv
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=change-me
GATEWAY_API_KEY=change-me
SERVER_URL=http://127.0.0.1:5000
IOT_DB_PATH=serveur/iot_data.db
```

- [ ] **Step 2: Declare dependencies**

`requirements.txt`:

```text
Flask>=3.1,<4
Flask-HTTPAuth>=4.8,<5
requests>=2.32,<3
pyserial>=3.5,<4
```

`requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8.4,<9
```

Document `RPi.GPIO` as platform-specific because it cannot be installed or used on a normal Windows development host.

- [ ] **Step 3: Add MIT license and delete generated/duplicate files**

Use the standard MIT license with:

```text
Copyright (c) 2026 FRTDev
```

Remove the exact files listed above. Keep the canonical sketches under `arduino/`.

### Task 4: Replace the placeholder README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the actual system**

Write an English README with:

- project purpose and educational status;
- a Mermaid flow from two Arduinos through the Raspberry Pi gateway to Flask/SQLite and the browser dashboard;
- hardware/software prerequisites;
- repository tree;
- server setup using a virtual environment and required environment variables;
- simulator command before hardware deployment;
- Raspberry Pi serial/GPIO assumptions;
- serial command/response table for both sketches;
- HTTP endpoint/authentication table;
- explicit limitations: no TLS, in-memory commands, one dashboard account, development server, fixed serial device assumptions;
- test commands and MIT license.

- [ ] **Step 2: Verify documentation does not expose working secrets**

Run: `rg -n "iot2026|gateway2026" . -g '!docs/superpowers/**'`

Expected: no matches.

### Task 5: Verify, commit, rename, and publish

**Files:**
- Modify: all files introduced by Tasks 1–4

- [ ] **Step 1: Install dependencies in an isolated environment**

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Expected: installation exits 0.

- [ ] **Step 2: Run full verification**

```powershell
.\.venv\Scripts\python -m compileall -q serveur raspberry tests
.\.venv\Scripts\python -m pytest -q
```

Expected: compilation exits 0 and five tests pass.

- [ ] **Step 3: Run simulator smoke test**

Start the server with test environment values, then run:

```powershell
.\.venv\Scripts\python serveur\generate_random_measures.py --count 2 --delay 0
```

Expected: two HTTP 201 responses and `Succes=2, Echecs=0`.

- [ ] **Step 4: Review and commit**

Run: `git diff --check`

Run: `git status --short`

Expected: only scoped cleanup changes.

```powershell
git add -- . ':!docs/superpowers/specs/2026-07-05-project-cleanup-design.md'
git commit -m "chore: prepare sensor hub for publication"
```

- [ ] **Step 5: Push the cleanup branch**

Run: `git push -u origin codex/project-cleanup`

Expected: the remote branch is created.

- [ ] **Step 6: Rename the GitHub repository**

Run:

```powershell
gh repo rename arduino-rpi-sensor-hub --repo FRTDev/IoT --yes
git remote set-url origin https://github.com/FRTDev/arduino-rpi-sensor-hub.git
```

Expected: `gh repo view FRTDev/arduino-rpi-sensor-hub` succeeds.

- [ ] **Step 7: Open a draft pull request**

Open a draft PR from `codex/project-cleanup` to `main` titled:

```text
[codex] prepare Arduino Raspberry Pi sensor hub for publication
```

The body must summarize cleanup, security changes, developer impact, and exact verification results.

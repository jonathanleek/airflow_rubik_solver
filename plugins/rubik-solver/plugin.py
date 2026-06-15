"""Rubik solver dashboard plugin."""

import asyncio
import json
import os
import time
from pathlib import Path

import requests
from airflow.plugins_manager import AirflowPlugin
from airflow.sdk import Variable
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from include.rubik.constants import AIRFLOW_VARIABLE_KEY, PHASE_DAG_IDS, RUBIK_HISTORY_VARIABLE_KEY

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
RUBIK_DAG_IDS = ["rubik_init", *PHASE_DAG_IDS.values()]

app = FastAPI(title="Rubik Solver")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_cached_token = None
_token_expires_at = 0.0


def _get_json_variable(key, default):
    raw = Variable.get(key, default=None)
    if not raw:
        return default
    return json.loads(raw)


def _airflow_api_url():
    return os.environ.get("RUBIK_SOLVER_AIRFLOW_API_URL", "http://localhost:8080").rstrip("/")


def _get_token():
    token = os.environ.get("RUBIK_SOLVER_TOKEN")
    if token:
        return token

    username = os.environ.get("RUBIK_SOLVER_USERNAME")
    password = os.environ.get("RUBIK_SOLVER_PASSWORD")
    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="Set RUBIK_SOLVER_TOKEN, or RUBIK_SOLVER_USERNAME and RUBIK_SOLVER_PASSWORD, to trigger DAGs from the plugin.",
        )

    global _cached_token, _token_expires_at
    now = time.monotonic()
    if _cached_token and now < _token_expires_at:
        return _cached_token

    response = requests.post(
        f"{_airflow_api_url()}/auth/token",
        json={"username": username, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    _cached_token = response.json()["access_token"]
    _token_expires_at = now + 55 * 60
    return _cached_token


def _headers():
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


@app.get("/ui", response_class=FileResponse)
async def serve_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/state")
async def current_state():
    def _fetch():
        return _get_json_variable(AIRFLOW_VARIABLE_KEY, {})

    return await asyncio.to_thread(_fetch)


@app.get("/api/history")
async def history():
    def _fetch():
        return _get_json_variable(RUBIK_HISTORY_VARIABLE_KEY, {"active_session_id": None, "sessions": {}})

    return await asyncio.to_thread(_fetch)


@app.post("/api/start")
async def start_solve(payload: dict | None = None):
    if os.environ.get("RUBIK_SOLVER_ENABLE_START") != "true":
        raise HTTPException(
            status_code=403,
            detail="Set RUBIK_SOLVER_ENABLE_START=true before enabling DAG triggers from the plugin.",
        )

    scramble = (payload or {}).get("scramble", "")

    def _trigger():
        response = requests.post(
            f"{_airflow_api_url()}/api/v2/dags/rubik_init/dagRuns",
            headers=_headers(),
            json={"logical_date": None, "conf": {"scramble": scramble}},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    try:
        return await asyncio.to_thread(_trigger)
    except requests.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=detail)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/dag-runs")
async def dag_runs():
    def _fetch_one(dag_id):
        response = requests.get(
            f"{_airflow_api_url()}/api/v2/dags/{dag_id}/dagRuns",
            headers=_headers(),
            params={"limit": 1, "order_by": "-start_date"},
            timeout=10,
        )
        response.raise_for_status()
        runs = response.json().get("dag_runs", [])
        return {"dag_id": dag_id, "latest_run": runs[0] if runs else None}

    def _fetch():
        return [_fetch_one(dag_id) for dag_id in RUBIK_DAG_IDS]

    try:
        return {"dags": await asyncio.to_thread(_fetch)}
    except requests.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=detail)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


class RubikSolverPlugin(AirflowPlugin):
    name = "rubik_solver"

    fastapi_apps = [
        {
            "app": app,
            "url_prefix": "/rubik-solver",
            "name": "Rubik Solver",
        }
    ]

    external_views = [
        {
            "name": "Rubik Solver",
            "href": "rubik-solver/ui",
            "destination": "nav",
            "category": "browse",
            "url_route": "rubik-solver",
        }
    ]

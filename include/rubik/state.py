"""Airflow Variable-backed state helpers for the Rubik solver."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from include.rubik.constants import AIRFLOW_VARIABLE_KEY, RUBIK_HISTORY_VARIABLE_KEY


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_variable(key: str, default: Any) -> Any:
    from airflow.sdk import Variable

    value = Variable.get(key, default=default, deserialize_json=True)
    return copy.deepcopy(value)


def _set_variable(key: str, value: Any) -> None:
    from airflow.sdk import Variable

    Variable.set(key=key, value=value, serialize_json=True)


def load_current_state() -> dict[str, Any]:
    state = _get_variable(AIRFLOW_VARIABLE_KEY, None)
    if state is None:
        raise ValueError("Rubik cube state is missing. Trigger rubik_init before solver phase DAGs.")
    return state


def save_current_state(state: dict[str, Any]) -> None:
    _set_variable(AIRFLOW_VARIABLE_KEY, state)


def _load_history() -> dict[str, Any]:
    history = _get_variable(RUBIK_HISTORY_VARIABLE_KEY, None)
    if history is None:
        return {"sessions": {}}
    history.setdefault("sessions", {})
    return history


def _save_history(history: dict[str, Any]) -> None:
    _set_variable(RUBIK_HISTORY_VARIABLE_KEY, history)


def _session_entry(history: dict[str, Any], session_id: str, state: dict[str, Any]) -> dict[str, Any]:
    sessions = history.setdefault("sessions", {})
    entry = sessions.setdefault(
        session_id,
        {
            "session_id": session_id,
            "status": state.get("status", "running"),
            "scramble": state.get("scramble", []),
            "started_at": _now_iso(),
            "snapshots": [],
        },
    )
    entry.setdefault("snapshots", [])
    return entry


def start_session(session_id: str, state: dict[str, Any]) -> None:
    history = _load_history()
    history["sessions"][session_id] = {
        "session_id": session_id,
        "status": "running",
        "scramble": state.get("scramble", []),
        "started_at": _now_iso(),
        "snapshots": [],
    }
    _save_history(history)


def record_snapshot(
    state: dict[str, Any],
    dag_id: str,
    task_id: str,
    moves: list[str],
    status: str,
) -> None:
    session_id = state.get("session_id", "manual")
    history = _load_history()
    entry = _session_entry(history, session_id, state)
    entry["status"] = status
    entry["snapshots"].append(
        {
            "recorded_at": _now_iso(),
            "dag_id": dag_id,
            "task_id": task_id,
            "phase": state.get("phase"),
            "iteration": state.get("iteration", 0),
            "status": status,
            "moves": list(moves),
            "total_moves": state.get("total_moves", 0),
            "cube": copy.deepcopy(state.get("cube")),
        }
    )
    _save_history(history)


def record_move_snapshots(
    state: dict[str, Any],
    dag_id: str,
    task_id: str,
    moves: list[str],
    status: str,
) -> None:
    record_snapshot(state, dag_id, task_id, moves, status)


def mark_session_failed(state: dict[str, Any], dag_id: str, task_id: str, reason: str) -> None:
    state["status"] = "failed"
    state["failure_reason"] = reason
    save_current_state(state)
    record_snapshot(state, dag_id, task_id, [], "failed")


def mark_session_complete(state: dict[str, Any], dag_id: str, task_id: str) -> None:
    state["status"] = "complete"
    save_current_state(state)
    record_snapshot(state, dag_id, task_id, [], "complete")

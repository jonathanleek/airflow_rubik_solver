"""Airflow Variable-backed state helpers for the Rubik solver."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from include.rubik.constants import AIRFLOW_VARIABLE_KEY, RUBIK_HISTORY_VARIABLE_KEY
from include.rubik.cube import apply_move


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


def _empty_history() -> dict[str, Any]:
    return {
        "active_session_id": None,
        "sessions": {},
    }


def load_history() -> dict[str, Any]:
    history = _get_variable(RUBIK_HISTORY_VARIABLE_KEY, None)
    if history is None:
        return _empty_history()
    history.setdefault("active_session_id", None)
    history.setdefault("sessions", {})
    return history


def save_history(history: dict[str, Any]) -> None:
    _set_variable(RUBIK_HISTORY_VARIABLE_KEY, history)


def start_session(session_id: str, state: dict[str, Any]) -> None:
    history = load_history()
    now = _now_iso()
    history["active_session_id"] = session_id
    history["sessions"][session_id] = {
        "session_id": session_id,
        "status": "running",
        "created_at": now,
        "updated_at": now,
        "scramble": state.get("scramble", []),
        "current": copy.deepcopy(state),
        "history": [],
    }
    save_history(history)
    record_snapshot(state, "rubik_init", "initialize_cube", [], "initialized")


def _get_session(history: dict[str, Any], state: dict[str, Any], status: str) -> dict[str, Any]:
    session_id = state.get("session_id", "manual")
    history["active_session_id"] = session_id
    session = history["sessions"].setdefault(
        session_id,
        {
            "session_id": session_id,
            "status": status,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "scramble": state.get("scramble", []),
            "current": {},
            "history": [],
        },
    )
    session.setdefault("history", [])
    return session


def _append_snapshot(
    session: dict[str, Any],
    state: dict[str, Any],
    dag_id: str,
    task_id: str,
    moves: list[str] | None,
    status: str,
    move_number: int | None = None,
) -> None:
    snapshot = {
        "timestamp": _now_iso(),
        "dag_id": dag_id,
        "task_id": task_id,
        "phase": state.get("phase"),
        "iteration": state.get("iteration", 0),
        "moves": moves or [],
        "total_moves": state.get("total_moves", 0),
        "cube": copy.deepcopy(state.get("cube", {})),
        "status": status,
    }
    if move_number is not None:
        snapshot["move_number"] = move_number
    session["history"].append(snapshot)


def record_snapshot(
    state: dict[str, Any],
    dag_id: str,
    task_id: str,
    moves: list[str] | None = None,
    status: str = "running",
) -> None:
    history = load_history()
    session = _get_session(history, state, status)
    session["status"] = status
    session["updated_at"] = _now_iso()
    session["current"] = copy.deepcopy(state)
    _append_snapshot(session, state, dag_id, task_id, moves, status)
    save_history(history)


def record_move_snapshots(
    state: dict[str, Any],
    dag_id: str,
    task_id: str,
    moves: list[str],
    status: str = "running",
) -> None:
    if not moves:
        return

    history = load_history()
    session = _get_session(history, state, status)
    session["status"] = status
    session["updated_at"] = _now_iso()

    snapshot_state = copy.deepcopy(state)
    starting_total_moves = snapshot_state.get("total_moves", 0)
    applied_moves = list(snapshot_state.get("moves_applied", []))

    for offset, move in enumerate(moves, start=1):
        snapshot_state["cube"] = apply_move(snapshot_state["cube"], move)
        applied_moves.append(move)
        snapshot_state["moves_applied"] = list(applied_moves)
        snapshot_state["total_moves"] = starting_total_moves + offset
        _append_snapshot(
            session,
            snapshot_state,
            dag_id,
            task_id,
            [move],
            status,
            starting_total_moves + offset,
        )

    session["current"] = copy.deepcopy(snapshot_state)
    save_history(history)


def mark_session_failed(state: dict[str, Any], dag_id: str, task_id: str, reason: str) -> None:
    state["status"] = "failed"
    state["failure_reason"] = reason
    save_current_state(state)
    record_snapshot(state, dag_id, task_id, [], "failed")


def mark_session_complete(state: dict[str, Any], dag_id: str, task_id: str) -> None:
    state["status"] = "complete"
    save_current_state(state)
    record_snapshot(state, dag_id, task_id, [], "complete")

"""Airflow Variable-backed state helpers for the Rubik solver."""

import copy
import json
from datetime import datetime, timezone

from airflow.sdk import Variable

from include.rubik.constants import AIRFLOW_VARIABLE_KEY, RUBIK_HISTORY_VARIABLE_KEY
from include.rubik.cube import apply_move


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_current_state():
    raw = Variable.get(AIRFLOW_VARIABLE_KEY)
    return json.loads(raw)


def save_current_state(state):
    Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))


def _empty_history():
    return {
        "active_session_id": None,
        "sessions": {},
    }


def load_history():
    raw = Variable.get(RUBIK_HISTORY_VARIABLE_KEY, default=None)
    if not raw:
        return _empty_history()
    return json.loads(raw)


def save_history(history):
    Variable.set(RUBIK_HISTORY_VARIABLE_KEY, json.dumps(history))


def start_session(session_id, state):
    history = load_history()
    history["active_session_id"] = session_id
    history["sessions"][session_id] = {
        "session_id": session_id,
        "status": "running",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "scramble": state.get("scramble", []),
        "current": copy.deepcopy(state),
        "history": [],
    }
    save_history(history)
    record_snapshot(state, "rubik_init", "initialize_cube", [], "initialized")


def _get_session(history, state, status):
    session_id = state.get("session_id", "default")
    history["active_session_id"] = session_id
    session = history["sessions"].setdefault(
        session_id,
        {
            "session_id": session_id,
            "status": status,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "scramble": state.get("scramble", []),
            "current": {},
            "history": [],
        },
    )
    return session


def _append_snapshot(session, state, dag_id, task_id, moves, status, move_number=None):
    snapshot = {
        "timestamp": utc_now_iso(),
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
    session.setdefault("history", []).append(snapshot)


def record_snapshot(state, dag_id, task_id, moves=None, status="running"):
    history = load_history()
    session = _get_session(history, state, status)
    session["status"] = status
    session["updated_at"] = utc_now_iso()
    session["current"] = copy.deepcopy(state)
    _append_snapshot(session, state, dag_id, task_id, moves, status)
    save_history(history)


def record_move_snapshots(state, dag_id, task_id, moves, status="running"):
    if not moves:
        return

    history = load_history()
    session = _get_session(history, state, status)
    session["status"] = status
    session["updated_at"] = utc_now_iso()

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


def mark_session_failed(state, dag_id, task_id, reason):
    state["status"] = "failed"
    state["error"] = reason
    save_current_state(state)
    record_snapshot(state, dag_id, task_id, [], "failed")


def mark_session_complete(state, dag_id, task_id):
    state["status"] = "complete"
    save_current_state(state)
    record_snapshot(state, dag_id, task_id, [], "complete")

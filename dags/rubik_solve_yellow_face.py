"""Phase 5: Solve the yellow face (OLL corners)."""

from airflow.sdk import dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.state import load_current_state, mark_session_failed, record_move_snapshots, record_snapshot, save_current_state
from include.rubik.constants import (
    MAX_ITERATIONS,
    NEXT_PHASE,
    PHASE_DAG_IDS,
)
from include.rubik.solver import (
    detect_yellow_face_case,
    is_yellow_face_solved,
    solve_yellow_face_step,
)


@dag(
    dag_id="rubik_solve_yellow_face",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_yellow_face():
    @task
    def read_state():
        return load_current_state()

    @task.branch
    def check_phase_solved(state):
        cube = state["cube"]
        iteration = state.get("iteration", 0)

        if is_yellow_face_solved(cube):
            return "prepare_next_phase"
        if iteration >= MAX_ITERATIONS["yellow_face"]:
            return "max_iterations_exceeded"
        return "detect_case"

    @task.branch
    def detect_case(state):
        cube = state["cube"]
        case = detect_yellow_face_case(cube)
        case_map = {
            "sune": "apply_sune",
            "antisune": "apply_antisune",
            "no_fish": "apply_no_fish",
            "no_yellow_corners": "apply_no_corners",
        }
        return case_map.get(case, "apply_no_fish")

    @task
    def apply_sune(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_face_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_face", "apply_sune", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Sune: applied {len(moves)} moves"

    @task
    def apply_antisune(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_face_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_face", "apply_antisune", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Antisune: applied {len(moves)} moves"

    @task
    def apply_no_fish(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_face_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_face", "apply_no_fish", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"No fish: applied {len(moves)} moves"

    @task
    def apply_no_corners(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_face_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_face", "apply_no_corners", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"No corners: applied {len(moves)} moves"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["yellow_face"]
        state["phase"] = next_phase
        state["iteration"] = 0
        save_current_state(state)
        record_snapshot(state, "rubik_solve_yellow_face", "prepare_next_phase", [], "running")
        return f"Yellow face solved! Moving to {next_phase}"

    @task
    def max_iterations_exceeded(state):
        reason = f"Yellow face phase exceeded max iterations ({MAX_ITERATIONS['yellow_face']})"
        mark_session_failed(state, "rubik_solve_yellow_face", "max_iterations_exceeded", reason)
        raise Exception(reason)

    state = read_state()
    branch = check_phase_solved(state)

    case_branch = detect_case(state)
    sune_step = apply_sune(state)
    antisune_step = apply_antisune(state)
    no_fish_step = apply_no_fish(state)
    no_corners_step = apply_no_corners(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded(state)

    trigger_self = TriggerDagRunOperator(
        task_id="trigger_self",
        trigger_dag_id="rubik_solve_yellow_face",
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    trigger_next = TriggerDagRunOperator(
        task_id="trigger_next_phase",
        trigger_dag_id=PHASE_DAG_IDS[NEXT_PHASE["yellow_face"]],
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    branch >> [case_branch, next_phase, max_iter]
    case_branch >> [sune_step, antisune_step, no_fish_step, no_corners_step]
    sune_step >> trigger_self
    antisune_step >> trigger_self
    no_fish_step >> trigger_self
    no_corners_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_yellow_face()

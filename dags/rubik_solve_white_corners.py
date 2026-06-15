"""Phase 2: Solve the white corners on the D face."""

from airflow.sdk import dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.lineage import phase_handoff_asset
from include.rubik.state import load_current_state, mark_session_failed, record_move_snapshots, record_snapshot, save_current_state
from include.rubik.constants import (
    MAX_ITERATIONS,
    NEXT_PHASE,
    PHASE_DAG_IDS,
)
from include.rubik.solver import is_white_corners_solved, solve_white_corners_step


@dag(
    dag_id="rubik_solve_white_corners",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_white_corners():
    @task(inlets=[phase_handoff_asset("white_corners")])
    def read_state():
        return load_current_state()

    @task.branch
    def check_phase_solved(state):
        cube = state["cube"]
        iteration = state.get("iteration", 0)

        if is_white_corners_solved(cube):
            return "prepare_next_phase"
        if iteration >= MAX_ITERATIONS["white_corners"]:
            return "max_iterations_exceeded"
        return "apply_algorithm"

    @task
    def apply_algorithm(state):
        cube = state["cube"]
        new_cube, moves = solve_white_corners_step(cube)
        record_move_snapshots(state, "rubik_solve_white_corners", "apply_algorithm", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Applied {len(moves)} moves: {' '.join(moves)}"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["white_corners"]
        state["phase"] = next_phase
        state["iteration"] = 0
        save_current_state(state)
        record_snapshot(state, "rubik_solve_white_corners", "prepare_next_phase", [], "running")
        return f"White corners solved! Moving to {next_phase}"

    @task
    def max_iterations_exceeded(state):
        reason = f"White corners phase exceeded max iterations ({MAX_ITERATIONS['white_corners']})"
        mark_session_failed(state, "rubik_solve_white_corners", "max_iterations_exceeded", reason)
        raise Exception(reason)

    state = read_state()
    branch = check_phase_solved(state)

    apply_step = apply_algorithm(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded(state)

    trigger_self = TriggerDagRunOperator(
        task_id="trigger_self",
        trigger_dag_id="rubik_solve_white_corners",
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    trigger_next = TriggerDagRunOperator(
        task_id="trigger_next_phase",
        trigger_dag_id=PHASE_DAG_IDS[NEXT_PHASE["white_corners"]],
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
        outlets=[phase_handoff_asset(NEXT_PHASE["white_corners"])],
    )

    branch >> [apply_step, next_phase, max_iter]
    apply_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_white_corners()

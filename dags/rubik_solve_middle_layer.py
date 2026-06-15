"""Phase 3: Solve the middle layer edges."""

from airflow.sdk import dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.state import load_current_state, mark_session_failed, record_move_snapshots, record_snapshot, save_current_state
from include.rubik.constants import (
    MAX_ITERATIONS,
    NEXT_PHASE,
    PHASE_DAG_IDS,
)
from include.rubik.solver import (
    detect_middle_case,
    is_middle_layer_solved,
    solve_middle_step,
)


@dag(
    dag_id="rubik_solve_middle_layer",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_middle_layer():
    @task
    def read_state():
        return load_current_state()

    @task.branch
    def check_phase_solved(state):
        cube = state["cube"]
        iteration = state.get("iteration", 0)

        if is_middle_layer_solved(cube):
            return "prepare_next_phase"
        if iteration >= MAX_ITERATIONS["middle_layer"]:
            return "max_iterations_exceeded"
        return "detect_case"

    @task.branch
    def detect_case(state):
        cube = state["cube"]
        case = detect_middle_case(cube)
        if case == "insert_from_top":
            return "apply_insert"
        elif case == "eject":
            return "apply_eject"
        return "apply_insert"

    @task
    def apply_insert(state):
        cube = state["cube"]
        new_cube, moves = solve_middle_step(cube)
        record_move_snapshots(state, "rubik_solve_middle_layer", "apply_insert", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Insert: applied {len(moves)} moves"

    @task
    def apply_eject(state):
        cube = state["cube"]
        new_cube, moves = solve_middle_step(cube)
        record_move_snapshots(state, "rubik_solve_middle_layer", "apply_eject", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Eject: applied {len(moves)} moves"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["middle_layer"]
        state["phase"] = next_phase
        state["iteration"] = 0
        save_current_state(state)
        record_snapshot(state, "rubik_solve_middle_layer", "prepare_next_phase", [], "running")
        return f"Middle layer solved! Moving to {next_phase}"

    @task
    def max_iterations_exceeded(state):
        reason = f"Middle layer phase exceeded max iterations ({MAX_ITERATIONS['middle_layer']})"
        mark_session_failed(state, "rubik_solve_middle_layer", "max_iterations_exceeded", reason)
        raise Exception(reason)

    state = read_state()
    branch = check_phase_solved(state)

    case_branch = detect_case(state)
    insert_step = apply_insert(state)
    eject_step = apply_eject(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded(state)

    trigger_self = TriggerDagRunOperator(
        task_id="trigger_self",
        trigger_dag_id="rubik_solve_middle_layer",
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    trigger_next = TriggerDagRunOperator(
        task_id="trigger_next_phase",
        trigger_dag_id=PHASE_DAG_IDS[NEXT_PHASE["middle_layer"]],
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    branch >> [case_branch, next_phase, max_iter]
    case_branch >> [insert_step, eject_step]
    insert_step >> trigger_self
    eject_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_middle_layer()

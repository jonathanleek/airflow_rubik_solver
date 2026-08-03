"""Phase 7: Position yellow edges (PLL edges)."""

from airflow.sdk import dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.lineage import phase_handoff_asset
from include.rubik.state import load_current_state, mark_session_failed, record_move_snapshots, record_snapshot, save_current_state
from include.rubik.constants import (
    MAX_ITERATIONS,
    NEXT_PHASE,
    PHASE_DAG_IDS,
)
from include.rubik.solver import (
    detect_yellow_edges_case,
    is_yellow_edges_positioned,
    solve_yellow_edges_step,
)


@dag(
    dag_id="rubik_solve_yellow_edges",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_yellow_edges():
    @task(inlets=[phase_handoff_asset("yellow_edges")])
    def read_state():
        return load_current_state()

    @task.branch
    def check_phase_solved(state):
        cube = state["cube"]
        iteration = state.get("iteration", 0)

        if is_yellow_edges_positioned(cube):
            return "prepare_next_phase"
        if iteration >= MAX_ITERATIONS["yellow_edges"]:
            return "max_iterations_exceeded"
        return "detect_case"

    @task.branch
    def detect_case(state):
        cube = state["cube"]
        case = detect_yellow_edges_case(cube)
        case_map = {
            "cw_cycle": "apply_cw_cycle",
            "ccw_cycle": "apply_ccw_cycle",
            "opposite_swap": "apply_opposite_swap",
            "adjacent_swap": "apply_adjacent_swap",
        }
        return case_map.get(case, "apply_cw_cycle")

    @task
    def apply_cw_cycle(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_edges_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_edges", "apply_cw_cycle", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"CW cycle: applied {len(moves)} moves"

    @task
    def apply_ccw_cycle(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_edges_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_edges", "apply_ccw_cycle", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"CCW cycle: applied {len(moves)} moves"

    @task
    def apply_opposite_swap(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_edges_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_edges", "apply_opposite_swap", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Opposite swap: applied {len(moves)} moves"

    @task
    def apply_adjacent_swap(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_edges_step(cube)
        record_move_snapshots(state, "rubik_solve_yellow_edges", "apply_adjacent_swap", moves, "running")
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        save_current_state(state)
        return f"Adjacent swap: applied {len(moves)} moves"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["yellow_edges"]
        state["phase"] = next_phase
        state["iteration"] = 0
        save_current_state(state)
        record_snapshot(state, "rubik_solve_yellow_edges", "prepare_next_phase", [], "running")
        return f"Yellow edges positioned! Moving to {next_phase}"

    @task
    def max_iterations_exceeded(state):
        reason = f"Yellow edges phase exceeded max iterations ({MAX_ITERATIONS['yellow_edges']})"
        mark_session_failed(state, "rubik_solve_yellow_edges", "max_iterations_exceeded", reason)
        raise Exception(reason)

    state = read_state()
    branch = check_phase_solved(state)

    case_branch = detect_case(state)
    cw_step = apply_cw_cycle(state)
    ccw_step = apply_ccw_cycle(state)
    opp_step = apply_opposite_swap(state)
    adj_step = apply_adjacent_swap(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded(state)

    trigger_self = TriggerDagRunOperator(
        task_id="trigger_self",
        trigger_dag_id="rubik_solve_yellow_edges",
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    trigger_next = TriggerDagRunOperator(
        task_id="trigger_next_phase",
        trigger_dag_id=PHASE_DAG_IDS[NEXT_PHASE["yellow_edges"]],
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
        outlets=[phase_handoff_asset(NEXT_PHASE["yellow_edges"])],
    )

    branch >> [case_branch, next_phase, max_iter]
    case_branch >> [cw_step, ccw_step, opp_step, adj_step]
    cw_step >> trigger_self
    ccw_step >> trigger_self
    opp_step >> trigger_self
    adj_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_yellow_edges()

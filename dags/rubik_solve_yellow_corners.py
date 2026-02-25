"""Phase 6: Position yellow corners (PLL corners)."""

import json

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.constants import (
    AIRFLOW_VARIABLE_KEY,
    MAX_ITERATIONS,
    NEXT_PHASE,
    PHASE_DAG_IDS,
)
from include.rubik.solver import (
    detect_yellow_corners_case,
    is_yellow_corners_positioned,
    solve_yellow_corners_step,
)


@dag(
    dag_id="rubik_solve_yellow_corners",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_yellow_corners():
    @task
    def read_state():
        raw = Variable.get(AIRFLOW_VARIABLE_KEY)
        return json.loads(raw)

    @task.branch
    def check_phase_solved(state):
        cube = state["cube"]
        iteration = state.get("iteration", 0)

        if is_yellow_corners_positioned(cube):
            return "prepare_next_phase"
        if iteration >= MAX_ITERATIONS["yellow_corners"]:
            return "max_iterations_exceeded"
        return "detect_case"

    @task.branch
    def detect_case(state):
        cube = state["cube"]
        case = detect_yellow_corners_case(cube)
        case_map = {
            "headlights": "apply_headlights",
            "no_headlights": "apply_no_headlights",
        }
        return case_map.get(case, "apply_no_headlights")

    @task
    def apply_headlights(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_corners_step(cube)
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Headlights: applied {len(moves)} moves"

    @task
    def apply_no_headlights(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_corners_step(cube)
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"No headlights: applied {len(moves)} moves"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["yellow_corners"]
        state["phase"] = next_phase
        state["iteration"] = 0
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Yellow corners positioned! Moving to {next_phase}"

    @task
    def max_iterations_exceeded():
        raise Exception(
            f"Yellow corners phase exceeded max iterations ({MAX_ITERATIONS['yellow_corners']})"
        )

    state = read_state()
    branch = check_phase_solved(state)

    case_branch = detect_case(state)
    headlights_step = apply_headlights(state)
    no_headlights_step = apply_no_headlights(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded()

    trigger_self = TriggerDagRunOperator(
        task_id="trigger_self",
        trigger_dag_id="rubik_solve_yellow_corners",
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    trigger_next = TriggerDagRunOperator(
        task_id="trigger_next_phase",
        trigger_dag_id=PHASE_DAG_IDS[NEXT_PHASE["yellow_corners"]],
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    branch >> [case_branch, next_phase, max_iter]
    case_branch >> [headlights_step, no_headlights_step]
    headlights_step >> trigger_self
    no_headlights_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_yellow_corners()

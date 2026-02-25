"""Phase 4: Solve the yellow cross on the U face (OLL edges)."""

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
    detect_yellow_cross_case,
    is_yellow_cross_solved,
    solve_yellow_cross_step,
)


@dag(
    dag_id="rubik_solve_yellow_cross",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_yellow_cross():
    @task
    def read_state():
        raw = Variable.get(AIRFLOW_VARIABLE_KEY)
        return json.loads(raw)

    @task.branch
    def check_phase_solved(state):
        cube = state["cube"]
        iteration = state.get("iteration", 0)

        if is_yellow_cross_solved(cube):
            return "prepare_next_phase"
        if iteration >= MAX_ITERATIONS["yellow_cross"]:
            return "max_iterations_exceeded"
        return "detect_case"

    @task.branch
    def detect_case(state):
        cube = state["cube"]
        case = detect_yellow_cross_case(cube)
        case_map = {
            "dot": "apply_dot",
            "l_shape": "apply_l_shape",
            "line": "apply_line",
        }
        return case_map.get(case, "apply_dot")

    @task
    def apply_dot(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_cross_step(cube)
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Dot case: applied {len(moves)} moves"

    @task
    def apply_l_shape(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_cross_step(cube)
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"L-shape case: applied {len(moves)} moves"

    @task
    def apply_line(state):
        cube = state["cube"]
        new_cube, moves = solve_yellow_cross_step(cube)
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Line case: applied {len(moves)} moves"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["yellow_cross"]
        state["phase"] = next_phase
        state["iteration"] = 0
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Yellow cross solved! Moving to {next_phase}"

    @task
    def max_iterations_exceeded():
        raise Exception(
            f"Yellow cross phase exceeded max iterations ({MAX_ITERATIONS['yellow_cross']})"
        )

    state = read_state()
    branch = check_phase_solved(state)

    case_branch = detect_case(state)
    dot_step = apply_dot(state)
    l_step = apply_l_shape(state)
    line_step = apply_line(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded()

    trigger_self = TriggerDagRunOperator(
        task_id="trigger_self",
        trigger_dag_id="rubik_solve_yellow_cross",
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    trigger_next = TriggerDagRunOperator(
        task_id="trigger_next_phase",
        trigger_dag_id=PHASE_DAG_IDS[NEXT_PHASE["yellow_cross"]],
        wait_for_completion=False,
        trigger_rule="none_failed_min_one_success",
    )

    branch >> [case_branch, next_phase, max_iter]
    case_branch >> [dot_step, l_step, line_step]
    dot_step >> trigger_self
    l_step >> trigger_self
    line_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_yellow_cross()

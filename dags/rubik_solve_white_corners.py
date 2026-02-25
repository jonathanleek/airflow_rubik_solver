"""Phase 2: Solve the white corners on the D face."""

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
from include.rubik.solver import is_white_corners_solved, solve_white_corners_step


@dag(
    dag_id="rubik_solve_white_corners",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik", "solve"],
)
def rubik_solve_white_corners():
    @task
    def read_state():
        raw = Variable.get(AIRFLOW_VARIABLE_KEY)
        return json.loads(raw)

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
        state["cube"] = new_cube
        state["moves_applied"].extend(moves)
        state["total_moves"] += len(moves)
        state["iteration"] = state.get("iteration", 0) + 1
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Applied {len(moves)} moves: {' '.join(moves)}"

    @task
    def prepare_next_phase(state):
        next_phase = NEXT_PHASE["white_corners"]
        state["phase"] = next_phase
        state["iteration"] = 0
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"White corners solved! Moving to {next_phase}"

    @task
    def max_iterations_exceeded():
        raise Exception(
            f"White corners phase exceeded max iterations ({MAX_ITERATIONS['white_corners']})"
        )

    state = read_state()
    branch = check_phase_solved(state)

    apply_step = apply_algorithm(state)
    next_phase = prepare_next_phase(state)
    max_iter = max_iterations_exceeded()

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
    )

    branch >> [apply_step, next_phase, max_iter]
    apply_step >> trigger_self
    next_phase >> trigger_next


rubik_solve_white_corners()

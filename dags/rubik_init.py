"""Entry point DAG: parse input or generate random scramble, write state to Variable."""

import json

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.constants import AIRFLOW_VARIABLE_KEY, PHASE_DAG_IDS
from include.rubik.cube import (
    apply_algorithm,
    generate_scramble,
    get_solved_state,
    parse_scramble_string,
    validate_state,
)


@dag(
    dag_id="rubik_init",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik"],
    params={"scramble": ""},
)
def rubik_init():
    @task
    def initialize_cube(**context):
        params = context["params"]
        scramble_input = params.get("scramble", "")

        cube = get_solved_state()

        if scramble_input:
            # Parse scramble string
            moves = parse_scramble_string(scramble_input)
            cube, applied = apply_algorithm(cube, moves)
            scramble_moves = applied
        else:
            # Generate random scramble
            scramble_moves = generate_scramble(20)
            cube, _ = apply_algorithm(cube, scramble_moves)

        validate_state(cube)

        state = {
            "cube": cube,
            "moves_applied": [],
            "scramble": scramble_moves,
            "phase": "cross",
            "iteration": 0,
            "total_moves": 0,
        }

        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))
        return f"Initialized cube with scramble: {' '.join(scramble_moves)}"

    init = initialize_cube()

    trigger_cross = TriggerDagRunOperator(
        task_id="trigger_solve_cross",
        trigger_dag_id=PHASE_DAG_IDS["cross"],
        wait_for_completion=False,
    )

    init >> trigger_cross


rubik_init()

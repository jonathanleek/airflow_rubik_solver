"""Entry point DAG: parse input or generate random scramble, write state to Variable."""

from airflow.sdk import dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

from include.rubik.constants import PHASE_DAG_IDS
from include.rubik.cube import (
    apply_algorithm,
    generate_scramble,
    get_solved_state,
    parse_scramble_string,
    validate_state,
)
from include.rubik.lineage import phase_handoff_asset
from include.rubik.state import save_current_state, start_session


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
        dag_run = context.get("dag_run")
        dag_run_conf = dag_run.conf if dag_run and dag_run.conf else {}
        scramble_input = dag_run_conf.get("scramble") or params.get("scramble", "")

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

        session_id = dag_run.run_id if dag_run else "manual"
        state = {
            "session_id": session_id,
            "status": "running",
            "cube": cube,
            "moves_applied": [],
            "scramble": scramble_moves,
            "phase": "cross",
            "iteration": 0,
            "total_moves": 0,
        }

        save_current_state(state)
        start_session(session_id, state)
        return f"Initialized cube with scramble: {' '.join(scramble_moves)}"

    init = initialize_cube()

    trigger_cross = TriggerDagRunOperator(
        task_id="trigger_solve_cross",
        trigger_dag_id=PHASE_DAG_IDS["cross"],
        wait_for_completion=False,
        outlets=[phase_handoff_asset("cross")],
    )

    init >> trigger_cross


rubik_init()

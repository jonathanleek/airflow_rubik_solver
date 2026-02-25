"""Final validation DAG: verify solved state and report solution."""

import json

from airflow.decorators import dag, task
from airflow.models import Variable

from include.rubik.constants import AIRFLOW_VARIABLE_KEY
from include.rubik.cube import is_solved


@dag(
    dag_id="rubik_complete",
    schedule=None,
    max_active_runs=1,
    catchup=False,
    tags=["rubik"],
)
def rubik_complete():
    @task
    def read_state():
        raw = Variable.get(AIRFLOW_VARIABLE_KEY)
        return json.loads(raw)

    @task
    def validate_solution(state):
        cube = state["cube"]
        moves = state["moves_applied"]
        total = state["total_moves"]
        scramble = state.get("scramble", [])

        if not is_solved(cube):
            # Print cube state for debugging
            for face in ["U", "D", "F", "B", "L", "R"]:
                print(f"{face}: {cube[face]}")
            raise Exception("Cube is NOT solved! Solution failed.")

        report = (
            f"CUBE SOLVED!\n"
            f"Scramble: {' '.join(scramble)}\n"
            f"Solution: {' '.join(moves)}\n"
            f"Total moves: {total}\n"
            f"Move count: {len(moves)}"
        )
        print(report)

        state["phase"] = "complete"
        Variable.set(AIRFLOW_VARIABLE_KEY, json.dumps(state))

        return report

    state = read_state()
    validate_solution(state)


rubik_complete()

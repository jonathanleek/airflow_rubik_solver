"""Final validation DAG: verify solved state and report solution."""

from airflow.sdk import dag, task

from include.rubik.cube import is_solved
from include.rubik.state import load_current_state, mark_session_complete


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
        return load_current_state()

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
        mark_session_complete(state, "rubik_complete", "validate_solution")

        return report

    state = read_state()
    validate_solution(state)


rubik_complete()

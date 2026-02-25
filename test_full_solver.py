"""End-to-end solver test: run all phases step by step on scrambled cubes."""

import copy
import sys
sys.path.insert(0, ".")

from include.rubik.cube import apply_algorithm, get_solved_state, generate_scramble, is_solved
from include.rubik.solver import (
    is_cross_solved, solve_cross_step,
    is_white_corners_solved, solve_white_corners_step,
    is_middle_layer_solved, solve_middle_step,
    is_yellow_cross_solved, solve_yellow_cross_step,
    is_yellow_face_solved, solve_yellow_face_step,
    is_yellow_corners_positioned, solve_yellow_corners_step,
    is_yellow_edges_positioned, solve_yellow_edges_step,
)

def run_phase(state, name, is_solved_fn, step_fn, max_iter=50):
    """Run a phase until solved or max iterations."""
    iteration = 0
    total_moves = 0
    while not is_solved_fn(state) and iteration < max_iter:
        new_state, moves = step_fn(state)
        if not moves:
            print(f"  [{name}] iter {iteration}: NO MOVES returned (stuck!)")
            return state, False, total_moves
        total_moves += len(moves)
        state = new_state
        iteration += 1
        if iteration <= 5 or iteration % 10 == 0:
            print(f"  [{name}] iter {iteration}: {len(moves)} moves -> {' '.join(moves)}")

    if is_solved_fn(state):
        print(f"  [{name}] SOLVED in {iteration} iterations, {total_moves} moves")
        return state, True, total_moves
    else:
        print(f"  [{name}] FAILED after {iteration} iterations, {total_moves} moves")
        return state, False, total_moves


def print_cube(state):
    """Print cube state compactly."""
    for face in ["U", "D", "F", "B", "L", "R"]:
        print(f"    {face}: {''.join(state[face])}")


def test_scramble(scramble_moves, idx=0):
    """Test the full solver on a specific scramble."""
    state = get_solved_state()
    state, _ = apply_algorithm(state, scramble_moves)

    print(f"\n{'='*60}")
    print(f"Test {idx}: Scramble = {scramble_moves}")
    print(f"{'='*60}")

    all_ok = True
    total = 0

    phases = [
        ("Cross", is_cross_solved, solve_cross_step),
        ("White Corners", is_white_corners_solved, solve_white_corners_step),
        ("Middle Layer", is_middle_layer_solved, solve_middle_step),
        ("Yellow Cross", is_yellow_cross_solved, solve_yellow_cross_step),
        ("Yellow Face", is_yellow_face_solved, solve_yellow_face_step),
        ("Yellow Corners", is_yellow_corners_positioned, solve_yellow_corners_step),
        ("Yellow Edges", is_yellow_edges_positioned, solve_yellow_edges_step),
    ]

    for name, check_fn, step_fn in phases:
        if check_fn(state):
            print(f"  [{name}] Already solved, skipping")
            continue
        state, ok, moves = run_phase(state, name, check_fn, step_fn)
        total += moves
        if not ok:
            print(f"  CUBE STATE AFTER FAILURE:")
            print_cube(state)
            all_ok = False
            break

    if all_ok:
        # Final check: is the cube fully solved?
        solved = is_solved(state)
        if not solved:
            # Might need a final U adjustment
            for u in ["U", "U'", "U2"]:
                test, _ = apply_algorithm(state, u)
                if is_solved(test):
                    state = test
                    total += 1
                    solved = True
                    break

        if solved:
            print(f"\n  CUBE FULLY SOLVED! Total moves: {total}")
        else:
            print(f"\n  CUBE NOT FULLY SOLVED after all phases!")
            print_cube(state)
            all_ok = False

    return all_ok


# Test with several scrambles
scrambles = [
    "R U R' U'",
    "R U F' L D B",
    "R2 U' F L2 D B' R U2 L F2",
    "R U R' F' R U R' U' R' F R2 U' R'",
    "F R U' R' U' R U R' F' R U R' U' R' F R F'",
]

# Also some random scrambles
import random
random.seed(42)
for i in range(5):
    s = generate_scramble(20)
    scrambles.append(" ".join(s))

results = []
for i, s in enumerate(scrambles):
    ok = test_scramble(s, i)
    results.append(ok)

print(f"\n{'='*60}")
print(f"RESULTS: {sum(results)}/{len(results)} passed")
for i, (ok, s) in enumerate(zip(results, scrambles)):
    status = "PASS" if ok else "FAIL"
    print(f"  {status}: {s[:50]}{'...' if len(s) > 50 else ''}")

"""Find middle layer algorithms that PRESERVE already-solved middle edges."""
import sys, copy
sys.path.insert(0, ".")

from itertools import product
from include.rubik.cube import apply_move, apply_algorithm, get_solved_state, generate_scramble
from include.rubik.solver import (
    is_cross_solved, solve_cross_step,
    is_white_corners_solved, solve_white_corners_step,
    _is_middle_edge_solved, _find_edge, _gs, _edge_layer,
    _edge_side_face_in_u, _edge_color_on_face,
    MIDDLE_EDGES, MIDDLE_EDGE_TARGETS, _FACE_ORDER, _COLOR_TO_FACE,
)

def solve_phase(state, check_fn, step_fn, max_iter=50):
    for _ in range(max_iter):
        if check_fn(state):
            return state, True
        state, moves = step_fn(state)
        if not moves:
            return state, False
    return state, check_fn(state)

def d_layer_ok(state):
    if not all(state["D"][i] == "W" for i in range(9)):
        return False
    for face, color in {"F": "G", "R": "R", "B": "B", "L": "O"}.items():
        for idx in [6, 7, 8]:
            if state[face][idx] != color:
                return False
    return True

def other_middle_preserved(state, test_state, exclude_edge):
    """Check that all middle edges except exclude_edge are the same."""
    for edge_name in ["FR", "FL", "BR", "BL"]:
        if edge_name == exclude_edge:
            continue
        pos = MIDDLE_EDGES[edge_name]
        for face, idx in pos:
            if _gs(state, face, idx) != _gs(test_state, face, idx):
                return False
    return True

import random
random.seed(42)

# Build test states for FR slot with both orientations
# We need: D layer + other 3 middle edges solved, FR unsolved, FR edge in U layer
print("Building test states for FR slot...")
test_states = {"FR_RIGHT": None, "FR_LEFT": None}

for attempt in range(500):
    scramble = generate_scramble(20)
    state = get_solved_state()
    state, _ = apply_algorithm(state, " ".join(scramble))
    state, ok1 = solve_phase(state, is_cross_solved, solve_cross_step)
    if not ok1:
        continue
    state, ok2 = solve_phase(state, is_white_corners_solved, solve_white_corners_step)
    if not ok2 or not d_layer_ok(state):
        continue

    # Check if FR is unsolved and edge is in U
    if _is_middle_edge_solved(state, "FR"):
        continue
    c1, c2 = "G", "R"
    loc = _find_edge(state, c1, c2)
    if not loc or _edge_layer(loc) != "U":
        continue

    # Check if other 3 middle edges are solved
    others_solved = all(_is_middle_edge_solved(state, e) for e in ["FL", "BR", "BL"])
    if not others_solved:
        continue

    # Determine orientation
    side_face = _edge_side_face_in_u(loc)
    side_color = _edge_color_on_face(loc, side_face)
    u_color = _edge_color_on_face(loc, "U")

    # Align above F center
    target_face = _COLOR_TO_FACE[side_color]
    cur_idx = _FACE_ORDER.index(side_face)
    target_idx = _FACE_ORDER.index(target_face)
    u_rot = (target_idx - cur_idx) % 4
    if u_rot:
        u_str = {1: "U", 2: "U2", 3: "U'"}[u_rot]
        state, _ = apply_algorithm(state, u_str)

    loc = _find_edge(state, c1, c2)
    u_color = _edge_color_on_face(loc, "U")
    u_target = _COLOR_TO_FACE[u_color]
    side_after = _edge_side_face_in_u(loc)

    tcf_idx = _FACE_ORDER.index(side_after)
    utf_idx = _FACE_ORDER.index(u_target)
    diff = (utf_idx - tcf_idx) % 4

    if diff == 1:
        key = "FR_RIGHT"
    elif diff == 3:
        key = "FR_LEFT"
    else:
        continue

    if test_states[key] is None:
        test_states[key] = state
        print(f"  Found {key} state (attempt {attempt})")

    if all(v is not None for v in test_states.values()):
        break

# Now search for safe algorithms for FR slot
move_set = ["U", "U'", "U2", "R", "R'", "R2", "F", "F'", "F2"]

for key, state in test_states.items():
    if state is None:
        print(f"\n{key}: No test state found!")
        continue

    print(f"\nSearching {key}...")
    print(f"  Other middle edges preserved: FL={_is_middle_edge_solved(state, 'FL')}, BR={_is_middle_edge_solved(state, 'BR')}, BL={_is_middle_edge_solved(state, 'BL')}")

    edge_positions = MIDDLE_EDGES["FR"]
    target_colors = MIDDLE_EDGE_TARGETS["FR"]

    found = []
    for length in range(5, 11):
        count = 0
        for combo in product(move_set, repeat=length):
            skip = False
            for i in range(len(combo) - 1):
                if combo[i][0] == combo[i + 1][0]:
                    skip = True
                    break
            if skip:
                continue

            count += 1
            alg_str = " ".join(combo)
            try:
                test, _ = apply_algorithm(state, alg_str)
            except:
                continue

            # Check FR solved
            ok = all(
                _gs(test, face, idx) == target_colors[i]
                for i, (face, idx) in enumerate(edge_positions)
            )
            if not ok:
                continue
            # Check D layer
            if not d_layer_ok(test):
                continue
            # Check other middle edges PRESERVED
            if not other_middle_preserved(state, test, "FR"):
                continue

            found.append(alg_str)
            if len(found) <= 5:
                print(f"  FOUND ({length} moves): {alg_str}")

        if found:
            print(f"  Total: {len(found)} solutions of length {length} (searched {count} combos)")
            break
        else:
            print(f"  Length {length}: {count} combos, no solution")

    if not found:
        print(f"  NO SAFE ALGORITHM FOUND up to length 10!")

# Also search using the full 18-move set for length 7-8
for key, state in test_states.items():
    if state is None:
        continue
    print(f"\nExtended search for {key} (all 18 moves)...")
    full_moves = ["U", "U'", "U2", "R", "R'", "R2", "F", "F'", "F2",
                   "L", "L'", "L2", "D", "D'", "D2", "B", "B'", "B2"]
    edge_positions = MIDDLE_EDGES["FR"]
    target_colors = MIDDLE_EDGE_TARGETS["FR"]

    found = []
    for length in range(7, 10):
        count = 0
        for combo in product(full_moves, repeat=length):
            skip = False
            for i in range(len(combo) - 1):
                if combo[i][0] == combo[i + 1][0]:
                    skip = True
                    break
            if skip:
                continue
            count += 1
            if count > 5000000:
                break

            alg_str = " ".join(combo)
            try:
                test, _ = apply_algorithm(state, alg_str)
            except:
                continue

            ok = all(
                _gs(test, face, idx) == target_colors[i]
                for i, (face, idx) in enumerate(edge_positions)
            )
            if not ok:
                continue
            if not d_layer_ok(test):
                continue
            if not other_middle_preserved(state, test, "FR"):
                continue

            found.append(alg_str)
            if len(found) <= 5:
                print(f"  FOUND ({length} moves): {alg_str}")

        if found:
            print(f"  Total: {len(found)} solutions of length {length}")
            break
        else:
            print(f"  Length {length}: searched {count} combos, no solution")

    if not found:
        print(f"  NO SAFE ALGORITHM FOUND with full move set!")

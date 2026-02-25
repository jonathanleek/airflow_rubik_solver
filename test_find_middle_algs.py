"""Find correct middle layer algorithms by brute-force on realistic states."""
import sys, copy
sys.path.insert(0, ".")

from itertools import product
from include.rubik.cube import apply_move, apply_algorithm, get_solved_state, generate_scramble
from include.rubik.solver import (
    is_cross_solved, solve_cross_step,
    is_white_corners_solved, solve_white_corners_step,
    is_middle_layer_solved, _is_middle_edge_solved,
    _find_edge, _gs, _edge_layer, _edge_side_face_in_u, _edge_color_on_face,
    _FACE_ORDER, _COLOR_TO_FACE, MIDDLE_EDGES, MIDDLE_EDGE_TARGETS,
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
    """Check full D layer is intact."""
    if not all(state["D"][i] == "W" for i in range(9)):
        return False
    targets = {"F": "G", "R": "R", "B": "B", "L": "O"}
    for face, color in targets.items():
        for idx in [6, 7, 8]:
            if state[face][idx] != color:
                return False
    return True

# Step 1: Verify cross + corners still work
print("="*60)
print("Verifying cross + corners solvers work...")
print("="*60)
import random
random.seed(42)
pass_count = 0
for i in range(10):
    scramble = generate_scramble(20)
    s = get_solved_state()
    s, _ = apply_algorithm(s, " ".join(scramble))
    s, ok1 = solve_phase(s, is_cross_solved, solve_cross_step)
    s, ok2 = solve_phase(s, is_white_corners_solved, solve_white_corners_step)
    d_ok = d_layer_ok(s) if ok1 and ok2 else False
    status = "PASS" if ok1 and ok2 and d_ok else "FAIL"
    print(f"  Test {i}: cross={'OK' if ok1 else 'FAIL'}, corners={'OK' if ok2 else 'FAIL'}, d_layer={'OK' if d_ok else 'FAIL'} -> {status}")
    if status == "PASS":
        pass_count += 1
print(f"  {pass_count}/10 passed\n")

if pass_count == 0:
    print("Cross+corners broken, cannot proceed")
    sys.exit(1)

# Step 2: Find a realistic post-corners state and search for middle layer algorithms
print("="*60)
print("Finding correct middle layer insert algorithms...")
print("="*60)

random.seed(999)
# We need to find algorithms for FR slot with both orientations
# Orient 1: G on side face (matching F center), R on U face -> insert RIGHT
# Orient 2: R on side face, G on U face -> insert LEFT

found_right = []
found_left = []

for attempt in range(100):
    scramble = generate_scramble(20)
    state = get_solved_state()
    state, _ = apply_algorithm(state, " ".join(scramble))
    state, ok1 = solve_phase(state, is_cross_solved, solve_cross_step)
    if not ok1:
        continue
    state, ok2 = solve_phase(state, is_white_corners_solved, solve_white_corners_step)
    if not ok2 or not d_layer_ok(state):
        continue

    # Find an unsolved middle edge in U layer
    for edge_name in ["FR", "FL", "BR", "BL"]:
        if _is_middle_edge_solved(state, edge_name):
            continue
        c1, c2 = MIDDLE_EDGE_TARGETS[edge_name]
        loc = _find_edge(state, c1, c2)
        if not loc or _edge_layer(loc) != "U":
            continue

        side_face = _edge_side_face_in_u(loc)
        side_color = _edge_color_on_face(loc, side_face)
        u_color = _edge_color_on_face(loc, "U")

        # Skip yellow edges
        if u_color == "Y" or side_color == "Y":
            continue

        # Align edge above target center
        target_face = _COLOR_TO_FACE[side_color]
        cur_idx = _FACE_ORDER.index(side_face)
        target_idx = _FACE_ORDER.index(target_face)
        u_rot = (target_idx - cur_idx) % 4
        test_state = copy.deepcopy(state)
        if u_rot:
            u_str = {1: "U", 2: "U2", 3: "U'"}[u_rot]
            test_state, _ = apply_algorithm(test_state, u_str)

        # Determine direction
        u_target = _COLOR_TO_FACE[_edge_color_on_face(_find_edge(test_state, c1, c2), "U")]
        side_after = _edge_side_face_in_u(_find_edge(test_state, c1, c2))
        tcf_idx = _FACE_ORDER.index(side_after)
        utf_idx = _FACE_ORDER.index(u_target)
        diff = (utf_idx - tcf_idx) % 4

        if diff == 1 and len(found_right) >= 3:
            continue
        if diff == 3 and len(found_left) >= 3:
            continue
        if diff not in (1, 3):
            continue

        direction = "RIGHT" if diff == 1 else "LEFT"

        # Get the faces involved
        front_face = side_after
        if direction == "RIGHT":
            adj_face = _FACE_ORDER[(_FACE_ORDER.index(front_face) + 1) % 4]
        else:
            adj_face = _FACE_ORDER[(_FACE_ORDER.index(front_face) - 1) % 4]

        edge_positions = MIDDLE_EDGES[edge_name]
        target_colors = MIDDLE_EDGE_TARGETS[edge_name]

        # Build move set
        move_faces = ["U", front_face, adj_face]
        move_set = []
        for f in move_faces:
            move_set.extend([f, f + "'", f + "2"])

        print(f"\nSearching {direction} insert for {edge_name} ({c1}/{c2}) via {front_face},{adj_face}...")
        print(f"  Edge at U above {front_face}, U-color={_edge_color_on_face(_find_edge(test_state, c1, c2), 'U')}")

        best = None
        for length in range(4, 10):
            for combo in product(move_set, repeat=length):
                skip = False
                for i in range(len(combo) - 1):
                    if combo[i][0] == combo[i+1][0]:
                        skip = True
                        break
                if skip:
                    continue

                alg_str = " ".join(combo)
                try:
                    test, _ = apply_algorithm(test_state, alg_str)
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

                # Also check other solved middle edges are preserved
                other_ok = True
                for other_edge in ["FR", "FL", "BR", "BL"]:
                    if other_edge == edge_name:
                        continue
                    if _is_middle_edge_solved(state, other_edge):
                        if not _is_middle_edge_solved(test, other_edge):
                            other_ok = False
                            break
                if not other_ok:
                    continue

                best = alg_str
                break  # Found shortest

            if best:
                break

        if best:
            print(f"  FOUND: {best}")
            if direction == "RIGHT":
                found_right.append((front_face, adj_face, best, edge_name))
            else:
                found_left.append((front_face, adj_face, best, edge_name))
        else:
            print(f"  NOT FOUND (searched up to length 9)")

        if len(found_right) >= 3 and len(found_left) >= 3:
            break

    if len(found_right) >= 3 and len(found_left) >= 3:
        break

print(f"\n{'='*60}")
print(f"RESULTS:")
print(f"{'='*60}")
print(f"\nRIGHT inserts found: {len(found_right)}")
for front, adj, alg, edge in found_right:
    print(f"  {front}->{adj} ({edge}): {alg}")
print(f"\nLEFT inserts found: {len(found_left)}")
for front, adj, alg, edge in found_left:
    print(f"  {front}->{adj} ({edge}): {alg}")

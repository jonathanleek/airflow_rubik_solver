"""Find ALL middle layer algorithms for all 4 slots, both directions, and ejects."""
import sys, copy
sys.path.insert(0, ".")

from itertools import product
from include.rubik.cube import apply_move, apply_algorithm, get_solved_state, generate_scramble
from include.rubik.solver import (
    is_cross_solved, solve_cross_step,
    is_white_corners_solved, solve_white_corners_step,
    _is_middle_edge_solved, _find_edge, _gs, _edge_layer,
    MIDDLE_EDGES, MIDDLE_EDGE_TARGETS, _FACE_ORDER,
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

def search_alg(state, target_edge, move_set, max_len=9):
    """Search for an algorithm that solves target_edge while preserving D layer."""
    edge_positions = MIDDLE_EDGES[target_edge]
    target_colors = MIDDLE_EDGE_TARGETS[target_edge]

    for length in range(4, max_len + 1):
        for combo in product(move_set, repeat=length):
            skip = False
            for i in range(len(combo) - 1):
                if combo[i][0] == combo[i + 1][0]:
                    skip = True
                    break
            if skip:
                continue

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
            return alg_str
    return None


# For each slot: find both RIGHT and LEFT insert algorithms
# RIGHT: edge above front face, U-color matches the CW-neighbor center
# LEFT: edge above front face, U-color matches the CCW-neighbor center
#
# Slot FR: front=F, right=R, left=L
# Slot FL: front=F is to the RIGHT of L. Actually:
#   FL slot is between F and L
#   RIGHT insert = edge above L, insert to the right (=F direction)
#   LEFT insert = edge above F, insert to the left (=L direction)
#
# Let me think about this differently:
# For each slot XY (between face X and face Y, where Y is CW from X):
#   RIGHT insert: edge is above X, U-color matches Y center -> insert into XY
#   LEFT insert: edge is above Y, U-color matches X center -> insert into XY
#
# Slots and their faces (first face, CW neighbor):
# FR: F, R
# BR: R, B  (R is CW from... wait)
#
# _FACE_ORDER = ["F", "R", "B", "L"]  (CW from above)
# FR: between F and R (R is CW from F)
# BR: between R and B (B is CW from R)  - wait, but BR in MIDDLE_EDGES is (B[3], R[5])
# BL: between B and L (L is CW from B)
# FL: between F and L (F is CW from L)
#
# For RIGHT insert into FR:
#   Edge above F face, U-sticker color = R (matches R center)
#   Faces used: U, F, R
#
# For LEFT insert into FR:
#   Edge above R face, U-sticker color = G (matches F center)
#   Faces used: U, R, F

# First, build all 8 test states
import random
random.seed(42)

# The approach: for each of the 4 slots, we need the slot's edge in the U layer
# with both possible orientations. We'll construct states by solving cross+corners
# on random scrambles and finding ones where the target edge is in U with the right orientation.

def get_move_set(f1, f2):
    moves = []
    for f in ["U", f1, f2]:
        moves.extend([f, f + "'", f + "2"])
    return moves

# All 8 algorithm cases
# (slot_name, front_face_for_right, adj_face_for_right, description)
cases = [
    # FR slot
    ("FR", "F", "R", "RIGHT", "G", "R"),  # edge above F, G on F-side, R on U -> insert right to R
    ("FR", "R", "F", "LEFT", "R", "G"),   # edge above R, R on R-side, G on U -> insert left to F
    # FL slot (between F and L, L is CCW from F)
    ("FL", "L", "F", "RIGHT", "O", "G"),  # edge above L, O on L-side, G on U -> insert right to F
    ("FL", "F", "L", "LEFT", "G", "O"),   # edge above F, G on F-side, O on U -> insert left to L
    # BR slot (between B and R)
    ("BR", "R", "B", "RIGHT", "R", "B"),  # edge above R, R on R-side, B on U -> insert right to B
    ("BR", "B", "R", "LEFT", "B", "R"),   # edge above B, B on B-side, R on U -> insert left to R
    # BL slot (between B and L)
    ("BL", "B", "L", "RIGHT", "B", "O"),  # edge above B, B on B-side, O on U -> insert right to L
    ("BL", "L", "B", "LEFT", "O", "B"),   # edge above L, O on L-side, B on U -> insert left to B
]

results = {}

for slot, front, adj, direction, side_c, u_c in cases:
    key = f"{slot}_{direction}"
    print(f"\nSearching {key}: edge above {front}, {side_c} on {front}-side, {u_c} on U...")

    c1, c2 = MIDDLE_EDGE_TARGETS[slot]

    # Find a state where this edge is in U above front_face with the right orientation
    found_state = None
    for attempt in range(200):
        scramble = generate_scramble(20)
        state = get_solved_state()
        state, _ = apply_algorithm(state, " ".join(scramble))
        state, ok1 = solve_phase(state, is_cross_solved, solve_cross_step)
        if not ok1:
            continue
        state, ok2 = solve_phase(state, is_white_corners_solved, solve_white_corners_step)
        if not ok2 or not d_layer_ok(state):
            continue

        loc = _find_edge(state, c1, c2)
        if not loc or _edge_layer(loc) != "U":
            continue

        # Try U rotations to position above front_face
        for u in ["", "U", "U'", "U2"]:
            test = copy.deepcopy(state)
            if u:
                test, _ = apply_algorithm(test, u)

            # Check if edge is at the right position
            # Edge above front_face: the side-face sticker should be on front_face
            side_faces_map = {"F": ("U", 7, "F", 1), "R": ("U", 5, "R", 1),
                              "B": ("U", 1, "B", 1), "L": ("U", 3, "L", 1)}
            u_idx, u_pos, f_face, f_pos = side_faces_map[front][0], side_faces_map[front][1], side_faces_map[front][2], side_faces_map[front][3]

            u_val = _gs(test, "U", u_pos)
            f_val = _gs(test, f_face, f_pos)

            if f_val == side_c and u_val == u_c:
                found_state = test
                break

        if found_state:
            break

    if found_state is None:
        print(f"  Could not find test state!")
        continue

    print(f"  Found test state. Searching...")
    move_set = get_move_set(front, adj)
    alg = search_alg(found_state, slot, move_set, max_len=8)

    if alg:
        print(f"  FOUND: {alg}")
        results[key] = alg
    else:
        print(f"  Not found with {front},{adj}. Trying extended set...")
        move_set_ext = get_move_set(front, adj) + [front + "2", adj + "2"]
        alg = search_alg(found_state, slot, list(set(move_set_ext)), max_len=9)
        if alg:
            print(f"  FOUND (extended): {alg}")
            results[key] = alg
        else:
            print(f"  NOT FOUND!")

# Also find EJECT algorithms (move a wrong edge from middle layer to U)
print(f"\n{'='*60}")
print("Searching EJECT algorithms...")
print(f"{'='*60}")

for slot in ["FR", "FL", "BR", "BL"]:
    print(f"\nEject from {slot}:")
    # Need a state where slot has a wrong edge
    for attempt in range(200):
        scramble = generate_scramble(20)
        state = get_solved_state()
        state, _ = apply_algorithm(state, " ".join(scramble))
        state, ok1 = solve_phase(state, is_cross_solved, solve_cross_step)
        if not ok1:
            continue
        state, ok2 = solve_phase(state, is_white_corners_solved, solve_white_corners_step)
        if not ok2 or not d_layer_ok(state):
            continue
        # Check slot has wrong edge
        if _is_middle_edge_solved(state, slot):
            continue

        c1, c2 = MIDDLE_EDGE_TARGETS[slot]
        loc = _find_edge(state, c1, c2)
        if loc and _edge_layer(loc) == "M":
            # Edge is in middle layer (might be in this slot or another)
            # We want a case where the slot has a WRONG edge that we need to eject
            edge_pos = MIDDLE_EDGES[slot]
            actual_c1 = _gs(state, edge_pos[0][0], edge_pos[0][1])
            actual_c2 = _gs(state, edge_pos[1][0], edge_pos[1][1])
            if actual_c1 == "Y" or actual_c2 == "Y":
                continue  # yellow edge, skip

            # Find an algorithm that ejects this edge to U layer
            face1, face2 = edge_pos[0][0], edge_pos[1][0]
            move_set = get_move_set(face1, face2)

            for length in range(4, 9):
                found_eject = None
                for combo in product(move_set, repeat=length):
                    skip = False
                    for i in range(len(combo) - 1):
                        if combo[i][0] == combo[i + 1][0]:
                            skip = True
                            break
                    if skip:
                        continue

                    alg_str = " ".join(combo)
                    try:
                        test, _ = apply_algorithm(state, alg_str)
                    except:
                        continue

                    # Check that the edge that was at slot is now in U layer
                    if _gs(test, edge_pos[0][0], edge_pos[0][1]) == actual_c1:
                        continue  # Still there
                    # Check D layer preserved
                    if not d_layer_ok(test):
                        continue
                    # Check the ejected colors are in U layer
                    loc2 = _find_edge(test, actual_c1, actual_c2)
                    if loc2 and _edge_layer(loc2) == "U":
                        found_eject = alg_str
                        break

                if found_eject:
                    break

            if found_eject:
                print(f"  {slot} ({face1},{face2}): {found_eject}")
                results[f"{slot}_EJECT"] = found_eject
                break

print(f"\n{'='*60}")
print("ALL RESULTS:")
print(f"{'='*60}")
for key in sorted(results.keys()):
    print(f"  {key:20s}: {results[key]}")

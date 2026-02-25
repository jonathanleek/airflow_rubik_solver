"""Find correct middle layer algorithms using a realistic post-corners state."""
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

def d_layer_intact(state):
    """Check full D layer: cross + corners + adjacent stickers."""
    # D face all white
    if not all(state["D"][i] == "W" for i in range(9)):
        return False
    # Bottom row of each side face
    targets = {"F": "G", "R": "R", "B": "B", "L": "O"}
    for face, color in targets.items():
        for idx in [6, 7, 8]:
            if state[face][idx] != color:
                return False
    return True

# Get a realistic post-corners state
import random
random.seed(123)
for attempt in range(20):
    scramble = generate_scramble(20)
    state = get_solved_state()
    state, _ = apply_algorithm(state, " ".join(scramble))
    state, ok1 = solve_phase(state, is_cross_solved, solve_cross_step)
    if not ok1:
        continue
    state, ok2 = solve_phase(state, is_white_corners_solved, solve_white_corners_step)
    if not ok2:
        continue
    if not d_layer_intact(state):
        continue
    if is_middle_layer_solved(state):
        continue
    print(f"Attempt {attempt}: Found valid post-corners state")
    print(f"Scramble: {' '.join(scramble)}")
    print(f"D layer intact: {d_layer_intact(state)}")

    # Show which middle edges need solving
    for edge_name in ["FR", "FL", "BR", "BL"]:
        solved = _is_middle_edge_solved(state, edge_name)
        targets = MIDDLE_EDGE_TARGETS[edge_name]
        loc = _find_edge(state, targets[0], targets[1])
        if loc:
            (p1,s1),(p2,s2) = loc
            layer = _edge_layer(loc)
            print(f"  {edge_name}: {'SOLVED' if solved else 'UNSOLVED'} at {p1[0]}[{p1[1]}]={s1}, {p2[0]}[{p2[1]}]={s2} (layer={layer})")

    # Now brute-force search for the right algorithm
    # Find the first unsolved middle edge that's in U layer
    target_edge = None
    for edge_name in ["FR", "FL", "BR", "BL"]:
        if _is_middle_edge_solved(state, edge_name):
            continue
        targets = MIDDLE_EDGE_TARGETS[edge_name]
        loc = _find_edge(state, targets[0], targets[1])
        if loc and _edge_layer(loc) == "U":
            target_edge = edge_name
            break

    if target_edge is None:
        # Try to find one in middle layer (wrong position)
        for edge_name in ["FR", "FL", "BR", "BL"]:
            if not _is_middle_edge_solved(state, edge_name):
                target_edge = edge_name
                break

    if target_edge is None:
        print("  No target edge found")
        continue

    targets = MIDDLE_EDGE_TARGETS[target_edge]
    c1, c2 = targets
    loc = _find_edge(state, c1, c2)
    (p1,s1),(p2,s2) = loc
    layer = _edge_layer(loc)
    print(f"\n  Target: {target_edge} ({c1}/{c2}), currently at {p1[0]}[{p1[1]}]={s1}, {p2[0]}[{p2[1]}]={s2} (layer={layer})")

    # If edge is in U layer, position it above the front face first
    if layer == "U":
        side_face = _edge_side_face_in_u(loc)
        side_color = _edge_color_on_face(loc, side_face)
        u_color = _edge_color_on_face(loc, "U")
        print(f"  U color: {u_color}, Side color: {side_color} (on {side_face})")
        print(f"  Target center for side_color: {_COLOR_TO_FACE[side_color]}")

        # Align: rotate U so side sticker matches its center
        target_face = _COLOR_TO_FACE[side_color]
        cur_idx = _FACE_ORDER.index(side_face)
        target_idx = _FACE_ORDER.index(target_face)
        u_rot = (target_idx - cur_idx) % 4

        test_state = state
        if u_rot != 0:
            u_moves = {1: "U", 2: "U2", 3: "U'"}
            test_state, _ = apply_algorithm(state, u_moves[u_rot])
            print(f"  Applied {u_moves[u_rot]} to align")

        # Now edge should be above the target face
        loc2 = _find_edge(test_state, c1, c2)
        (p1b,s1b),(p2b,s2b) = loc2
        print(f"  After align: {p1b[0]}[{p1b[1]}]={s1b}, {p2b[0]}[{p2b[1]}]={s2b}")

        # Now determine: which face is the edge above? And which slot should it go to?
        u_color_after = _edge_color_on_face(loc2, "U")
        u_target = _COLOR_TO_FACE[u_color_after]
        side_face_after = _edge_side_face_in_u(loc2)
        tcf_idx = _FACE_ORDER.index(side_face_after)
        utf_idx = _FACE_ORDER.index(u_target)
        diff = (utf_idx - tcf_idx) % 4
        direction = "RIGHT" if diff == 1 else ("LEFT" if diff == 3 else f"UNKNOWN({diff})")
        print(f"  Insert direction: {direction} (u_color={u_color_after} -> {u_target}, side_face={side_face_after})")

        # Brute force: find algorithm that inserts this edge
        # Use moves involving the side face, its neighbor, and U
        # For a "right" insert from F face, we use U, R, F
        # The relevant faces depend on the target face
        front = side_face_after
        if direction == "RIGHT":
            right = _FACE_ORDER[(_FACE_ORDER.index(front) + 1) % 4]
        else:
            right = _FACE_ORDER[(_FACE_ORDER.index(front) - 1) % 4]

        print(f"  Search faces: U, {front}, {right}")

        # Build move set for these faces
        moves_for_search = []
        for f in ["U", front, right]:
            moves_for_search.extend([f, f + "'", f + "2"])

        print(f"  Move set: {moves_for_search}")

        # Determine target stickers
        edge_positions = MIDDLE_EDGES[target_edge]
        target_colors = MIDDLE_EDGE_TARGETS[target_edge]

        print(f"  Target: {edge_positions[0][0]}[{edge_positions[0][1]}]={target_colors[0]}, {edge_positions[1][0]}[{edge_positions[1][1]}]={target_colors[1]}")

        found = []
        for length in range(4, 10):
            for combo in product(moves_for_search, repeat=length):
                # Skip consecutive same-face moves
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

                # Check if target edge is solved
                ok = all(
                    _gs(test, face, idx) == target_colors[i]
                    for i, (face, idx) in enumerate(edge_positions)
                )
                if not ok:
                    continue

                # Check D layer preserved
                if not d_layer_intact(test):
                    continue

                found.append(alg_str)
                if len(found) <= 5:
                    print(f"  FOUND ({length} moves): {alg_str}")

            if found:
                print(f"  Total {len(found)} solutions of length {length}")
                break

        if not found:
            print(f"  NO SOLUTION FOUND!")

    break  # Just test first valid state

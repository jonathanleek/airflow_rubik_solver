"""Test script for Rubik's cube move correctness."""

import copy
from include.rubik.cube import (
    get_solved_state,
    apply_move,
    is_solved,
    MOVE_PERMS,
    compose_perms,
    _state_to_flat,
    _flat_to_state,
    _make_identity,
)
from include.rubik.constants import COLORS, FACES, SOLVED_STATE


def state_equal(s1, s2):
    """Check if two cube states are identical."""
    for face in FACES:
        if s1[face] != s2[face]:
            return False
    return True


def test_m4_identity():
    """Test that every base move applied 4 times returns to the solved state (M^4 = I)."""
    print("=" * 60)
    print("TEST 1: M^4 = I (every move applied 4 times returns identity)")
    print("=" * 60)
    base_moves = ["R", "L", "U", "D", "F", "B"]
    all_pass = True
    for move in base_moves:
        state = get_solved_state()
        for i in range(4):
            state = apply_move(state, move)
        passed = is_solved(state)
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
            # Show which faces differ
            solved = get_solved_state()
            diffs = []
            for face in FACES:
                if state[face] != solved[face]:
                    diffs.append(f"  {face}: got {state[face]}, expected {solved[face]}")
            print(f"  {move}^4 = I: {status}")
            for d in diffs:
                print(d)
        else:
            print(f"  {move}^4 = I: {status}")
    print(f"\nOverall: {'ALL PASSED' if all_pass else 'SOME FAILED'}\n")


def test_m_mprime_identity():
    """Test that M * M' = I for all 6 base moves."""
    print("=" * 60)
    print("TEST 2: M * M' = I (move then inverse returns identity)")
    print("=" * 60)
    base_moves = ["R", "L", "U", "D", "F", "B"]
    all_pass = True
    for move in base_moves:
        state = get_solved_state()
        state = apply_move(state, move)
        state = apply_move(state, move + "'")
        passed = is_solved(state)
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
            solved = get_solved_state()
            diffs = []
            for face in FACES:
                if state[face] != solved[face]:
                    diffs.append(f"  {face}: got {state[face]}, expected {solved[face]}")
            print(f"  {move} * {move}' = I: {status}")
            for d in diffs:
                print(d)
        else:
            print(f"  {move} * {move}' = I: {status}")
    print(f"\nOverall: {'ALL PASSED' if all_pass else 'SOME FAILED'}\n")


def test_r_move_f2_to_u8():
    """Test physical property: R move on solved cube should move F[2] (green) to U[8]."""
    print("=" * 60)
    print("TEST 3: R move - F[2] sticker should go to U[8]")
    print("=" * 60)
    print("  Physical Rubik's cube: R move rotates right face CW (looking at it).")
    print("  F[2] (top-right of Front face) is green on a solved cube.")
    print("  After R, that green sticker should move to U[8] (bottom-right of Up face).")
    print()

    solved = get_solved_state()
    print(f"  Before R: F[2] = {solved['F'][2]}, U[8] = {solved['U'][8]}")

    state = apply_move(solved, "R")
    print(f"  After  R: F[2] = {state['F'][2]}, U[8] = {state['U'][8]}")

    expected_u8 = "G"  # green from F[2]
    actual_u8 = state["U"][8]
    passed = actual_u8 == expected_u8
    print(f"\n  U[8] after R: expected '{expected_u8}' (green from F[2]), got '{actual_u8}'")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")

    # Also show what moved where for the right column
    print("\n  Full right-column trace after R:")
    print(f"    U[2]={solved['U'][2]} -> after R: U[2]={state['U'][2]}  (was {solved['U'][2]}, should become B sticker from B[6])")
    print(f"    U[5]={solved['U'][5]} -> after R: U[5]={state['U'][5]}")
    print(f"    U[8]={solved['U'][8]} -> after R: U[8]={state['U'][8]}  (should be G from F[2])")
    print(f"    F[2]={solved['F'][2]} -> after R: F[2]={state['F'][2]}  (should be W from D[2])")
    print(f"    F[5]={solved['F'][5]} -> after R: F[5]={state['F'][5]}")
    print(f"    F[8]={solved['F'][8]} -> after R: F[8]={state['F'][8]}")
    print(f"    D[2]={solved['D'][2]} -> after R: D[2]={state['D'][2]}")
    print(f"    D[5]={solved['D'][5]} -> after R: D[5]={state['D'][5]}")
    print(f"    D[8]={solved['D'][8]} -> after R: D[8]={state['D'][8]}")
    print()


def test_u_move_front_to_right():
    """Test: U move on solved cube should move F[0],F[1],F[2] to R[0],R[1],R[2]."""
    print("=" * 60)
    print("TEST 4: U move - F top row should go to R top row")
    print("=" * 60)
    print("  Physical Rubik's cube: U move rotates top face CW (looking from above).")
    print("  F[0],F[1],F[2] (green) should move to R[0],R[1],R[2].")
    print()

    solved = get_solved_state()
    state = apply_move(solved, "U")

    f_top_before = [solved["F"][i] for i in [0, 1, 2]]
    r_top_after = [state["R"][i] for i in [0, 1, 2]]

    print(f"  Before U: F[0,1,2] = {f_top_before}")
    print(f"  After  U: R[0,1,2] = {r_top_after}")

    expected = ["G", "G", "G"]  # green from front face
    passed = r_top_after == expected
    print(f"\n  R[0,1,2] after U: expected {expected}, got {r_top_after}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")

    # Show all 4 face top-row movements
    print("\n  Full top-row cycle after U:")
    print(f"    F[0,1,2] was {[solved['F'][i] for i in [0,1,2]]} -> after U: {[state['F'][i] for i in [0,1,2]]}")
    print(f"    R[0,1,2] was {[solved['R'][i] for i in [0,1,2]]} -> after U: {[state['R'][i] for i in [0,1,2]]}")
    print(f"    B[0,1,2] was {[solved['B'][i] for i in [0,1,2]]} -> after U: {[state['B'][i] for i in [0,1,2]]}")
    print(f"    L[0,1,2] was {[solved['L'][i] for i in [0,1,2]]} -> after U: {[state['L'][i] for i in [0,1,2]]}")
    print()


def test_f_move_u_bottom_to_r_left():
    """Test: F move on solved should move U[6],U[7],U[8] to R[0],R[3],R[6]."""
    print("=" * 60)
    print("TEST 5: F move - U[6,7,8] should go to R[0,3,6]")
    print("=" * 60)
    print("  Physical Rubik's cube: F move rotates front face CW (looking at it).")
    print("  U[6],U[7],U[8] (yellow) should move to R[0],R[3],R[6].")
    print()

    solved = get_solved_state()
    state = apply_move(solved, "F")

    u_bottom_before = [solved["U"][i] for i in [6, 7, 8]]
    r_left_after = [state["R"][i] for i in [0, 3, 6]]

    print(f"  Before F: U[6,7,8] = {u_bottom_before}")
    print(f"  After  F: R[0,3,6] = {r_left_after}")

    expected = ["Y", "Y", "Y"]  # yellow from U face
    passed = r_left_after == expected
    print(f"\n  R[0,3,6] after F: expected {expected}, got {r_left_after}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")

    # Show what happens to U bottom row and R left column fully
    print("\n  Detailed trace:")
    print(f"    U[6]={solved['U'][6]} -> R[0]: {state['R'][0]}")
    print(f"    U[7]={solved['U'][7]} -> R[3]: {state['R'][3]}")
    print(f"    U[8]={solved['U'][8]} -> R[6]: {state['R'][6]}")
    print(f"    R[0]={solved['R'][0]} -> D[2]: {state['D'][2]}")
    print(f"    R[3]={solved['R'][3]} -> D[1]: {state['D'][1]}")
    print(f"    R[6]={solved['R'][6]} -> D[0]: {state['D'][0]}")
    print(f"    D[0]={solved['D'][0]} -> L[2]: {state['L'][2]}")
    print(f"    D[1]={solved['D'][1]} -> L[5]: {state['L'][5]}")
    print(f"    D[2]={solved['D'][2]} -> L[8]: {state['L'][8]}")
    print(f"    L[2]={solved['L'][2]} -> U[8]: {state['U'][8]}")
    print(f"    L[5]={solved['L'][5]} -> U[7]: {state['U'][7]}")
    print(f"    L[8]={solved['L'][8]} -> U[6]: {state['U'][6]}")
    print()


def test_u_face_sticker_cycle():
    """Print the face sticker cycle for U move on the U face itself."""
    print("=" * 60)
    print("TEST 6: U move face sticker cycle (U face non-center stickers)")
    print("=" * 60)
    print("  Sticker layout:")
    print("    0 | 1 | 2")
    print("    ---------")
    print("    3 | 4 | 5")
    print("    ---------")
    print("    6 | 7 | 8")
    print()

    # We look at the permutation directly
    perm = MOVE_PERMS["U"]
    u_base = FACES.index("U") * 9  # = 0

    non_center = [0, 1, 2, 3, 5, 6, 7, 8]

    print("  U face sticker cycle under U move:")
    print("  (Where does each U sticker position get its value from?)")
    print()

    for pos in non_center:
        flat_idx = u_base + pos
        source_flat = perm[flat_idx]
        source_face = FACES[source_flat // 9]
        source_pos = source_flat % 9
        print(f"    U[{pos}] <- {source_face}[{source_pos}]  (i.e., position {flat_idx} gets value from position {source_flat})")

    print()

    # Also show it as a visual cycle
    print("  Tracing cycles on U face:")
    visited = set()
    for start in non_center:
        if start in visited:
            continue
        cycle = []
        current = start
        while current not in visited:
            visited.add(current)
            cycle.append(current)
            # Where does U[current] come from? perm[u_base + current] gives the source
            # But to trace forward (where does U[current] GO?), we need inverse
            # Forward: after the move, the value at U[current] goes to position X where perm[X] = u_base+current
            # Let's trace using the permutation: after move, new[i] = old[perm[i]]
            # So new[u_base+?] = old[u_base+current] means we need to find ? where perm[u_base+?] = u_base+current
            next_pos = None
            for p in non_center:
                if perm[u_base + p] == u_base + current:
                    next_pos = p
                    break
            if next_pos is None or next_pos in visited:
                break
            current = next_pos
        if len(cycle) > 1:
            cycle_str = " -> ".join(f"U[{c}]" for c in cycle)
            print(f"    Cycle: {cycle_str} -> U[{cycle[0]}]")
        elif len(cycle) == 1:
            print(f"    Fixed: U[{cycle[0]}]")

    print()

    # Also show it concretely with colors on a solved cube
    print("  Concrete example on solved cube (U face is all Yellow):")
    solved = get_solved_state()
    state = apply_move(solved, "U")
    print(f"    Before U: U = {solved['U']}")
    print(f"    After  U: U = {state['U']}")
    print("  (U face stickers remain yellow since the face itself rotates, keeping its own colors)")
    print()


if __name__ == "__main__":
    print()
    print("RUBIK'S CUBE MOVE CORRECTNESS TESTS")
    print("=" * 60)
    print(f"Color convention: U={COLORS['U']}(Yellow), D={COLORS['D']}(White), "
          f"F={COLORS['F']}(Green), B={COLORS['B']}(Blue), "
          f"L={COLORS['L']}(Orange), R={COLORS['R']}(Red)")
    print()

    test_m4_identity()
    test_m_mprime_identity()
    test_r_move_f2_to_u8()
    test_u_move_front_to_right()
    test_f_move_u_bottom_to_r_left()
    test_u_face_sticker_cycle()

    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

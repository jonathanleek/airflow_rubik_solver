"""Test script for Rubik's cube solver algorithms.

Tests the permutation behavior of key algorithms used in the solver,
focusing on white corner insertion and middle layer F2L insertion.
"""

import copy
from include.rubik.cube import apply_algorithm, get_solved_state, is_solved
from include.rubik.constants import COLORS, FACES, SOLVED_STATE


def state_summary(state):
    """Return a compact string representation of the cube state."""
    lines = []
    for face in FACES:
        lines.append(f"  {face}: {''.join(state[face])}")
    return "\n".join(lines)


def dfr_stickers(state):
    """Return the DFR corner stickers: (D[2], F[8], R[6])."""
    return (state["D"][2], state["F"][8], state["R"][6])


def fr_stickers(state):
    """Return the FR edge stickers: (F[5], R[3])."""
    return (state["F"][5], state["R"][3])


def changed_stickers(state1, state2):
    """Return list of (face, index, old_color, new_color) for stickers that differ."""
    changes = []
    for face in FACES:
        for i in range(9):
            if state1[face][i] != state2[face][i]:
                changes.append((face, i, state1[face][i], state2[face][i]))
    return changes


def print_changed(state1, state2, label=""):
    """Print which stickers changed between two states."""
    changes = changed_stickers(state1, state2)
    if label:
        print(f"  {label}")
    if not changes:
        print("    No stickers changed (identity).")
        return
    print(f"    {len(changes)} stickers moved:")
    for face, idx, old, new in changes:
        print(f"      {face}[{idx}]: {old} -> {new}")


def d_layer_preserved(state):
    """Check if the entire D layer (D face + bottom row of F,R,B,L) matches solved."""
    solved = SOLVED_STATE
    ok = True
    if state["D"] != solved["D"]:
        ok = False
    for face in ["F", "R", "B", "L"]:
        for i in [6, 7, 8]:
            if state[face][i] != solved[face][i]:
                ok = False
    return ok


def cross_preserved(state):
    """Check if the white cross edges are still solved."""
    solved = SOLVED_STATE
    checks = [
        ("D", 1), ("F", 7),  # DF
        ("D", 5), ("R", 7),  # DR
        ("D", 7), ("B", 7),  # DB
        ("D", 3), ("L", 7),  # DL
    ]
    for face, idx in checks:
        if state[face][idx] != solved[face][idx]:
            return False
    return True


SEPARATOR = "=" * 70


def test_1():
    """Test 1: White corner insertion with R U R' U' (standard sexy move)."""
    print(SEPARATOR)
    print("TEST 1: White corner insertion - 'R U R' U'' (standard sexy move)")
    print(SEPARATOR)

    solved = get_solved_state()
    print(f"\nSolved DFR corner: D[2]={solved['D'][2]}, F[8]={solved['F'][8]}, R[6]={solved['R'][6]}")

    # Apply U to bring DFR corner up to UFR
    setup, _ = apply_algorithm(solved, "U")
    print(f"\nAfter U move (setup):")
    print(f"  DFR corner: D[2]={setup['D'][2]}, F[8]={setup['F'][8]}, R[6]={setup['R'][6]}")
    print(f"  UFR corner: U[8]={setup['U'][8]}, F[2]={setup['F'][2]}, R[0]={setup['R'][0]}")

    # Apply "R U R' U'" repeatedly
    current = copy.deepcopy(setup)
    for rep in range(1, 7):
        current, moves = apply_algorithm(current, "R U R' U'")
        d2, f8, r6 = dfr_stickers(current)
        is_correct = (d2 == "W" and f8 == "G" and r6 == "R")
        print(f"\n  After rep {rep} of R U R' U':")
        print(f"    DFR: D[2]={d2}, F[8]={f8}, R[6]={r6}  {'<-- SOLVED!' if is_correct else ''}")
        print(f"    UFR: U[8]={current['U'][8]}, F[2]={current['F'][2]}, R[0]={current['R'][0]}")
        if is_correct:
            print(f"    Corner correctly inserted after {rep} repetition(s)!")
            print(f"    Cross preserved: {cross_preserved(current)}")
            break
    else:
        print("\n  WARNING: Corner not solved after 6 repetitions!")

    print()


def test_2():
    """Test 2: White corner insertion with R U' R' U (the modified version in solver.py)."""
    print(SEPARATOR)
    print("TEST 2: White corner insertion - 'R U' R' U' (modified version from solver.py)")
    print(SEPARATOR)

    solved = get_solved_state()

    # Apply U to bring DFR corner up to UFR
    setup, _ = apply_algorithm(solved, "U")
    print(f"\nAfter U move (setup):")
    print(f"  DFR corner: D[2]={setup['D'][2]}, F[8]={setup['F'][8]}, R[6]={setup['R'][6]}")
    print(f"  UFR corner: U[8]={setup['U'][8]}, F[2]={setup['F'][2]}, R[0]={setup['R'][0]}")

    # Apply "R U' R' U" repeatedly
    current = copy.deepcopy(setup)
    for rep in range(1, 7):
        current, moves = apply_algorithm(current, "R U' R' U")
        d2, f8, r6 = dfr_stickers(current)
        is_correct = (d2 == "W" and f8 == "G" and r6 == "R")
        print(f"\n  After rep {rep} of R U' R' U:")
        print(f"    DFR: D[2]={d2}, F[8]={f8}, R[6]={r6}  {'<-- SOLVED!' if is_correct else ''}")
        print(f"    UFR: U[8]={current['U'][8]}, F[2]={current['F'][2]}, R[0]={current['R'][0]}")
        if is_correct:
            print(f"    Corner correctly inserted after {rep} repetition(s)!")
            print(f"    Cross preserved: {cross_preserved(current)}")
            break
    else:
        print("\n  WARNING: Corner not solved after 6 repetitions!")

    print()


def test_3():
    """Test 3: Middle layer F2L insert-right for F face - eject and reinsert."""
    print(SEPARATOR)
    print("TEST 3: Middle layer F2L - eject FR edge and try to reinsert")
    print(SEPARATOR)

    solved = get_solved_state()
    print(f"\nSolved FR edge: F[5]={solved['F'][5]}, R[3]={solved['R'][3]}")

    # Eject the FR edge using the eject algorithm from solver.py
    eject_alg = "U R U' R' U' F' U F"
    ejected, _ = apply_algorithm(solved, eject_alg)
    print(f"\nAfter eject '{eject_alg}':")
    print(f"  FR slot: F[5]={ejected['F'][5]}, R[3]={ejected['R'][3]}")

    # Find where G/R edge went (check all U-layer edges)
    u_edges = [
        ("UF", ("U", 7), ("F", 1)),
        ("UR", ("U", 5), ("R", 1)),
        ("UB", ("U", 1), ("B", 1)),
        ("UL", ("U", 3), ("L", 1)),
    ]
    for name, (uf, ui), (sf, si) in u_edges:
        c1 = ejected[uf][ui]
        c2 = ejected[sf][si]
        if {c1, c2} == {"G", "R"}:
            print(f"  G/R edge found at {name}: {uf}[{ui}]={c1}, {sf}[{si}]={c2}")

    # Now try to insert it back with insert-right algorithm
    # First, we need to position the edge: U-face sticker should match
    # the side it needs to go to. Let's find the edge and see where it is.
    print(f"\n  Now applying insert-right: '{eject_alg}' again")
    reinserted, _ = apply_algorithm(ejected, eject_alg)
    f5, r3 = fr_stickers(reinserted)
    print(f"  FR slot after reinsertion: F[5]={f5}, R[3]={r3}")
    print(f"  FR solved: {f5 == 'G' and r3 == 'R'}")
    print(f"  D layer preserved: {d_layer_preserved(reinserted)}")

    print()


def test_4():
    """Test 4: Direct test of insert-right with manual setup."""
    print(SEPARATOR)
    print("TEST 4: Direct insert-right test with R U2 R' setup")
    print(SEPARATOR)

    solved = get_solved_state()

    # Eject FR edge to UB position
    setup_alg = "R U2 R'"
    setup, _ = apply_algorithm(solved, setup_alg)
    print(f"\nAfter setup '{setup_alg}':")
    print(f"  FR slot: F[5]={setup['F'][5]}, R[3]={setup['R'][3]}")

    # Show all U-layer edges
    u_edges = [
        ("UF", "U", 7, "F", 1),
        ("UR", "U", 5, "R", 1),
        ("UB", "U", 1, "B", 1),
        ("UL", "U", 3, "L", 1),
    ]
    print("\n  U-layer edges:")
    for name, uf, ui, sf, si in u_edges:
        print(f"    {name}: {uf}[{ui}]={setup[uf][ui]}, {sf}[{si}]={setup[sf][si]}")

    # Find G/R edge
    gr_pos = None
    for name, uf, ui, sf, si in u_edges:
        if {setup[uf][ui], setup[sf][si]} == {"G", "R"}:
            gr_pos = name
            print(f"\n  G/R edge found at {name}")

    # (a) Position edge above the F face using U rotations
    current = copy.deepcopy(setup)
    all_moves = []

    # We need G on the side face (F[1]) and R on U face, or vice versa
    # For insert-right, we need the side color to match the front center
    # Let's figure out the correct U adjustment
    print("\n  Trying different U rotations before insert-right:")
    for u_adj in ["", "U", "U'", "U2"]:
        test = copy.deepcopy(setup)
        if u_adj:
            test, _ = apply_algorithm(test, u_adj)

        # Check UF edge
        uf_u = test["U"][7]
        uf_f = test["F"][1]
        print(f"    After '{u_adj or 'none'}': UF = U[7]={uf_u}, F[1]={uf_f}")

        # For insert-right on F face, we need F[1] to match F center (G)
        # and U[7] to match R center (R) -- meaning the edge goes right
        if uf_f == "G" and uf_u == "R":
            print(f"    --> This is correct setup for insert-right on F face!")

    # (b) Let's do the right U adjustment and apply insert-right
    # Try each U adjustment + insert
    print("\n  Testing each U adjustment + insert-right algorithm:")
    insert_alg = "U R U' R' U' F' U F"
    for u_adj in ["", "U", "U'", "U2"]:
        test = copy.deepcopy(setup)
        if u_adj:
            test, _ = apply_algorithm(test, u_adj)
        test, _ = apply_algorithm(test, insert_alg)
        f5, r3 = fr_stickers(test)
        fr_ok = (f5 == "G" and r3 == "R")
        d_ok = d_layer_preserved(test)
        cross_ok = cross_preserved(test)
        print(f"    U_adj='{u_adj or 'none'}' + insert: FR=F[5]={f5},R[3]={r3}  FR_ok={fr_ok}  D_ok={d_ok}  cross_ok={cross_ok}")

    print()


def test_5():
    """Test 5: What does 'U R U' R' U' F' U F' actually do to a solved cube?"""
    print(SEPARATOR)
    print("TEST 5: Permutation of 'U R U' R' U' F' U F' on solved cube")
    print(SEPARATOR)

    solved = get_solved_state()
    alg = "U R U' R' U' F' U F"
    result, _ = apply_algorithm(solved, alg)

    print(f"\nAlgorithm: {alg}")
    print(f"Applied to solved cube.\n")
    print_changed(solved, result)

    # Also show the full state of affected faces
    print("\n  Full state of changed faces:")
    changed_faces = set()
    for face in FACES:
        for i in range(9):
            if solved[face][i] != result[face][i]:
                changed_faces.add(face)

    for face in sorted(changed_faces):
        solved_str = "".join(solved[face])
        result_str = "".join(result[face])
        print(f"    {face}: {solved_str} -> {result_str}")

    # Check: is this algorithm an involution (self-inverse)?
    result2, _ = apply_algorithm(result, alg)
    print(f"\n  Applying algorithm twice returns to solved: {is_solved(result2)}")

    # What's the order of this permutation?
    current = copy.deepcopy(solved)
    for n in range(1, 25):
        current, _ = apply_algorithm(current, alg)
        if is_solved(current):
            print(f"  Order of this permutation: {n}")
            break
    else:
        print(f"  Order > 24")

    print()


def test_6():
    """Test 6: What does 'R U R' U'' do to a solved cube?"""
    print(SEPARATOR)
    print("TEST 6: Permutation of 'R U R' U'' (sexy move) on solved cube")
    print(SEPARATOR)

    solved = get_solved_state()
    alg = "R U R' U'"
    result, _ = apply_algorithm(solved, alg)

    print(f"\nAlgorithm: {alg}")
    print(f"Applied to solved cube.\n")
    print_changed(solved, result)

    # Show full state of changed faces
    print("\n  Full state of changed faces:")
    changed_faces = set()
    for face in FACES:
        for i in range(9):
            if solved[face][i] != result[face][i]:
                changed_faces.add(face)

    for face in sorted(changed_faces):
        solved_str = "".join(solved[face])
        result_str = "".join(result[face])
        print(f"    {face}: {solved_str} -> {result_str}")

    # What's the order of this permutation?
    current = copy.deepcopy(solved)
    for n in range(1, 25):
        current, _ = apply_algorithm(current, alg)
        if is_solved(current):
            print(f"\n  Order of this permutation: {n}")
            break
    else:
        print(f"\n  Order > 24")

    # Also test R U' R' U
    print(f"\n  --- Also testing R U' R' U ---")
    alg2 = "R U' R' U"
    result2, _ = apply_algorithm(solved, alg2)
    print(f"\n  Algorithm: {alg2}")
    print_changed(solved, result2)

    current = copy.deepcopy(solved)
    for n in range(1, 25):
        current, _ = apply_algorithm(current, alg2)
        if is_solved(current):
            print(f"\n  Order of R U' R' U: {n}")
            break
    else:
        print(f"\n  Order of R U' R' U > 24")

    print()


if __name__ == "__main__":
    print()
    print("RUBIK'S CUBE SOLVER ALGORITHM TESTS")
    print("=" * 70)
    print(f"Color convention: U=Y(Yellow), D=W(White), F=G(Green), B=B(Blue), L=O(Orange), R=R(Red)")
    print(f"Sticker layout per face:")
    print(f"  0 | 1 | 2")
    print(f"  ---------")
    print(f"  3 | 4 | 5")
    print(f"  ---------")
    print(f"  6 | 7 | 8")
    print()

    test_1()
    test_2()
    test_3()
    test_4()
    test_5()
    test_6()

    print(SEPARATOR)
    print("ALL TESTS COMPLETE")
    print(SEPARATOR)

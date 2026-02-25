#!/usr/bin/env python3
"""Independent reference comparison for Rubik's cube permutation model.

This script builds a completely independent Rubik's cube permutation model
using the well-known SageMath/GAP Rubik's cube group permutations as ground
truth. It translates the SageMath 48-facelet numbering to the project's
54-facelet numbering and compares element-by-element.

Reference source:
  SageMath cubegroup.py - sage.groups.perm_gps.cubegroup
  https://doc.sagemath.org/html/en/reference/groups/sage/groups/perm_gps/cubegroup.html

SageMath facelet numbering (1-indexed, 48 facelets, centers omitted):
                 +----------+
                 | 1   2   3|
                 | 4  top  5|
                 | 6   7   8|
    +------------+----------+-----------+----------+
    | 9  10  11  |17  18  19|25  26  27 |33  34  35|
    |12  left  13|20 front21|28 right 29|36 rear 37|
    |14  15  16  |22  23  24|30  31  32 |38  39  40|
    +------------+----------+-----------+----------+
                 |41  42  43|
                 |44 bot  45|
                 |46  47  48|
                 +----------+

SageMath move definitions (standard cycle notation, a->b->c->d->a):
  R = (3,38,43,19)(5,36,45,21)(8,33,48,24)(25,27,32,30)(26,29,31,28)
  L = (1,17,41,40)(4,20,44,37)(6,22,46,35)(9,11,16,14)(10,13,15,12)
  U = (1,3,8,6)(2,5,7,4)(9,33,25,17)(10,34,26,18)(11,35,27,19)
  D = (14,22,30,38)(15,23,31,39)(16,24,32,40)(41,43,48,46)(42,45,47,44)
  F = (6,25,43,16)(7,28,42,13)(8,30,41,11)(17,19,24,22)(18,21,23,20)
  B = (1,14,48,27)(2,12,47,29)(3,9,46,32)(33,35,40,38)(34,37,39,36)

Project conventions:
  FACES = ['U', 'D', 'F', 'B', 'L', 'R']
  Each face 0-8 in grid:  0|1|2 / 3|4|5 / 6|7|8
  Viewed from front-above perspective.
  Flat index = FACES.index(face) * 9 + pos
  Pull convention: new[i] = old[perm[i]]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# PART 1: Build SageMath-verified reference model
# ============================================================================

FACES = ['U', 'D', 'F', 'B', 'L', 'R']
COLORS = {'U': 'Y', 'D': 'W', 'F': 'G', 'B': 'B', 'L': 'O', 'R': 'R'}


def idx(face, pos):
    """Convert (face, position) to flat index 0-53."""
    return FACES.index(face) * 9 + pos


def face_pos(flat_idx):
    """Convert flat index to (face, position)."""
    return FACES[flat_idx // 9], flat_idx % 9


def sticker_label(flat_idx):
    """Human-readable label for a flat index."""
    f, p = face_pos(flat_idx)
    return f"{f}[{p}]"


# ---------------------------------------------------------------------------
# SageMath to project index mapping
# ---------------------------------------------------------------------------
# SageMath uses 1-indexed, 48 facelets (no centers).
# Project uses 0-indexed, 54 facelets (with centers at position 4 per face).
# Mapping derived by cross-referencing corner positions between the SageMath
# unfolded diagram and the project's corner definitions from constants.py:
#   UFR: (U[8], F[2], R[0])   UFL: (U[6], F[0], L[2])
#   UBR: (U[2], B[0], R[2])   UBL: (U[0], B[2], L[0])
#   DFR: (D[2], F[8], R[6])   DFL: (D[0], F[6], L[8])
#   DBR: (D[8], B[6], R[8])   DBL: (D[6], B[8], L[6])

SAGE_TO_OURS = {}

# U face: sage 1-8 (no center) -> our U[0]-U[8] (skip U[4]=center)
for sage_i, our_pos in [(1, 0), (2, 1), (3, 2), (4, 3), (5, 5), (6, 6), (7, 7), (8, 8)]:
    SAGE_TO_OURS[sage_i] = idx('U', our_pos)

# L face: sage 9-16 -> our L[0]-L[8]
for sage_i, our_pos in [(9, 0), (10, 1), (11, 2), (12, 3), (13, 5), (14, 6), (15, 7), (16, 8)]:
    SAGE_TO_OURS[sage_i] = idx('L', our_pos)

# F face: sage 17-24 -> our F[0]-F[8]
for sage_i, our_pos in [(17, 0), (18, 1), (19, 2), (20, 3), (21, 5), (22, 6), (23, 7), (24, 8)]:
    SAGE_TO_OURS[sage_i] = idx('F', our_pos)

# R face: sage 25-32 -> our R[0]-R[8]
for sage_i, our_pos in [(25, 0), (26, 1), (27, 2), (28, 3), (29, 5), (30, 6), (31, 7), (32, 8)]:
    SAGE_TO_OURS[sage_i] = idx('R', our_pos)

# B face: sage 33-40 -> our B[0]-B[8]
for sage_i, our_pos in [(33, 0), (34, 1), (35, 2), (36, 3), (37, 5), (38, 6), (39, 7), (40, 8)]:
    SAGE_TO_OURS[sage_i] = idx('B', our_pos)

# D face: sage 41-48 -> our D[0]-D[8]
for sage_i, our_pos in [(41, 0), (42, 1), (43, 2), (44, 3), (45, 5), (46, 6), (47, 7), (48, 8)]:
    SAGE_TO_OURS[sage_i] = idx('D', our_pos)


# SageMath move definitions (each move = list of cycles in sage numbering)
SAGE_MOVES = {
    'R': [(3, 38, 43, 19), (5, 36, 45, 21), (8, 33, 48, 24), (25, 27, 32, 30), (26, 29, 31, 28)],
    'L': [(1, 17, 41, 40), (4, 20, 44, 37), (6, 22, 46, 35), (9, 11, 16, 14), (10, 13, 15, 12)],
    'U': [(1, 3, 8, 6), (2, 5, 7, 4), (9, 33, 25, 17), (10, 34, 26, 18), (11, 35, 27, 19)],
    'D': [(14, 22, 30, 38), (15, 23, 31, 39), (16, 24, 32, 40), (41, 43, 48, 46), (42, 45, 47, 44)],
    'F': [(6, 25, 43, 16), (7, 28, 42, 13), (8, 30, 41, 11), (17, 19, 24, 22), (18, 21, 23, 20)],
    'B': [(1, 14, 48, 27), (2, 12, 47, 29), (3, 9, 46, 32), (33, 35, 40, 38), (34, 37, 39, 36)],
}


def build_perm_from_sage(sage_cycles):
    """Build a 54-element pull-convention permutation from SageMath cycles.

    SageMath cycle (a,b,c,d) means a->b, b->c, c->d, d->a.
    In pull convention: perm[dest] = src, meaning position dest gets its
    value from position src.

    All cycles within a single move are disjoint, so they can be applied
    independently to the identity permutation.
    """
    perm = list(range(54))  # Start with identity
    for sage_cycle in sage_cycles:
        our_cycle = [SAGE_TO_OURS[s] for s in sage_cycle]
        n = len(our_cycle)
        for i in range(n):
            src = our_cycle[i]
            dst = our_cycle[(i + 1) % n]
            perm[dst] = src  # Pull convention: dest pulls from src
    return perm


def compose(p1, p2):
    """Compose two pull-convention permutations: apply p1 first, then p2.

    result[i] = p1[p2[i]]

    This is because:
      After p1: intermediate[i] = old[p1[i]]
      After p2: result[i] = intermediate[p2[i]] = old[p1[p2[i]]]
    """
    return [p1[p2[i]] for i in range(54)]


def build_reference_moves():
    """Build all 18 move permutations from SageMath reference."""
    moves = {}

    # Build the 6 basic CW moves from SageMath data
    for move_name, sage_cycles in SAGE_MOVES.items():
        moves[move_name] = build_perm_from_sage(sage_cycles)

    # Build inverse (CCW) and double moves
    for face in ['R', 'L', 'U', 'D', 'F', 'B']:
        cw = moves[face]
        # Inverse = CW applied 3 times
        ccw = compose(cw, compose(cw, cw))
        moves[face + "'"] = ccw
        # Double = CW applied 2 times
        moves[face + "2"] = compose(cw, cw)

    return moves


# ============================================================================
# PART 2: Compare reference vs project model
# ============================================================================

def compare_moves(ref_moves, proj_moves):
    """Compare reference and project move permutations element by element."""
    total_diffs = 0
    move_results = {}

    for move_name in ['R', 'L', 'U', 'D', 'F', 'B']:
        ref = ref_moves[move_name]
        proj = proj_moves[move_name]

        diffs = []
        for i in range(54):
            if ref[i] != proj[i]:
                diffs.append({
                    'index': i,
                    'dst': sticker_label(i),
                    'ref_src': sticker_label(ref[i]),
                    'proj_src': sticker_label(proj[i]),
                })

        total_diffs += len(diffs)

        # Categorize: face-only vs adjacent-only vs both
        if diffs:
            face_base = FACES.index(move_name) * 9
            face_diffs = [d for d in diffs if face_base <= d['index'] < face_base + 9]
            adj_diffs = [d for d in diffs if not (face_base <= d['index'] < face_base + 9)]
            move_results[move_name] = {
                'diffs': diffs,
                'face_diffs': face_diffs,
                'adj_diffs': adj_diffs,
            }
        else:
            move_results[move_name] = {'diffs': [], 'face_diffs': [], 'adj_diffs': []}

    return total_diffs, move_results


def compute_order(perm, max_iter=1260):
    """Compute the order of a permutation (number of applications to reach identity)."""
    identity = list(range(54))
    p = perm[:]
    for order in range(1, max_iter + 1):
        if p == identity:
            return order
        p = compose(perm, p)
    return None  # Did not reach identity


def get_perm_cycles(perm):
    """Extract cycle decomposition of a permutation."""
    visited = set()
    cycles = []
    for i in range(54):
        if i in visited or perm[i] == i:
            continue
        cycle = []
        j = i
        while j not in visited:
            visited.add(j)
            cycle.append(j)
            j = perm[j]
        if len(cycle) > 1:
            cycles.append(cycle)
    return cycles


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("REFERENCE COMPARISON TEST")
    print("SageMath-verified model vs project MOVE_PERMS")
    print("=" * 70)

    # Import project model
    from include.rubik.cube import MOVE_PERMS as proj_perms

    # Build reference
    ref_moves = build_reference_moves()
    identity = list(range(54))

    # -----------------------------------------------------------------------
    # Verify reference model sanity
    # -----------------------------------------------------------------------
    print("\n--- Reference model sanity checks ---")
    ref_ok = True
    for face in ['R', 'L', 'U', 'D', 'F', 'B']:
        p = ref_moves[face]
        p4 = compose(p, compose(p, compose(p, p)))
        ok = (p4 == identity)
        if not ok:
            ref_ok = False
        mm_inv = compose(ref_moves[face], ref_moves[face + "'"])
        inv_ok = (mm_inv == identity)
        if not inv_ok:
            ref_ok = False
        status = "OK" if (ok and inv_ok) else "FAIL"
        print(f"  {face}^4=I: {'OK' if ok else 'FAIL'},  {face}*{face}'=I: {'OK' if inv_ok else 'FAIL'}")

    if ref_ok:
        print("  All reference sanity checks PASSED.")
    else:
        print("  WARNING: Reference model has sanity check failures!")

    # -----------------------------------------------------------------------
    # Compare basic moves
    # -----------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("BASIC MOVE COMPARISON (6 CW moves)")
    print("=" * 70)

    total_diffs, move_results = compare_moves(ref_moves, proj_perms)

    for move_name in ['R', 'L', 'U', 'D', 'F', 'B']:
        result = move_results[move_name]
        diffs = result['diffs']
        face_diffs = result['face_diffs']
        adj_diffs = result['adj_diffs']

        if not diffs:
            print(f"\n  {move_name} move: CORRECT (0 differences)")
            continue

        print(f"\n  {move_name} move: {len(diffs)} DIFFERENCES")
        print(f"  {'Position':<12} {'Reference (correct)':<25} {'Project (actual)':<25}")
        print(f"  {'-'*12} {'-'*25} {'-'*25}")
        for d in diffs:
            print(f"  {d['dst']:<12} pulls from {d['ref_src']:<15} pulls from {d['proj_src']:<15}")

        # Diagnosis
        if face_diffs and not adj_diffs:
            print(f"\n  DIAGNOSIS: {move_name} FACE ROTATION is WRONG DIRECTION")
            print(f"    Adjacent sticker cycles are correct.")
            print(f"    The {move_name} face stickers rotate CCW instead of CW (or vice versa).")
        elif adj_diffs and not face_diffs:
            print(f"\n  DIAGNOSIS: {move_name} ADJACENT STICKER CYCLES are WRONG DIRECTION")
            print(f"    Face rotation is correct.")
            print(f"    The adjacent stickers cycle in the opposite direction from correct.")
        else:
            print(f"\n  DIAGNOSIS: BOTH face rotation ({len(face_diffs)} diffs) and")
            print(f"    adjacent cycles ({len(adj_diffs)} diffs) are wrong for {move_name}.")

    # -----------------------------------------------------------------------
    # Compare derived moves
    # -----------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("DERIVED MOVE COMPARISON (primes and doubles)")
    print("=" * 70)

    for suffix in ["'", "2"]:
        for face in ['R', 'L', 'U', 'D', 'F', 'B']:
            move_name = face + suffix
            ref = ref_moves[move_name]
            proj = proj_perms[move_name]
            diff_count = sum(1 for i in range(54) if ref[i] != proj[i])
            status = "CORRECT" if diff_count == 0 else f"{diff_count} diffs"
            print(f"  {move_name:<4}: {status}")

    # -----------------------------------------------------------------------
    # T-perm order test
    # -----------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("T-PERM ORDER TEST: R U R' U' R' F R2 U' R' U' R U R' F'")
    print("=" * 70)

    t_perm_alg = "R U R' U' R' F R2 U' R' U' R U R' F'"
    t_perm_moves = t_perm_alg.split()

    # Reference T-perm
    ref_t = identity[:]
    for m in t_perm_moves:
        ref_t = compose(ref_t, ref_moves[m])

    ref_t_order = compute_order(ref_t)
    ref_t_cycles = get_perm_cycles(ref_t)

    print(f"\n  Reference model:")
    print(f"    Order: {ref_t_order} (expected: 2)")
    if ref_t_cycles:
        print(f"    Cycles:")
        for cycle in ref_t_cycles:
            labels = [sticker_label(x) for x in cycle]
            print(f"      ({len(cycle)}-cycle) {' <-> '.join(labels)}")
    else:
        print(f"    No cycles (identity)")

    # Project T-perm
    proj_t = identity[:]
    for m in t_perm_moves:
        proj_t = compose(proj_t, proj_perms[m])

    proj_t_order = compute_order(proj_t)
    proj_t_cycles = get_perm_cycles(proj_t)

    print(f"\n  Project model:")
    print(f"    Order: {proj_t_order} (expected: 2)")
    if proj_t_cycles:
        print(f"    Cycles ({len(proj_t_cycles)} total):")
        for cycle in proj_t_cycles:
            labels = [sticker_label(x) for x in cycle]
            print(f"      ({len(cycle)}-cycle) {' -> '.join(labels)}")

    if ref_t_order == 2:
        print(f"\n  REFERENCE IS CORRECT: T-perm order = 2")
    if proj_t_order != 2:
        print(f"  PROJECT IS WRONG: T-perm order = {proj_t_order}, should be 2")

    # -----------------------------------------------------------------------
    # Additional algorithm order tests
    # -----------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("ADDITIONAL ALGORITHM ORDER TESTS")
    print("=" * 70)

    test_algs = [
        ("Sexy move (R U R' U')", "R U R' U'", 6),
        ("Sune (R U R' U R U2 R')", "R U R' U R U2 R'", 6),
        ("J-perm", "R U R' F' R U R' U' R' F R2 U' R' U'", 2),
        ("A-perm (a)", "R' F R' B2 R F' R' B2 R2", None),  # Just compare ref vs proj
        ("Y-perm", "F R U' R' U' R U R' F' R U R' U' R' F R F'", 2),
    ]

    for name, alg, expected_order in test_algs:
        moves_list = alg.split()

        ref_p = identity[:]
        for m in moves_list:
            ref_p = compose(ref_p, ref_moves[m])
        ref_ord = compute_order(ref_p)

        proj_p = identity[:]
        for m in moves_list:
            proj_p = compose(proj_p, proj_perms[m])
        proj_ord = compute_order(proj_p)

        expected_str = str(expected_order) if expected_order else "N/A"
        ref_ok = "OK" if (expected_order and ref_ord == expected_order) else str(ref_ord)
        proj_ok = "OK" if (expected_order and proj_ord == expected_order) else str(proj_ord)

        print(f"\n  {name}")
        print(f"    Algorithm: {alg}")
        print(f"    Expected: {expected_str}  |  Reference: {ref_ok}  |  Project: {proj_ok}")
        if ref_ord != proj_ord:
            print(f"    MISMATCH: reference={ref_ord}, project={proj_ord}")

    # -----------------------------------------------------------------------
    # Root cause summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("ROOT CAUSE SUMMARY")
    print("=" * 70)

    buggy_moves = []
    for move_name in ['R', 'L', 'U', 'D', 'F', 'B']:
        result = move_results[move_name]
        if result['diffs']:
            buggy_moves.append(move_name)

    if not buggy_moves:
        print("\n  All basic moves match the reference. No bugs found.")
    else:
        print(f"\n  Buggy moves: {', '.join(buggy_moves)}")
        print(f"  Total sticker-level differences: {total_diffs}")
        print()

        for move_name in buggy_moves:
            result = move_results[move_name]
            face_count = len(result['face_diffs'])
            adj_count = len(result['adj_diffs'])
            print(f"  {move_name} move ({len(result['diffs'])} diffs):")
            if face_count and not adj_count:
                print(f"    - Face rotation: WRONG (reversed direction)")
                print(f"    - Adjacent stickers: correct")
            elif adj_count and not face_count:
                print(f"    - Face rotation: correct")
                print(f"    - Adjacent stickers: WRONG (reversed direction)")
            else:
                print(f"    - Face rotation: WRONG ({face_count} diffs)")
                print(f"    - Adjacent stickers: WRONG ({adj_count} diffs)")

        print()
        print("  In cube.py, the _rotate_face_cw function groups faces as:")
        print('    if face in ("D", "L"):    # pattern A (0->6->8->2)')
        print('    else (U, F, R, B):        # pattern B (0->2->8->6)')
        print()
        print("  CORRECT grouping (verified against SageMath):")
        print("    ALL faces should use pattern B: 0->2->8->6->0, 1->5->7->3->1")
        print("    No face needs the reversed pattern.")
        print()
        print("  Additionally, the adjacent sticker cycles for U and D are reversed:")
        print("    U cycle in code: [F, R, B, L] giving F->R->B->L")
        print("    Correct U cycle: [F, L, B, R] giving F->L, L->B, B->R, R->F")
        print("    (CW from above means Front goes to Left face position)")
        print()
        print("    D cycle in code: [F, L, B, R] giving F->L->B->R")
        print("    Correct D cycle: [F, R, B, L] giving F->R, R->B, B->L, L->F")
        print("    (CW from below = CCW from above)")
        print()
        print("  Specifically, in _build_move_perms():")
        print()
        print("    FIX 1 - _rotate_face_cw: remove special casing.")
        print("      Change: if face in ('D', 'L'): [b+0,b+6,b+8,b+2] ...")
        print("      To:     ALL faces use [b+0,b+2,b+8,b+6], [b+1,b+5,b+7,b+3]")
        print()
        print("    FIX 2 - U adjacent cycles: reverse the direction.")
        print('      Change: [F0,R0,B0,L0] to [F0,L0,B0,R0]  (and same for 1,2)')
        print()
        print("    FIX 3 - D adjacent cycles: reverse the direction.")
        print('      Change: [F6,L6,B6,R6] to [F6,R6,B6,L6]  (and same for 7,8)')


if __name__ == "__main__":
    main()

"""Solver logic for beginner layer-by-layer method (7 phases).

Each phase has:
- is_phase_solved(state): bool
- detect_case(state): str (case name for branching)
- solve_phase(state): (new_state, moves_applied) -- applies one step toward solving
"""

import copy

from include.rubik.cube import apply_algorithm, get_sticker
from include.rubik.constants import (
    COLORS,
    WHITE_CROSS_EDGES,
    WHITE_CROSS_TARGETS,
    WHITE_CORNERS,
    WHITE_CORNER_TARGETS,
    MIDDLE_EDGES,
    MIDDLE_EDGE_TARGETS,
    YELLOW_CROSS_EDGES,
    YELLOW_CORNERS,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _do(state, alg):
    """Apply algorithm string, return (new_state, move_list)."""
    if not alg or not alg.strip():
        return state, []
    return apply_algorithm(state, alg)


def _gs(state, face, idx):
    """Shorthand for get_sticker."""
    return get_sticker(state, face, idx)


# Color-to-face mapping (inverse of COLORS)
_COLOR_TO_FACE = {v: k for k, v in COLORS.items()}

# All 12 edges as ((face1, idx1), (face2, idx2))
ALL_EDGES = [
    # U layer edges
    (("U", 7), ("F", 1)),   # UF
    (("U", 5), ("R", 1)),   # UR
    (("U", 1), ("B", 1)),   # UB
    (("U", 3), ("L", 1)),   # UL
    # Middle layer edges
    (("F", 5), ("R", 3)),   # FR
    (("F", 3), ("L", 5)),   # FL
    (("B", 3), ("R", 5)),   # BR
    (("B", 5), ("L", 3)),   # BL
    # D layer edges
    (("D", 1), ("F", 7)),   # DF
    (("D", 5), ("R", 7)),   # DR
    (("D", 7), ("B", 7)),   # DB
    (("D", 3), ("L", 7)),   # DL
]

ALL_CORNERS = [
    # U layer
    (("U", 8), ("F", 2), ("R", 0)),   # UFR
    (("U", 6), ("F", 0), ("L", 2)),   # UFL
    (("U", 2), ("B", 0), ("R", 2)),   # UBR
    (("U", 0), ("B", 2), ("L", 0)),   # UBL
    # D layer
    (("D", 2), ("F", 8), ("R", 6)),   # DFR
    (("D", 0), ("F", 6), ("L", 8)),   # DFL
    (("D", 8), ("B", 6), ("R", 8)),   # DBR
    (("D", 6), ("B", 8), ("L", 6)),   # DBL
]

# Face order for U-layer rotation: F->R->B->L (clockwise from top)
_FACE_ORDER = ["F", "R", "B", "L"]


def _find_edge(state, c1, c2):
    """Find edge with colors c1,c2. Returns ((pos1,col1),(pos2,col2)) or None."""
    for p1, p2 in ALL_EDGES:
        s1 = _gs(state, p1[0], p1[1])
        s2 = _gs(state, p2[0], p2[1])
        if {s1, s2} == {c1, c2}:
            return ((p1, s1), (p2, s2))
    return None


def _find_corner(state, c1, c2, c3):
    """Find corner with colors c1,c2,c3. Returns ((pos1,col1),(pos2,col2),(pos3,col3)) or None."""
    colors = {c1, c2, c3}
    for p1, p2, p3 in ALL_CORNERS:
        s1 = _gs(state, p1[0], p1[1])
        s2 = _gs(state, p2[0], p2[1])
        s3 = _gs(state, p3[0], p3[1])
        if {s1, s2, s3} == colors:
            return ((p1, s1), (p2, s2), (p3, s3))
    return None


def _u_turns_str(n):
    """Return U-rotation string for n quarter turns (0-3)."""
    n = n % 4
    if n == 0:
        return ""
    if n == 1:
        return "U"
    if n == 2:
        return "U2"
    return "U'"


def _edge_layer(loc):
    """Given _find_edge result, return 'U', 'M', or 'D'."""
    faces = {loc[0][0][0], loc[1][0][0]}
    if "U" in faces:
        return "U"
    if "D" in faces:
        return "D"
    return "M"


def _edge_side_face_in_u(loc):
    """Given an edge in U layer, return the side face (non-U face)."""
    if loc[0][0][0] == "U":
        return loc[1][0][0]
    return loc[0][0][0]


def _edge_color_on_face(loc, face):
    """Get the color of the edge sticker that's on a given face."""
    for pos, col in [loc[0], loc[1]]:
        if pos[0] == face:
            return col
    return None


# ---------------------------------------------------------------------------
# Phase 1: White Cross
# ---------------------------------------------------------------------------
# Strategy: solve edges one at a time. For each unsolved edge:
# 1. If in D layer: use the face2 of the D-slot it's in to bring it to U.
#    (face2 only affects one D-edge position, safe for others.)
# 2. If in middle layer: eject to U with a 3-move sequence.
# 3. In U layer: rotate U to align, then insert.
#    - White on top (U face): position above target, do target_face2.
#    - White on side: use specific safe 4-move algorithm per target face.

# Maps D-slot side face to the face2 move that extracts the edge to U
_D_SLOT_EXTRACT = {
    "F": "F2",  # DF -> UF
    "R": "R2",  # DR -> UR
    "B": "B2",  # DB -> UB
    "L": "L2",  # DL -> UL
}

# Middle-layer eject: maps frozenset of {face1, face2} to eject algorithm
_MID_EJECT_FOR_CROSS = {
    frozenset({"F", "R"}): "R U R'",
    frozenset({"F", "L"}): "L' U' L",
    frozenset({"B", "R"}): "R' U' R",
    frozenset({"B", "L"}): "L U L'",
}

# White-on-side insertion algorithms (safe: preserve all other D-layer cross edges).
# For each target face, when edge is at U with white on the side face and
# the non-white color on U, positioned directly above the target slot.
_CROSS_INSERT_WHITE_ON_SIDE = {
    "F": "U' R' F R",
    "R": "U' B' R B",
    "B": "U' L' B L",
    "L": "U' F' L F",
}


def _is_cross_edge_solved(state, edge_name):
    """Check if a single white cross edge is solved."""
    positions = WHITE_CROSS_EDGES[edge_name]
    target = WHITE_CROSS_TARGETS[edge_name]
    return all(
        _gs(state, face, idx) == target[i]
        for i, (face, idx) in enumerate(positions)
    )


def is_cross_solved(state):
    """Check if the white cross on the D face is solved."""
    return all(_is_cross_edge_solved(state, e) for e in WHITE_CROSS_EDGES)


def solve_cross_step(state):
    """Solve one white cross edge. Returns (new_state, moves_applied)."""
    if is_cross_solved(state):
        return state, []

    edge_order = ["DF", "DR", "DB", "DL"]

    for edge_name in edge_order:
        if _is_cross_edge_solved(state, edge_name):
            continue

        side_color = WHITE_CROSS_TARGETS[edge_name][1]
        target_face = _COLOR_TO_FACE[side_color]
        target_face_idx = _FACE_ORDER.index(target_face)

        loc = _find_edge(state, "W", side_color)
        if loc is None:
            continue

        current = state
        all_moves = []
        layer = _edge_layer(loc)

        # --- Step 1: Get edge to U layer ---
        if layer == "D":
            # Use face2 of the D-slot the edge is currently in.
            # Find which D slot it's in by looking at the side face.
            for pos, col in [loc[0], loc[1]]:
                if pos[0] != "D":
                    d_side_face = pos[0]
                    break
            else:
                # Both on D? Shouldn't happen.
                continue

            extract_alg = _D_SLOT_EXTRACT[d_side_face]
            current, moves = _do(current, extract_alg)
            all_moves.extend(moves)

            # Re-find edge
            loc = _find_edge(current, "W", side_color)
            if loc is None:
                return current, all_moves
            layer = _edge_layer(loc)

        if layer == "M":
            # Eject from middle layer to U
            faces = frozenset(pos[0] for pos, _ in [loc[0], loc[1]])
            eject_alg = _MID_EJECT_FOR_CROSS.get(faces)
            if eject_alg:
                current, moves = _do(current, eject_alg)
                all_moves.extend(moves)

            loc = _find_edge(current, "W", side_color)
            if loc is None:
                return current, all_moves
            layer = _edge_layer(loc)

        if layer != "U":
            # Shouldn't happen, but bail out
            return current, all_moves

        # --- Step 2: Insert from U layer ---
        u_color = _edge_color_on_face(loc, "U")
        side_face_cur = _edge_side_face_in_u(loc)
        side_face_cur_idx = _FACE_ORDER.index(side_face_cur)

        if u_color == "W":
            # White is on U face. Position edge above target slot, then face2.
            u_rot = (side_face_cur_idx - target_face_idx) % 4
            if u_rot != 0:
                current, moves = _do(current, _u_turns_str(u_rot))
                all_moves.extend(moves)

            insert_alg = target_face + "2"
            current, moves = _do(current, insert_alg)
            all_moves.extend(moves)
        else:
            # White is on side face. Position edge above target slot, then use
            # the safe 4-move insertion algorithm.
            u_rot = (side_face_cur_idx - target_face_idx) % 4
            if u_rot != 0:
                current, moves = _do(current, _u_turns_str(u_rot))
                all_moves.extend(moves)

            insert_alg = _CROSS_INSERT_WHITE_ON_SIDE[target_face]
            current, moves = _do(current, insert_alg)
            all_moves.extend(moves)

        return current, all_moves

    return state, []


# ---------------------------------------------------------------------------
# Phase 2: White Corners
# ---------------------------------------------------------------------------

def _is_white_corner_solved(state, corner_name):
    """Check if a single white corner is correctly placed."""
    positions = WHITE_CORNERS[corner_name]
    target = WHITE_CORNER_TARGETS[corner_name]
    return all(
        _gs(state, face, idx) == target[i]
        for i, (face, idx) in enumerate(positions)
    )


def is_white_corners_solved(state):
    """Check if all four white corners are correctly placed."""
    return all(_is_white_corner_solved(state, c) for c in WHITE_CORNERS)


def _corner_in_d_layer(loc):
    """Check if corner is in D layer."""
    return any(pos[0] == "D" for pos, _ in [loc[0], loc[1], loc[2]])


def _corner_in_u_layer(loc):
    """Check if corner is in U layer."""
    return any(pos[0] == "U" for pos, _ in [loc[0], loc[1], loc[2]])


def _corner_side_faces(loc):
    """Get the two non-U/D faces of a corner (sorted tuple)."""
    faces = []
    for pos, _ in [loc[0], loc[1], loc[2]]:
        if pos[0] not in ("U", "D"):
            faces.append(pos[0])
    return tuple(sorted(faces))


# The insert algorithm for each corner slot (sexy move variant).
# Each swaps the U-layer corner above the slot with the D-layer corner.
# Applying 1, 3, or 5 times solves the corner depending on orientation.
_CORNER_INSERT_ALG = {
    "DFR": "R U R' U'",
    "DFL": "L' U' L U",
    "DBR": "R' U' R U",
    "DBL": "L U L' U'",
}

# Side faces above each D-layer corner slot
_CORNER_ABOVE = {
    "DFR": ("F", "R"),
    "DFL": ("F", "L"),
    "DBR": ("B", "R"),
    "DBL": ("B", "L"),
}

# Maps sorted pair of side faces to a U-layer corner index (for U-turn positioning)
_U_CORNER_POS = {
    ("F", "R"): 0,
    ("F", "L"): 1,
    ("B", "L"): 2,
    ("B", "R"): 3,
}


def solve_white_corners_step(state):
    """Solve one white corner. Returns (new_state, moves_applied)."""
    if is_white_corners_solved(state):
        return state, []

    corner_order = ["DFR", "DFL", "DBR", "DBL"]

    for corner_name in corner_order:
        if _is_white_corner_solved(state, corner_name):
            continue

        targets = WHITE_CORNER_TARGETS[corner_name]
        c1, c2, c3 = targets

        loc = _find_corner(state, c1, c2, c3)
        if loc is None:
            continue

        current = state
        all_moves = []

        # If corner is in D layer but wrong, eject it to U
        if _corner_in_d_layer(loc):
            side_faces = _corner_side_faces(loc)
            # Find the D-slot this corner is in and eject
            for cn, af in _CORNER_ABOVE.items():
                if tuple(sorted(af)) == side_faces:
                    eject_alg = _CORNER_INSERT_ALG[cn]
                    current, moves = _do(current, eject_alg)
                    all_moves.extend(moves)
                    break

            loc = _find_corner(current, c1, c2, c3)
            if loc is None:
                return current, all_moves

        if not _corner_in_u_layer(loc):
            return current, all_moves

        # Position above target slot using U turns
        cur_side_faces = _corner_side_faces(loc)
        target_side_faces = tuple(sorted(_CORNER_ABOVE[corner_name]))
        cur_idx = _U_CORNER_POS.get(cur_side_faces, 0)
        target_idx = _U_CORNER_POS.get(target_side_faces, 0)
        u_rot = (cur_idx - target_idx) % 4
        if u_rot != 0:
            current, moves = _do(current, _u_turns_str(u_rot))
            all_moves.extend(moves)

        # Apply insert algorithm repeatedly (up to 6 times)
        insert_alg = _CORNER_INSERT_ALG[corner_name]
        for _ in range(6):
            current, moves = _do(current, insert_alg)
            all_moves.extend(moves)
            if _is_white_corner_solved(current, corner_name):
                break

        return current, all_moves

    return state, []


# ---------------------------------------------------------------------------
# Phase 3: Middle Layer Edges
# ---------------------------------------------------------------------------

def _is_middle_edge_solved(state, edge_name):
    """Check if a single middle edge is correctly placed."""
    positions = MIDDLE_EDGES[edge_name]
    target = MIDDLE_EDGE_TARGETS[edge_name]
    return all(
        _gs(state, face, idx) == target[i]
        for i, (face, idx) in enumerate(positions)
    )


def is_middle_layer_solved(state):
    """Check if all four middle layer edges are correctly placed."""
    return all(_is_middle_edge_solved(state, e) for e in MIDDLE_EDGES)


def detect_middle_case(state):
    """Detect middle layer case: 'insert_from_top', 'eject', or 'solved'."""
    if is_middle_layer_solved(state):
        return "solved"

    # Check if any unsolved middle edge is in U layer
    for edge_name in MIDDLE_EDGES:
        if _is_middle_edge_solved(state, edge_name):
            continue
        target = MIDDLE_EDGE_TARGETS[edge_name]
        loc = _find_edge(state, target[0], target[1])
        if loc and _edge_layer(loc) == "U":
            return "insert_from_top"

    return "eject"


# Standard F2L edge insertion algorithms.
# RIGHT = edge above front face, insert to CW neighbor.
# LEFT = edge above front face, insert to CCW neighbor.
# Each is parameterized by the front face:
#   front=F: right=R, left=L
#   front=R: right=B, left=F
#   front=B: right=L, left=R
#   front=L: right=F, left=B
_MIDDLE_INSERT_RIGHT = {
    "F": "U R U' R' U' F' U F",
    "R": "U B U' B' U' R' U R",
    "B": "U L U' L' U' B' U B",
    "L": "U F U' F' U' L' U L",
}
_MIDDLE_INSERT_LEFT = {
    "F": "U' L' U L U F U' F'",
    "R": "U' F' U F U R U' R'",
    "B": "U' R' U R U B U' B'",
    "L": "U' B' U B U L U' L'",
}

# Eject: use any insert algorithm to kick out the wrong edge.
# Using the right-insert from the first face of the slot.
_MIDDLE_EJECT = {
    "FR": "U R U' R' U' F' U F",
    "FL": "U' L' U L U F U' F'",
    "BR": "U B U' B' U' R' U R",
    "BL": "U L U' L' U' B' U B",
}


def solve_middle_step(state):
    """Solve one middle layer edge. Returns (new_state, moves_applied)."""
    if is_middle_layer_solved(state):
        return state, []

    current = state
    all_moves = []

    edge_info = [
        ("FR", "G", "R"),
        ("FL", "G", "O"),
        ("BR", "B", "R"),
        ("BL", "B", "O"),
    ]

    # First try to insert from U layer
    for edge_name, c1, c2 in edge_info:
        if _is_middle_edge_solved(current, edge_name):
            continue

        loc = _find_edge(current, c1, c2)
        if loc is None:
            continue
        if _edge_layer(loc) != "U":
            continue

        u_color = _edge_color_on_face(loc, "U")
        side_face_cur = _edge_side_face_in_u(loc)
        side_color = _edge_color_on_face(loc, side_face_cur)

        # Skip if either color is yellow (doesn't belong in middle)
        if u_color == "Y" or side_color == "Y":
            continue

        # Rotate U so side sticker matches center below
        target_center_face = _COLOR_TO_FACE[side_color]
        cur_idx = _FACE_ORDER.index(side_face_cur)
        target_idx = _FACE_ORDER.index(target_center_face)
        u_rot = (cur_idx - target_idx) % 4
        if u_rot != 0:
            current, moves = _do(current, _u_turns_str(u_rot))
            all_moves.extend(moves)

        # Determine insert direction
        u_target_face = _COLOR_TO_FACE[u_color]
        tcf_idx = _FACE_ORDER.index(target_center_face)
        utf_idx = _FACE_ORDER.index(u_target_face)
        diff = (utf_idx - tcf_idx) % 4

        if diff == 1:
            alg = _MIDDLE_INSERT_RIGHT[target_center_face]
        elif diff == 3:
            alg = _MIDDLE_INSERT_LEFT[target_center_face]
        else:
            alg = _MIDDLE_INSERT_RIGHT[target_center_face]

        current, moves = _do(current, alg)
        all_moves.extend(moves)
        return current, all_moves

    # No edge in U layer -> eject a wrong middle edge
    for edge_name, c1, c2 in edge_info:
        if _is_middle_edge_solved(current, edge_name):
            continue

        if edge_name in _MIDDLE_EJECT:
            alg = _MIDDLE_EJECT[edge_name]
            current, moves = _do(current, alg)
            all_moves.extend(moves)
            return current, all_moves

    return current, all_moves


# ---------------------------------------------------------------------------
# Phase 4: Yellow Cross (OLL edges)
# ---------------------------------------------------------------------------

def is_yellow_cross_solved(state):
    """Check if the yellow cross is formed on the U face."""
    return (
        _gs(state, "U", 1) == "Y"
        and _gs(state, "U", 3) == "Y"
        and _gs(state, "U", 5) == "Y"
        and _gs(state, "U", 7) == "Y"
    )


def detect_yellow_cross_case(state):
    """Detect: 'dot', 'l_shape', 'line', or 'solved'."""
    if is_yellow_cross_solved(state):
        return "solved"

    top = _gs(state, "U", 1) == "Y"
    left = _gs(state, "U", 3) == "Y"
    right = _gs(state, "U", 5) == "Y"
    bottom = _gs(state, "U", 7) == "Y"

    count = sum([top, left, right, bottom])

    if count == 0:
        return "dot"
    elif count == 2:
        if (top and bottom) or (left and right):
            return "line"
        else:
            return "l_shape"
    return "dot"


def solve_yellow_cross_step(state):
    """Apply one step of yellow cross algorithm. Returns (new_state, moves_applied)."""
    case = detect_yellow_cross_case(state)
    if case == "solved":
        return state, []

    current = state
    all_moves = []

    base_alg = "F R U R' U' F'"

    if case == "dot":
        current, moves = _do(current, base_alg)
        all_moves.extend(moves)

    elif case == "l_shape":
        # Orient L-shape so yellow edges are at back (U[1]) and left (U[3])
        top = _gs(current, "U", 1) == "Y"
        left = _gs(current, "U", 3) == "Y"
        right = _gs(current, "U", 5) == "Y"
        bottom = _gs(current, "U", 7) == "Y"

        if top and left:
            pass
        elif top and right:
            current, moves = _do(current, "U'")
            all_moves.extend(moves)
        elif bottom and right:
            current, moves = _do(current, "U2")
            all_moves.extend(moves)
        elif bottom and left:
            current, moves = _do(current, "U")
            all_moves.extend(moves)

        current, moves = _do(current, base_alg)
        all_moves.extend(moves)

    elif case == "line":
        # Orient line horizontally (left-right: U[3] and U[5])
        left = _gs(current, "U", 3) == "Y"
        if not left:
            current, moves = _do(current, "U")
            all_moves.extend(moves)

        current, moves = _do(current, base_alg)
        all_moves.extend(moves)

    return current, all_moves


# ---------------------------------------------------------------------------
# Phase 5: Yellow Face (OLL corners)
# ---------------------------------------------------------------------------

def is_yellow_face_solved(state):
    """Check if the entire U face is yellow."""
    return all(_gs(state, "U", i) == "Y" for i in range(9))


def _yellow_corner_count(state):
    """Count how many U-face corners are yellow."""
    return sum(1 for i in [0, 2, 6, 8] if _gs(state, "U", i) == "Y")


def detect_yellow_face_case(state):
    """Detect: 'sune', 'antisune', 'no_fish', 'no_yellow_corners', or 'solved'."""
    if is_yellow_face_solved(state):
        return "solved"

    count = _yellow_corner_count(state)

    if count == 0:
        return "no_yellow_corners"
    elif count == 1:
        # Fish shape. Find the yellow corner and determine sune vs antisune.
        yellow_pos = None
        for i in [0, 2, 6, 8]:
            if _gs(state, "U", i) == "Y":
                yellow_pos = i
                break

        # Orient so yellow corner is at U[6] (front-left)
        rot_map = {6: "", 8: "U", 2: "U2", 0: "U'"}
        rot = rot_map[yellow_pos]
        test = state
        if rot:
            test, _ = _do(state, rot)

        # Check UFR corner (U[8], F[2], R[0]) after rotation
        # F[2]==Y means yellow is on front face → need Sune to solve
        # R[0]==Y means yellow is on right face → need Anti-Sune to solve
        if _gs(test, "F", 2) == "Y":
            return "sune"
        else:
            return "antisune"
    elif count == 2:
        return "no_fish"
    else:
        return "no_fish"


def solve_yellow_face_step(state):
    """Apply one step of yellow face algorithm. Returns (new_state, moves_applied)."""
    case = detect_yellow_face_case(state)
    if case == "solved":
        return state, []

    current = state
    all_moves = []

    sune = "R U R' U R U2 R'"

    if case in ("sune", "antisune"):
        # Orient: put the single yellow corner at U[6] (front-left)
        yellow_pos = None
        for i in [0, 2, 6, 8]:
            if _gs(current, "U", i) == "Y":
                yellow_pos = i
                break

        rot_map = {6: "", 8: "U", 2: "U2", 0: "U'"}
        rot = rot_map.get(yellow_pos, "")
        if rot:
            current, moves = _do(current, rot)
            all_moves.extend(moves)

        # Always use Sune for fish cases. Anti-Sune can create cycles
        # when the fish resulted from a non-fish case. Sune always
        # converges within ~5 iterations due to its order-6 property.
        current, moves = _do(current, sune)
        all_moves.extend(moves)

    elif case == "no_yellow_corners":
        # 0 yellow corners: orient so front-left corner has yellow on L face (L[2])
        for u in ["", "U", "U2", "U'"]:
            test = current
            if u:
                test, _ = _do(current, u)
            if _gs(test, "L", 2) == "Y":
                if u:
                    current, moves = _do(current, u)
                    all_moves.extend(moves)
                break

        current, moves = _do(current, sune)
        all_moves.extend(moves)

    elif case == "no_fish":
        # 2 yellow corners: orient so front-left corner has yellow on front face (F[0])
        placed = False
        for u in ["", "U", "U2", "U'"]:
            test = current
            if u:
                test, _ = _do(current, u)
            if _gs(test, "F", 0) == "Y":
                if u:
                    current, moves = _do(current, u)
                    all_moves.extend(moves)
                placed = True
                break

        if not placed:
            # Try L[2] orientation
            for u in ["", "U", "U2", "U'"]:
                test = current
                if u:
                    test, _ = _do(current, u)
                if _gs(test, "L", 2) == "Y":
                    if u:
                        current, moves = _do(current, u)
                        all_moves.extend(moves)
                    break

        current, moves = _do(current, sune)
        all_moves.extend(moves)

    return current, all_moves


# ---------------------------------------------------------------------------
# Phase 6: Yellow Corner Position (PLL)
# ---------------------------------------------------------------------------

def is_yellow_corners_positioned(state):
    """Check if all yellow corners have the correct color sets (may need U rotation)."""
    for corner_name, positions in YELLOW_CORNERS.items():
        corner_colors = set()
        for face, idx in positions:
            corner_colors.add(_gs(state, face, idx))
        expected = set()
        for face, _ in positions:
            expected.add(COLORS[face])
        if corner_colors != expected:
            return False
    return True


def detect_yellow_corners_case(state):
    """Detect: 'headlights', 'no_headlights', or 'solved'."""
    if is_yellow_corners_positioned(state):
        return "solved"

    for face in _FACE_ORDER:
        stickers = {
            "F": (("F", 0), ("F", 2)),
            "R": (("R", 0), ("R", 2)),
            "B": (("B", 0), ("B", 2)),
            "L": (("L", 0), ("L", 2)),
        }
        (f1, i1), (f2, i2) = stickers[face]
        if _gs(state, f1, i1) == _gs(state, f2, i2):
            return "headlights"

    return "no_headlights"


def _count_correct_corners(state):
    """Count how many U-layer corners have the correct color set."""
    corner_slots = [
        ("UFR", [("U", 8), ("F", 2), ("R", 0)]),
        ("UFL", [("U", 6), ("F", 0), ("L", 2)]),
        ("UBR", [("U", 2), ("B", 0), ("R", 2)]),
        ("UBL", [("U", 0), ("B", 2), ("L", 0)]),
    ]
    correct = []
    wrong = []
    for name, positions in corner_slots:
        actual = set(_gs(state, f, i) for f, i in positions)
        expected = set(COLORS[f] for f, _ in positions)
        if actual == expected:
            correct.append(name)
        else:
            wrong.append(name)
    return correct, wrong


def solve_yellow_corners_step(state):
    """Position yellow corners. Returns (new_state, moves_applied)."""
    if is_yellow_corners_positioned(state):
        return state, []

    current = state
    all_moves = []

    # PLL corner 3-cycle: fixes UFL, cycles UFR→UBR→UBL.
    # Preserves the yellow face (OLL) unlike the non-PLL U R U' L' variant.
    three_cycle = "R' F R' B2 R F' R' B2 R2"
    # T-perm: swaps UFR↔UBR corners (and UR↔UL edges), preserves OLL.
    t_perm = "R U R' U' R' F R2 U' R' U' R U R' F'"

    correct, wrong = _count_correct_corners(current)

    if len(correct) == 4:
        return current, all_moves

    elif len(correct) >= 1 and len(wrong) == 2:
        # 2-swap case: the 3-cycle can't fix this (parity mismatch).
        # Use T-perm with U-setup to swap the two wrong corners.
        for u in ["", "U", "U2", "U'"]:
            test = copy.deepcopy(current)
            test_moves = []
            if u:
                test, moves = _do(test, u)
                test_moves.extend(moves)
            test, moves = _do(test, t_perm)
            test_moves.extend(moves)
            if u:
                inv = {"U": "U'", "U'": "U", "U2": "U2"}
                test, moves = _do(test, inv[u])
                test_moves.extend(moves)
            if is_yellow_corners_positioned(test):
                return test, test_moves
        # Diagonal 2-swap: apply T-perm to convert to a 3-cycle.
        current, moves = _do(current, t_perm)
        all_moves.extend(moves)

    elif len(correct) >= 1:
        # 3-cycle case: orient the correct corner to UFL (fixed point)
        u_rotations = {"UFR": "U", "UFL": "", "UBR": "U2", "UBL": "U'"}
        rot = u_rotations[correct[0]]
        if rot:
            current, moves = _do(current, rot)
            all_moves.extend(moves)
        current, moves = _do(current, three_cycle)
        all_moves.extend(moves)

    else:
        # No correct corners (double-swap): apply 3-cycle to create one
        current, moves = _do(current, three_cycle)
        all_moves.extend(moves)

    return current, all_moves


# ---------------------------------------------------------------------------
# Phase 7: Yellow Edge Position (PLL)
# ---------------------------------------------------------------------------

def is_yellow_edges_positioned(state):
    """Check if all yellow edges are correctly positioned (cube solved up to U rotation)."""
    for face in _FACE_ORDER:
        if _gs(state, face, 1) != COLORS[face]:
            return False
    return True


def detect_yellow_edges_case(state):
    """Detect: 'cw_cycle', 'ccw_cycle', 'opposite_swap', 'adjacent_swap', or 'solved'."""
    # Check if a U rotation solves edges WITHOUT breaking corner positioning
    for u in ["", "U", "U2", "U'"]:
        test = state
        if u:
            test, _ = _do(state, u)
        if is_yellow_edges_positioned(test) and is_yellow_corners_positioned(test):
            return "solved"

    edges = {}
    for face in _FACE_ORDER:
        edges[face] = _gs(state, face, 1)

    solved_count = sum(1 for f in _FACE_ORDER if edges[f] == COLORS[f])

    if solved_count == 1:
        solved_face = None
        for f in _FACE_ORDER:
            if edges[f] == COLORS[f]:
                solved_face = f
                break

        idx = _FACE_ORDER.index(solved_face)
        others = [_FACE_ORDER[(idx + i) % 4] for i in range(1, 4)]

        if edges[others[0]] == COLORS[others[1]]:
            return "cw_cycle"
        else:
            return "ccw_cycle"

    elif solved_count == 0:
        if edges["F"] == COLORS["B"] and edges["B"] == COLORS["F"]:
            if edges["R"] == COLORS["L"] and edges["L"] == COLORS["R"]:
                return "opposite_swap"
        for i in range(4):
            f1 = _FACE_ORDER[i]
            f2 = _FACE_ORDER[(i + 1) % 4]
            if edges[f1] == COLORS[f2] and edges[f2] == COLORS[f1]:
                return "adjacent_swap"
        return "opposite_swap"

    return "cw_cycle"


def solve_yellow_edges_step(state):
    """Position yellow edges. Returns (new_state, moves_applied)."""
    current = state
    all_moves = []

    # Check if a U rotation solves edges WITHOUT breaking corner positioning
    for u in ["", "U", "U'", "U2"]:
        test = current
        if u:
            test, _ = _do(current, u)
        if is_yellow_edges_positioned(test) and is_yellow_corners_positioned(test):
            if u:
                current, moves = _do(current, u)
                all_moves.extend(moves)
            return current, all_moves

    case = detect_yellow_edges_case(current)
    if case == "solved":
        return current, all_moves

    # Ua perm variants (CW 3-cycle), keyed by which edge stays fixed.
    # Derived from base Ua (R U' R U R U R U' R' U' R2) via y-rotation conjugation.
    _cw = {
        "B": "R U' R U R U R U' R' U' R2",
        "R": "F U' F U F U F U' F' U' F2",
        "F": "L U' L U L U L U' L' U' L2",
        "L": "B U' B U B U B U' B' U' B2",
    }
    # Ub perm variants (CCW 3-cycle), keyed by which edge stays fixed.
    _ccw = {
        "B": "R2 U R U R' U' R' U' R' U R'",
        "R": "F2 U F U F' U' F' U' F' U F'",
        "F": "L2 U L U L' U' L' U' L' U L'",
        "L": "B2 U B U B' U' B' U' B' U B'",
    }

    if case in ("cw_cycle", "ccw_cycle"):
        # Find the anchor (correctly positioned edge)
        edges = {}
        for face in _FACE_ORDER:
            edges[face] = _gs(current, face, 1)

        anchor = None
        for f in _FACE_ORDER:
            if edges[f] == COLORS[f]:
                anchor = f
                break

        if anchor:
            if case == "cw_cycle":
                current, moves = _do(current, _cw[anchor])
            else:
                current, moves = _do(current, _ccw[anchor])
            all_moves.extend(moves)

    elif case in ("opposite_swap", "adjacent_swap"):
        # No anchor edge: apply Ua from any position to create one
        current, moves = _do(current, _cw["B"])
        all_moves.extend(moves)

    return current, all_moves

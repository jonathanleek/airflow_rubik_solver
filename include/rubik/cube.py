"""Rubik's cube state representation and move logic using permutation arrays."""

import copy
import random

from include.rubik.constants import COLORS, FACES, MOVE_NAMES, SOLVED_STATE


def _index(face, pos):
    """Convert (face, position) to a flat index 0-53."""
    return FACES.index(face) * 9 + pos


def _face_pos(flat_idx):
    """Convert flat index 0-53 to (face, position)."""
    return FACES[flat_idx // 9], flat_idx % 9


def _make_identity():
    """Return identity permutation (54 elements)."""
    return list(range(54))


def _apply_cycles(perm, cycles):
    """Apply cycle notation to a permutation. Each cycle is a list of flat indices."""
    for cycle in cycles:
        if len(cycle) < 2:
            continue
        last_val = perm[cycle[-1]]
        for i in range(len(cycle) - 1, 0, -1):
            perm[cycle[i]] = perm[cycle[i - 1]]
        perm[cycle[0]] = last_val
    return perm


def _rotate_face_cw(face):
    """Return cycles for rotating a face 90 degrees clockwise.

    All faces use the same cycle [0,2,8,6] for corners and [1,5,7,3] for edges.
    This matches the SageMath Rubik's cube group convention.
    """
    b = FACES.index(face) * 9
    return [
        [b + 0, b + 2, b + 8, b + 6],
        [b + 1, b + 5, b + 7, b + 3],
    ]


def _build_move_perms():
    """Build permutation arrays for all 18 moves."""
    moves = {}

    # R face: rotates R face CW, cycles U/F/D/B columns
    # R: U[2,5,8] -> B[6,3,0], F[2,5,8] -> U[2,5,8], D[2,5,8] -> F[2,5,8], B[6,3,0] -> D[2,5,8]
    p = _make_identity()
    _apply_cycles(p, _rotate_face_cw("R"))
    _apply_cycles(p, [
        [_index("U", 2), _index("B", 6), _index("D", 2), _index("F", 2)],
        [_index("U", 5), _index("B", 3), _index("D", 5), _index("F", 5)],
        [_index("U", 8), _index("B", 0), _index("D", 8), _index("F", 8)],
    ])
    moves["R"] = p

    # L face: rotates L face CW
    # L: U[0,3,6] -> F[0,3,6] -> D[0,3,6] -> B[8,5,2] -> U[0,3,6]
    p = _make_identity()
    _apply_cycles(p, _rotate_face_cw("L"))
    _apply_cycles(p, [
        [_index("U", 0), _index("F", 0), _index("D", 0), _index("B", 8)],
        [_index("U", 3), _index("F", 3), _index("D", 3), _index("B", 5)],
        [_index("U", 6), _index("F", 6), _index("D", 6), _index("B", 2)],
    ])
    moves["L"] = p

    # U face: rotates U face CW (viewed from above)
    # Cycle [F,L,B,R] means R→F, F→L, L→B, B→R (CW from above)
    p = _make_identity()
    _apply_cycles(p, _rotate_face_cw("U"))
    _apply_cycles(p, [
        [_index("F", 0), _index("L", 0), _index("B", 0), _index("R", 0)],
        [_index("F", 1), _index("L", 1), _index("B", 1), _index("R", 1)],
        [_index("F", 2), _index("L", 2), _index("B", 2), _index("R", 2)],
    ])
    moves["U"] = p

    # D face: rotates D face CW (viewed from below)
    # Cycle [F,R,B,L] means L→F, F→R, R→B, B→L (CW from below)
    p = _make_identity()
    _apply_cycles(p, _rotate_face_cw("D"))
    _apply_cycles(p, [
        [_index("F", 6), _index("R", 6), _index("B", 6), _index("L", 6)],
        [_index("F", 7), _index("R", 7), _index("B", 7), _index("L", 7)],
        [_index("F", 8), _index("R", 8), _index("B", 8), _index("L", 8)],
    ])
    moves["D"] = p

    # F face: rotates F face CW
    # F: U[6,7,8] -> R[0,3,6] -> D[2,1,0] -> L[8,5,2] -> U[6,7,8]
    p = _make_identity()
    _apply_cycles(p, _rotate_face_cw("F"))
    _apply_cycles(p, [
        [_index("U", 6), _index("R", 0), _index("D", 2), _index("L", 8)],
        [_index("U", 7), _index("R", 3), _index("D", 1), _index("L", 5)],
        [_index("U", 8), _index("R", 6), _index("D", 0), _index("L", 2)],
    ])
    moves["F"] = p

    # B face: rotates B face CW (looking from back)
    # B CW from behind: U top -> L left col, L left -> D bottom, D bottom -> R right col, R right -> U top
    # Note: from behind, "right" is L and "left" is R (mirrored)
    p = _make_identity()
    _apply_cycles(p, _rotate_face_cw("B"))
    _apply_cycles(p, [
        [_index("U", 2), _index("L", 0), _index("D", 6), _index("R", 8)],
        [_index("U", 1), _index("L", 3), _index("D", 7), _index("R", 5)],
        [_index("U", 0), _index("L", 6), _index("D", 8), _index("R", 2)],
    ])
    moves["B"] = p

    # Build inverse and double moves
    for face_move in ["R", "L", "U", "D", "F", "B"]:
        cw = moves[face_move]
        # Inverse: apply CW three times
        ccw = compose_perms(cw, compose_perms(cw, cw))
        moves[face_move + "'"] = ccw
        # Double: apply CW twice
        moves[face_move + "2"] = compose_perms(cw, cw)

    return moves


def compose_perms(p1, p2):
    """Compose two permutations: result[i] = p1[p2[i]]."""
    return [p1[p2[i]] for i in range(54)]


def _state_to_flat(state):
    """Convert dict state to flat 54-element list."""
    flat = []
    for face in FACES:
        flat.extend(state[face])
    return flat


def _flat_to_state(flat):
    """Convert flat 54-element list to dict state."""
    state = {}
    for i, face in enumerate(FACES):
        state[face] = flat[i * 9:(i + 1) * 9]
    return state


# Build move permutation tables at module load
MOVE_PERMS = _build_move_perms()


def apply_move(state, move_name):
    """Apply a single move to a cube state dict. Returns new state."""
    if move_name not in MOVE_PERMS:
        raise ValueError(f"Unknown move: {move_name}")
    flat = _state_to_flat(state)
    perm = MOVE_PERMS[move_name]
    new_flat = [flat[perm[i]] for i in range(54)]
    return _flat_to_state(new_flat)


def apply_algorithm(state, algorithm):
    """Apply a sequence of moves (space-separated string or list). Returns (new_state, move_list)."""
    if isinstance(algorithm, str):
        moves = algorithm.split()
    else:
        moves = list(algorithm)
    current = copy.deepcopy(state)
    for move in moves:
        current = apply_move(current, move)
    return current, moves


def get_solved_state():
    """Return a fresh copy of the solved state."""
    return copy.deepcopy(SOLVED_STATE)


def generate_scramble(num_moves=20):
    """Generate a random scramble of the given length. Returns list of move strings."""
    base_moves = ["R", "L", "U", "D", "F", "B"]
    suffixes = ["", "'", "2"]
    scramble = []
    last_face = None
    for _ in range(num_moves):
        face = random.choice(base_moves)
        while face == last_face:
            face = random.choice(base_moves)
        last_face = face
        suffix = random.choice(suffixes)
        scramble.append(face + suffix)
    return scramble


def is_solved(state):
    """Check if the cube is in the solved state."""
    for face in FACES:
        if len(set(state[face])) != 1:
            return False
        if state[face][0] != COLORS[face]:
            return False
    return True


def get_sticker(state, face, index):
    """Get the color of a sticker at (face, index)."""
    return state[face][index]


def validate_state(state):
    """Validate that a cube state is structurally valid."""
    if not isinstance(state, dict):
        raise ValueError("State must be a dict")
    for face in FACES:
        if face not in state:
            raise ValueError(f"Missing face: {face}")
        if len(state[face]) != 9:
            raise ValueError(f"Face {face} must have 9 stickers, got {len(state[face])}")
    # Check center pieces are correct
    for face in FACES:
        if state[face][4] != COLORS[face]:
            raise ValueError(f"Center of {face} should be {COLORS[face]}, got {state[face][4]}")
    # Check total color counts
    color_counts = {}
    for face in FACES:
        for sticker in state[face]:
            color_counts[sticker] = color_counts.get(sticker, 0) + 1
    for color in COLORS.values():
        if color_counts.get(color, 0) != 9:
            raise ValueError(f"Color {color} appears {color_counts.get(color, 0)} times, expected 9")
    return True


def parse_scramble_string(scramble_str):
    """Parse a scramble string like 'R U R' F2 L' into a list of moves."""
    moves = scramble_str.strip().split()
    for m in moves:
        if m not in MOVE_PERMS:
            raise ValueError(f"Unknown move in scramble: {m}")
    return moves

"""Constants for the Rubik's cube solver."""

# Face names
FACES = ["U", "D", "F", "B", "L", "R"]

# Color convention: U=Yellow, D=White, F=Green, B=Blue, L=Orange, R=Red
COLORS = {
    "U": "Y",  # Yellow
    "D": "W",  # White
    "F": "G",  # Green
    "B": "B",  # Blue
    "L": "O",  # Orange
    "R": "R",  # Red
}

# Solved state: each face is 9 copies of its color
SOLVED_STATE = {face: [COLORS[face]] * 9 for face in FACES}

# Sticker index layout per face:
#  0 | 1 | 2
#  ---------
#  3 | 4 | 5
#  ---------
#  6 | 7 | 8
# Index 4 is always the center.

# Phase names in order
PHASES = [
    "cross",
    "white_corners",
    "middle_layer",
    "yellow_cross",
    "yellow_face",
    "yellow_corners",
    "yellow_edges",
    "complete",
]

# Max iterations per phase (safety limit for self-triggering loops)
MAX_ITERATIONS = {
    "cross": 20,
    "white_corners": 20,
    "middle_layer": 20,
    "yellow_cross": 10,
    "yellow_face": 10,
    "yellow_corners": 15,
    "yellow_edges": 15,
}

# DAG IDs for each phase
PHASE_DAG_IDS = {
    "cross": "rubik_solve_cross",
    "white_corners": "rubik_solve_white_corners",
    "middle_layer": "rubik_solve_middle_layer",
    "yellow_cross": "rubik_solve_yellow_cross",
    "yellow_face": "rubik_solve_yellow_face",
    "yellow_corners": "rubik_solve_yellow_corners",
    "yellow_edges": "rubik_solve_yellow_edges",
    "complete": "rubik_complete",
}

# Next phase mapping
NEXT_PHASE = {
    "cross": "white_corners",
    "white_corners": "middle_layer",
    "middle_layer": "yellow_cross",
    "yellow_cross": "yellow_face",
    "yellow_face": "yellow_corners",
    "yellow_corners": "yellow_edges",
    "yellow_edges": "complete",
}

# Edge positions: (face, index) pairs for each edge piece.
# Each edge is defined by two stickers. The first listed is the "primary" face.
# White (D) cross edges
WHITE_CROSS_EDGES = {
    "DF": (("D", 1), ("F", 7)),
    "DR": (("D", 5), ("R", 7)),
    "DB": (("D", 7), ("B", 7)),
    "DL": (("D", 3), ("L", 7)),
}

# White (D) corner positions
WHITE_CORNERS = {
    "DFR": (("D", 2), ("F", 8), ("R", 6)),
    "DFL": (("D", 0), ("F", 6), ("L", 8)),
    "DBR": (("D", 8), ("B", 6), ("R", 8)),
    "DBL": (("D", 6), ("B", 8), ("L", 6)),
}

# Middle layer edge positions
MIDDLE_EDGES = {
    "FR": (("F", 5), ("R", 3)),
    "FL": (("F", 3), ("L", 5)),
    "BR": (("B", 3), ("R", 5)),
    "BL": (("B", 5), ("L", 3)),
}

# Yellow (U) edge positions
YELLOW_CROSS_EDGES = {
    "UF": (("U", 7), ("F", 1)),
    "UR": (("U", 5), ("R", 1)),
    "UB": (("U", 1), ("B", 1)),
    "UL": (("U", 3), ("L", 1)),
}

# Yellow (U) corner positions
YELLOW_CORNERS = {
    "UFR": (("U", 8), ("F", 2), ("R", 0)),
    "UFL": (("U", 6), ("F", 0), ("L", 2)),
    "UBR": (("U", 2), ("B", 0), ("R", 2)),
    "UBL": (("U", 0), ("B", 2), ("L", 0)),
}

# Target colors for white cross edges (D-face center is white)
WHITE_CROSS_TARGETS = {
    "DF": ("W", "G"),
    "DR": ("W", "R"),
    "DB": ("W", "B"),
    "DL": ("W", "O"),
}

# Target colors for white corners
WHITE_CORNER_TARGETS = {
    "DFR": ("W", "G", "R"),
    "DFL": ("W", "G", "O"),
    "DBR": ("W", "B", "R"),
    "DBL": ("W", "B", "O"),
}

# Target colors for middle layer edges
MIDDLE_EDGE_TARGETS = {
    "FR": ("G", "R"),
    "FL": ("G", "O"),
    "BR": ("B", "R"),
    "BL": ("B", "O"),
}

# All 18 move names
MOVE_NAMES = [
    "R", "R'", "R2",
    "L", "L'", "L2",
    "U", "U'", "U2",
    "D", "D'", "D2",
    "F", "F'", "F2",
    "B", "B'", "B2",
]

AIRFLOW_VARIABLE_KEY = "rubik_cube_state"

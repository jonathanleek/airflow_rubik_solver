"""Verify that U face sticker rotation matches adjacent piece rotation direction."""
import sys
sys.path.insert(0, ".")
from include.rubik.cube import apply_move, get_solved_state

state = get_solved_state()
after_u = apply_move(state, "U")

# Adjacent cycle: verified F[0,1,2] → R[0,1,2] (CW from above)
print("Adjacent pieces after U move (CW from above):")
print(f"  F top row -> R top row: F[0]={after_u['F'][0]}, R[0]={after_u['R'][0]} (was O, now O→R)")
print(f"  Confirmed: F→R→B→L (CW)")

# Face sticker rotation
print("\nU face stickers after U move:")
print(f"  Before: 0=Y 1=Y 2=Y / 3=Y 4=Y 5=Y / 6=Y 7=Y 8=Y (all yellow)")
print(f"  After:  same (all yellow, can't tell direction)")

# To test face sticker direction, we need different colors on U face
# Set up: put a marker at U[0] and see where it goes
state2 = get_solved_state()
state2["U"][0] = "X"  # marker at top-left
after = apply_move(state2, "U")
marker_pos = after["U"].index("X")
print(f"\nMarker test: U[0]='X', after U move, X is at U[{marker_pos}]")
print(f"  If CW (viewed from above): 0→2 (top-left → top-right)")
print(f"  If CCW (viewed from above): 0→6 (top-left → bottom-left)")

if marker_pos == 2:
    print("  RESULT: CW ✓ (correct)")
elif marker_pos == 6:
    print("  RESULT: CCW ✗ (WRONG - face stickers rotate opposite to adjacent pieces!)")

# Same test for D
state3 = get_solved_state()
state3["D"][0] = "X"
after_d = apply_move(state3, "D")
d_marker = after_d["D"].index("X")
print(f"\nD face: D[0]='X', after D move, X is at D[{d_marker}]")

# Same test for B
state4 = get_solved_state()
state4["B"][0] = "X"
after_b = apply_move(state4, "B")
b_marker = after_b["B"].index("X")
print(f"B face: B[0]='X', after B move, X is at B[{b_marker}]")

# Test F, L, R for comparison
for face in ["F", "L", "R"]:
    s = get_solved_state()
    s[face][0] = "X"
    a = apply_move(s, face)
    pos = a[face].index("X")
    print(f"{face} face: {face}[0]='X', after {face} move, X is at {face}[{pos}]")

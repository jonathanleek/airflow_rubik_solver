"""Compare our cube model against known physical Rubik's cube behavior.

On a PHYSICAL cube, applying U R U' R' U' F' U F to a solved cube produces
a specific permutation. Let's check if our model matches.
"""
import sys
sys.path.insert(0, ".")
from include.rubik.cube import apply_algorithm, get_solved_state, _state_to_flat, MOVE_PERMS, compose_perms

# Build the combined permutation for U R U' R' U' F' U F
alg_moves = ["U", "R", "U'", "R'", "U'", "F'", "U", "F"]
perm = list(range(54))  # identity
for m in alg_moves:
    perm = compose_perms(MOVE_PERMS[m], perm)

# Show what this permutation does (non-identity elements)
print("Permutation of U R U' R' U' F' U F:")
print("(sticker at position X moves to position Y)")
print()

from include.rubik.cube import _face_pos
cycles = []
visited = set()
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

for cycle in cycles:
    parts = []
    for idx in cycle:
        face, pos = _face_pos(idx)
        parts.append(f"{face}[{pos}]")
    print(f"  Cycle ({len(cycle)}): {' -> '.join(parts)} -> {parts[0]}")

# Also show on solved cube what changes
print("\nApplied to solved cube - changed stickers:")
solved = get_solved_state()
result, _ = apply_algorithm(solved, " ".join(alg_moves))

from include.rubik.constants import FACES, COLORS
for face in FACES:
    for i in range(9):
        if result[face][i] != COLORS[face]:
            print(f"  {face}[{i}]: {COLORS[face]} -> {result[face][i]}")

# On a PHYSICAL Rubik's cube, U R U' R' U' F' U F should:
# 1. Create a 3-cycle of edges: UF -> FR -> FL -> UF
# 2. Create a 3-cycle of corners: UFR -> UFL -> UBR -> UFR
# (This is the well-known "sexy move insert" effect)
#
# Let's check our edge and corner positions:
print("\nKey positions after algorithm (our model):")
print(f"  UF edge: U[7]={result['U'][7]}, F[1]={result['F'][1]}")
print(f"  FR edge: F[5]={result['F'][5]}, R[3]={result['R'][3]}")
print(f"  FL edge: F[3]={result['F'][3]}, L[5]={result['L'][5]}")
print()
print(f"  UFR corner: U[8]={result['U'][8]}, F[2]={result['F'][2]}, R[0]={result['R'][0]}")
print(f"  UFL corner: U[6]={result['U'][6]}, F[0]={result['F'][0]}, L[2]={result['L'][2]}")
print(f"  UBR corner: U[2]={result['U'][2]}, B[0]={result['B'][0]}, R[2]={result['R'][2]}")

print("\nExpected for physical cube:")
print("  UF should have: FL's colors (G, O) -> U[7]=O, F[1]=G OR U[7]=G, F[1]=O")
print("  FR should have: UF's colors (Y, G) -> F[5]=Y, R[3]=G OR F[5]=G, R[3]=Y")
print("  FL should have: FR's colors (G, R) -> F[3]=R, L[5]=G OR F[3]=G, L[5]=R")

# Let's also check the T-perm: R U R' U' R' F R2 U' R' U' R U R' F'
print(f"\n{'='*60}")
print("T-perm test: R U R' U' R' F R2 U' R' U' R U R' F'")
t_perm = "R U R' U' R' F R2 U' R' U' R U R' F'"
result2, _ = apply_algorithm(solved, t_perm)

print("Changed stickers on solved cube:")
changed = 0
for face in FACES:
    for i in range(9):
        if result2[face][i] != COLORS[face]:
            print(f"  {face}[{i}]: {COLORS[face]} -> {result2[face][i]}")
            changed += 1

print(f"Total changed: {changed}")
print(f"\nT-perm on physical cube should swap: UF<->UR edges and UFR<->UBR corners")
print(f"  UF: U[7]={result2['U'][7]}, F[1]={result2['F'][1]} (should be UR's colors: Y,R)")
print(f"  UR: U[5]={result2['U'][5]}, R[1]={result2['R'][1]} (should be UF's colors: Y,G)")

# Verify the ORDER of the algorithm (should be 6 for insert, 2 for T-perm)
perm_insert = list(range(54))
for m in alg_moves:
    perm_insert = compose_perms(MOVE_PERMS[m], perm_insert)

order = 1
p = perm_insert[:]
while p != list(range(54)):
    p = compose_perms(perm_insert, p)
    order += 1
    if order > 100:
        break

print(f"\nOrder of U R U' R' U' F' U F: {order}")
print("(Physical cube: should be 6 for this algorithm)")

# Check T-perm order
t_moves = t_perm.split()
perm_t = list(range(54))
for m in t_moves:
    perm_t = compose_perms(MOVE_PERMS[m], perm_t)

order_t = 1
p = perm_t[:]
while p != list(range(54)):
    p = compose_perms(perm_t, p)
    order_t += 1
    if order_t > 100:
        break

print(f"Order of T-perm: {order_t}")
print("(Physical cube: should be 2)")

Rubik's Cube Solver on Airflow
==============================

An Apache Airflow / Astronomer project that solves a 3x3 Rubik's cube using the
beginner **layer-by-layer** method. Each stage of the solve is implemented as its
own DAG, and the DAGs chain together into a state machine that drives a scrambled
cube all the way to solved.

It reliably solves any valid scramble: a 1,000-scramble stress test of the solver
logic passes 100% (avg ~222 moves per solve).

How It Works
============

The cube is represented as 54 stickers (6 faces x 9) and moved with permutation
arrays. All the cube/solver logic is pure Python and lives in `include/rubik/`:

- `cube.py` — state representation, the 18 moves (`R R' R2` ... `B B' B2`),
  scramble generation, and validation.
- `solver.py` — the 7-phase layer-by-layer solver. Each phase exposes an
  `is_<phase>_solved(state)` check and a `solve_<phase>_step(state)` function that
  applies one step toward solving.
- `constants.py` — color convention, sticker layout, phase ordering, per-phase
  iteration limits, and DAG id mappings.

Color/orientation convention: `U`=Yellow, `D`=White, `F`=Green, `B`=Blue,
`L`=Orange, `R`=Red. The white cross is built on the **D** face.

The Solve Pipeline
==================

Solving is orchestrated as a chain of single-purpose DAGs. State (the current
cube, moves applied so far, current phase, iteration count) is stored in a single
Airflow **Variable** (`rubik_cube_state`). Each phase DAG reads the state, applies
one solving step, writes it back, then either **re-triggers itself** to keep
working the current layer or triggers the next phase via `TriggerDagRunOperator`.

```
rubik_init
   -> rubik_solve_cross            (Phase 1: white cross on D)
   -> rubik_solve_white_corners    (Phase 2: white corners)
   -> rubik_solve_middle_layer     (Phase 3: middle-layer edges)
   -> rubik_solve_yellow_cross     (Phase 4: yellow cross / OLL edges)
   -> rubik_solve_yellow_face      (Phase 5: yellow face / OLL corners)
   -> rubik_solve_yellow_corners   (Phase 6: position corners / PLL)
   -> rubik_solve_yellow_edges     (Phase 7: position edges / PLL)
   -> rubik_complete               (validate solved state + report)
```

Each phase DAG uses a `@task.branch` to decide between three outcomes per run:
keep going (apply another step and re-trigger itself), advance to the next phase,
or fail if a per-phase safety limit (`MAX_ITERATIONS` in `constants.py`) is
exceeded. In practice real solves stay well under those limits.

Running a Solve
===============

1. Start Airflow locally:

   ```
   astro dev start
   ```

   This opens the Airflow UI at http://localhost:8080/.

2. Trigger the `rubik_init` DAG. It accepts an optional `scramble` param:

   - Provide a scramble string (e.g. `R U R' U' F2 L D' B`) to solve a specific
     cube, or
   - Leave it blank to generate a random 20-move scramble.

   `rubik_init` initializes the cube state in the `rubik_cube_state` Variable and
   triggers the first phase. The remaining phases run automatically until
   `rubik_complete` validates the solved cube and prints the full solution
   (scramble, move list, and move count) to its task logs.

> Note: state is held in a single shared Variable, so only **one** cube can be
> solved at a time on a given Airflow instance. Triggering `rubik_init` again
> while a solve is in progress will overwrite the in-flight cube.

Tests & Research Scripts
========================

The `tests/` directory holds the pytest suite (this is what `astro dev pytest`
runs, and what a plain `pytest` invocation at the repo root will collect — see
`pyproject.toml`).

The `research/` directory holds standalone development scripts used while
building the cube engine and discovering the solver algorithms. Despite their
`test_*.py` names, they are **not** pytest suites — they're brute-force search
programs and diagnostic sweeps. Run them directly:

```
python3 research/test_full_solver.py     # end-to-end solve over several scrambles
```

Other scripts in `research/` cover move correctness, face-rotation direction,
middle-layer algorithm searches, and reference comparisons against SageMath's
canonical Rubik's-cube permutations.

Project Layout
==============

- `dags/` — the Rubik solver DAGs.
- `include/rubik/` — cube representation and solver logic.
- `tests/` — pytest suite (collected by `pytest` / `astro dev pytest`).
- `research/` — development scripts and algorithm-search programs (not pytest).
- `pyproject.toml` — pytest config (scopes collection to `tests/`).
- `Dockerfile` — the Astro Runtime image version.
- `requirements.txt` / `packages.txt` — Python and OS-level dependencies.

Deploy to Astronomer
====================

To deploy to an Astronomer Deployment, see the Astronomer docs:
https://www.astronomer.io/docs/astro/deploy-code/

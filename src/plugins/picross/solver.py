"""
Nonogram (Picross) Solver

Provides:
- derive_clues(): run-length encode a binary grid into row/column clues
- line_solve(): iterative constraint-propagation solver (line logic only)
- backtrack_solve(): brute-force solver for uniqueness checking
- is_line_solvable(): convenience predicate

The line solver implements the standard algorithm: for each row/column,
enumerate all valid placements consistent with known cells, then mark
cells that are filled (or empty) in ALL placements as determined.
Repeat until convergence.

Reference: Batenburg & Kosters, "Solving Nonograms by combining
relaxations", Pattern Recognition, 2009.
"""

from typing import List, Optional, Tuple

# Type aliases
Grid = List[List[int]]
Clue = List[int]  # e.g. [2, 1, 3]
ClueList = List[Clue]

# Cell states for the solver's internal grid
UNKNOWN = -1
FILLED = 1
EMPTY = 0


def derive_clues(grid: Grid) -> Tuple[ClueList, ClueList]:
    """Run-length encode a binary grid into (row_clues, col_clues).

    Each clue is a list of consecutive filled-cell run lengths.
    An all-empty line produces [0].
    """
    rows = len(grid)
    cols = len(grid[0]) if grid else 0

    row_clues: ClueList = []
    for r in range(rows):
        runs = _runs_of(grid[r])
        row_clues.append(runs if runs else [0])

    col_clues: ClueList = []
    for c in range(cols):
        col = [grid[r][c] for r in range(rows)]
        runs = _runs_of(col)
        col_clues.append(runs if runs else [0])

    return row_clues, col_clues


def _runs_of(line: List[int]) -> List[int]:
    """Return run lengths of consecutive 1s in *line*."""
    runs: List[int] = []
    count = 0
    for cell in line:
        if cell:
            count += 1
        else:
            if count > 0:
                runs.append(count)
                count = 0
    if count > 0:
        runs.append(count)
    return runs


# ── Line solver ──────────────────────────────────────────────────────────


def _valid_placements(clue: Clue, length: int, known: List[int]) -> List[List[int]]:
    """Enumerate all valid placements of *clue* in a line of *length*.

    *known* encodes what is already determined:
        UNKNOWN (-1) = undecided, FILLED (1) = must be filled, EMPTY (0) = must be empty.

    Returns a list of candidate lines (each a list of 0/1 of *length*).
    """
    if clue == [0]:
        # All-empty clue: the only valid placement is all zeros
        candidate = [EMPTY] * length
        if _compatible(candidate, known):
            return [candidate]
        return []

    results: List[List[int]] = []
    _place(clue, 0, 0, length, known, [], results)
    return results


def _place(
    clue: Clue,
    clue_idx: int,
    pos: int,
    length: int,
    known: List[int],
    current: List[int],
    results: List[List[int]],
) -> None:
    """Recursive helper: try placing clue[clue_idx..] starting at *pos*."""
    if clue_idx == len(clue):
        # All runs placed — fill remainder with EMPTY
        candidate = current + [EMPTY] * (length - pos)
        if _compatible(candidate, known):
            results.append(candidate)
        return

    run_len = clue[clue_idx]
    remaining_runs = len(clue) - clue_idx - 1
    # Minimum space needed for remaining runs (each run + 1 gap, minus last gap)
    min_remaining = sum(clue[clue_idx + 1:]) + remaining_runs

    # Try placing this run at each valid starting position
    for start in range(pos, length - run_len - min_remaining + 1):
        # Build candidate segment: empties before run, then the run
        segment = [EMPTY] * (start - pos) + [FILLED] * run_len
        # Add mandatory gap after run (unless this is the last run)
        if clue_idx < len(clue) - 1:
            segment.append(EMPTY)

        candidate_so_far = current + segment
        next_pos = pos + len(segment)

        # Quick compatibility check on the segment we just added
        seg_start = pos
        seg_end = pos + len(segment)
        if not _segment_compatible(segment, known, seg_start):
            # If we placed empties before a FILLED known cell, no point
            # continuing further right — we'd skip a required filled cell
            if any(known[i] == FILLED for i in range(pos, min(start, length))):
                return
            continue

        _place(clue, clue_idx + 1, next_pos, length, known, candidate_so_far, results)

        # Optimization: if we just skipped past a FILLED known cell,
        # we can't start the run any later (we'd leave it unfilled)
        if start < length and known[start] == FILLED:
            break


def _compatible(candidate: List[int], known: List[int]) -> bool:
    """Check full-line compatibility."""
    for c, k in zip(candidate, known):
        if k != UNKNOWN and c != k:
            return False
    return True


def _segment_compatible(segment: List[int], known: List[int], offset: int) -> bool:
    """Check segment compatibility at *offset*."""
    for i, val in enumerate(segment):
        k = known[offset + i]
        if k != UNKNOWN and val != k:
            return False
    return True


def line_solve(row_clues: ClueList, col_clues: ClueList) -> Optional[Grid]:
    """Solve a nonogram using pure line logic (no guessing).

    Returns the solved grid if fully determined, or None if the puzzle
    cannot be solved by line logic alone (i.e. it gets stuck with
    UNKNOWN cells remaining).
    """
    rows = len(row_clues)
    cols = len(col_clues)
    grid = [[UNKNOWN] * cols for _ in range(rows)]

    changed = True
    while changed:
        changed = False

        # Process rows
        for r in range(rows):
            known = grid[r]
            if UNKNOWN not in known:
                continue
            placements = _valid_placements(row_clues[r], cols, known)
            if not placements:
                return None  # Contradiction
            for c in range(cols):
                if known[c] != UNKNOWN:
                    continue
                vals = {p[c] for p in placements}
                if len(vals) == 1:
                    grid[r][c] = vals.pop()
                    changed = True

        # Process columns
        for c in range(cols):
            known = [grid[r][c] for r in range(rows)]
            if UNKNOWN not in known:
                continue
            placements = _valid_placements(col_clues[c], rows, known)
            if not placements:
                return None  # Contradiction
            for r in range(rows):
                if known[r] != UNKNOWN:
                    continue
                vals = {p[r] for p in placements}
                if len(vals) == 1:
                    grid[r][c] = vals.pop()
                    changed = True

    # Check if fully solved
    for r in range(rows):
        if UNKNOWN in grid[r]:
            return None  # Stuck — not line-solvable

    return grid


def backtrack_solve(
    row_clues: ClueList,
    col_clues: ClueList,
    max_solutions: int = 2,
) -> List[Grid]:
    """Solve a nonogram via backtracking, returning up to *max_solutions*.

    Useful for uniqueness checking: if len(result) == 1, the puzzle is
    unique. Capped at *max_solutions* to avoid exhaustive enumeration.
    """
    rows = len(row_clues)
    cols = len(col_clues)

    # Pre-compute valid row placements (unconstrained) for pruning
    row_options = []
    for r in range(rows):
        opts = _valid_placements(row_clues[r], cols, [UNKNOWN] * cols)
        if not opts:
            return []
        row_options.append(opts)

    solutions: List[Grid] = []
    _backtrack(row_clues, col_clues, row_options, 0, rows, cols, [], solutions, max_solutions)
    return solutions


def _backtrack(
    row_clues: ClueList,
    col_clues: ClueList,
    row_options: List[List[List[int]]],
    row_idx: int,
    rows: int,
    cols: int,
    partial: List[List[int]],
    solutions: List[Grid],
    max_solutions: int,
) -> None:
    """Recursively build grid row-by-row, pruning via column constraints."""
    if len(solutions) >= max_solutions:
        return

    if row_idx == rows:
        # All rows placed — verify column constraints
        grid = [list(row) for row in partial]
        for c in range(cols):
            col_data = [grid[r][c] for r in range(rows)]
            if _runs_of(col_data) != col_clues[c] and not (
                not _runs_of(col_data) and col_clues[c] == [0]
            ):
                return
        solutions.append(grid)
        return

    for candidate_row in row_options[row_idx]:
        # Partial column check: verify columns are still feasible
        if not _columns_feasible(partial, candidate_row, row_idx, rows, col_clues, cols):
            continue
        partial.append(candidate_row)
        _backtrack(row_clues, col_clues, row_options, row_idx + 1, rows, cols,
                   partial, solutions, max_solutions)
        partial.pop()
        if len(solutions) >= max_solutions:
            return


def _columns_feasible(
    partial: List[List[int]],
    new_row: List[int],
    row_idx: int,
    total_rows: int,
    col_clues: ClueList,
    cols: int,
) -> bool:
    """Quick check: can column clues still be satisfied after adding *new_row*?"""
    for c in range(cols):
        col_so_far = [partial[r][c] for r in range(len(partial))] + [new_row[c]]
        runs_so_far = _runs_of(col_so_far)
        expected = col_clues[c]
        remaining_rows = total_rows - row_idx - 1

        # Check: current runs don't already exceed expected
        if expected == [0]:
            # Column should be all empty
            if any(v == FILLED for v in col_so_far):
                return False
            continue

        # If current last cell is filled and within a run, the current run
        # could still grow — compare completed runs only
        if col_so_far[-1] == FILLED:
            # The last run is still open
            completed = runs_so_far[:-1]
            open_run = runs_so_far[-1] if runs_so_far else 0
        else:
            completed = runs_so_far
            open_run = 0

        # Too many completed runs already?
        if len(completed) > len(expected):
            return False

        # Any completed run exceeds corresponding expected run?
        for i, run in enumerate(completed):
            if i >= len(expected) or run != expected[i]:
                return False

        # Open run already too long?
        open_idx = len(completed)
        if open_run > 0:
            if open_idx >= len(expected):
                return False
            if open_run > expected[open_idx]:
                return False

        # Enough room for remaining runs?
        runs_left = expected[open_idx:]
        if open_run > 0:
            runs_left = [runs_left[0] - open_run] + list(runs_left[1:]) if runs_left else []
        min_space_needed = sum(max(0, r) for r in runs_left) + max(0, len(runs_left) - 1)
        if open_run > 0 and runs_left and runs_left[0] > 0:
            pass  # no gap needed before continuation of open run
        elif open_run > 0 and runs_left and runs_left[0] <= 0:
            # The open run consumed this expected run — need gap before next
            runs_left = list(runs_left[1:])
            min_space_needed = sum(max(0, r) for r in runs_left) + max(0, len(runs_left) - 1)
            if col_so_far[-1] == FILLED and runs_left:
                min_space_needed += 1  # gap after current run

        if min_space_needed > remaining_rows:
            return False

    return True


def is_line_solvable(row_clues: ClueList, col_clues: ClueList) -> bool:
    """Return True if the puzzle can be fully solved by line logic alone."""
    return line_solve(row_clues, col_clues) is not None

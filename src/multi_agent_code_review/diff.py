"""Parse unified diffs to learn which lines a change actually touched.

Used by the "drop findings outside the diff" filter and, later, by the
orchestration layer's diff parser. We rely on the `unidiff` library rather
than hand-rolling hunk parsing: unified-diff edge cases (new files, multiple
hunks, deletions, line-count arithmetic) are easy to get subtly wrong.
"""

from unidiff import PatchSet


def added_lines_by_file(diff: str) -> dict[str, set[int]]:
    """Map each file in the diff to the set of line numbers it adds.

    Line numbers are positions in the new (post-change) file. Only added
    lines are included; context and removed lines are not, because the
    specialists review the code a change introduces.
    """
    touched: dict[str, set[int]] = {}
    for patched_file in PatchSet(diff):
        added = {
            line.target_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_added and line.target_line_no is not None
        }
        if added:
            touched[patched_file.path] = added
    return touched
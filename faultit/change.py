import dataclasses
from collections import defaultdict
from itertools import chain
from typing import Dict, Iterable, List

import pygit2

from .blame import get_blame_per_line
from .hunk_utils import get_hunk_new_lines, get_hunk_old_lines
from .match_lines import match_lines


@dataclasses.dataclass(frozen=True)
class Change:
    filename: str
    commit: str
    old_start: int
    old_lines: List[bytes]
    new_start: int
    new_lines: List[bytes]
    mode: int


def _split_hunk_to_changes(
    hunk: pygit2.DiffHunk, filename: str, blame_map: Dict[int, str], mode: int
) -> Iterable[Change]:
    old_lines = get_hunk_old_lines(hunk)
    new_lines = get_hunk_new_lines(hunk)

    line_match = match_lines(old_lines, new_lines)

    old_start = hunk.old_start - 1
    new_start = hunk.new_start - 1

    return (
        Change(
            filename=filename,
            commit=blame_map[old_start + old_line_indices[0]],
            old_start=old_start + old_line_indices[0],
            old_lines=old_lines[old_line_indices[0] : old_line_indices[-1] + 1],
            new_start=new_start + (new_line_indices[0] if new_line_indices else 0),
            new_lines=new_lines[new_line_indices[0] : new_line_indices[-1] + 1]
            if new_line_indices
            else [],
            mode=mode,
        )
        for old_line_indices, new_line_indices in line_match.items()
    )


def split_patch_to_changes(patch: pygit2.Patch) -> Iterable[Change]:
    filename = patch.delta.old_file.path
    mode = patch.delta.old_file.mode
    blame_map = get_blame_per_line(filename)

    return chain(
        *[
            _split_hunk_to_changes(hunk, filename, blame_map, mode)
            for hunk in patch.hunks
        ]
    )


def group_changes_by_commit(changes: Iterable[Change]) -> Dict[str, List[Change]]:
    grouped: Dict[str, List[Change]] = defaultdict(lambda: list())
    for change in changes:
        grouped[change.commit].append(change)

    return grouped

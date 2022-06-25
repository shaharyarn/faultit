import dataclasses
from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

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
    new_start_inner: int
    new_lines: List[bytes]
    mode: int


def get_change_offset(change: Change) -> Tuple[int, int]:
    return (
        change.old_start if change.old_lines else change.new_start,
        change.new_start if change.old_lines else change.new_start_inner,
    )


def _split_hunk_to_changes(
    hunk: pygit2.DiffHunk,
    filename: str,
    blame_map: Dict[int, str],
    removed_lines_map: Dict[int, bytes],
    mode: int,
) -> Iterable[Change]:
    old_lines = get_hunk_old_lines(hunk)
    new_lines = get_hunk_new_lines(hunk)

    old_start = hunk.old_start - 1
    new_start = hunk.new_start - 1

    line_match, external_line_match = match_lines(
        old_lines, new_lines, removed_lines_map
    )

    scope_changes = (
        Change(
            filename=filename,
            commit=blame_map[
                old_start + old_line_indices[0] if old_line_indices else 0
            ],
            old_start=old_start + (old_line_indices[0] if old_line_indices else 0),
            old_lines=old_lines[old_line_indices[0] : old_line_indices[-1] + 1]
            if old_line_indices
            else [],
            new_start=new_start + (new_line_indices[0] if new_line_indices else 0),
            new_start_inner=0,
            new_lines=new_lines[new_line_indices[0] : new_line_indices[-1] + 1]
            if new_line_indices
            else [],
            mode=mode,
        )
        for old_line_indices, new_line_indices in line_match.items()
        if old_line_indices or new_line_indices
    )

    external_changes = (
        Change(
            filename=filename,
            commit=blame_map[old_line_index],
            old_start=old_line_index,
            old_lines=[],
            new_start=new_start,
            new_start_inner=new_line_index,
            new_lines=[new_line],
            mode=mode,
        )
        for old_line_index, old_line, new_line_index, new_line in external_line_match
    )

    return chain(scope_changes, external_changes)


def map_removed_lines(patch: pygit2.Patch) -> Dict[int, bytes]:
    map: Dict[int, bytes] = {}
    for hunk in patch.hunks:
        old_lines = get_hunk_old_lines(hunk)
        for index, line in enumerate(old_lines):
            map[hunk.old_start + index - 1] = line

    return map


def split_patch_to_changes(
    patch: pygit2.Patch, repo: pygit2.Repository
) -> Iterable[Change]:
    filename = patch.delta.old_file.path
    mode = patch.delta.old_file.mode
    blame_map = get_blame_per_line(filename, Path(repo.path).parent)
    removed_lines_map = map_removed_lines(patch)

    return chain(
        *[
            _split_hunk_to_changes(hunk, filename, blame_map, removed_lines_map, mode)
            for hunk in patch.hunks
        ]
    )


def group_changes_by_commit(changes: Iterable[Change]) -> Dict[str, List[Change]]:
    grouped: Dict[str, List[Change]] = defaultdict(lambda: list())
    for change in changes:
        grouped[change.commit].append(change)

    return grouped

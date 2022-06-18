from typing import Dict, List, Tuple

from .change import Change

Offsets = Dict[Tuple[int, int], int]


def apply_change_on_lines(
    change: Change, lines: List[bytes], offsets: Offsets
) -> List[bytes]:
    lines = lines[:]

    change_offset = (change.old_start, change.new_start)
    old_start = change.old_start

    for pos, offset in offsets.items():
        if max((pos, change_offset)) == change_offset:
            old_start += offset

    for _ in range(len(change.old_lines)):
        lines.pop(old_start)

    for line in reversed(change.new_lines):
        lines.insert(old_start, line)

    return lines

from typing import Dict, List, Tuple

from .change import Change, get_change_offset

Offsets = Dict[Tuple[int, int], int]


def apply_change_on_lines(
    change: Change, lines: List[bytes], offsets: Offsets
) -> List[bytes]:
    lines = lines[:]

    change_offset = get_change_offset(change)
    curr_offset = 0

    for pos, offset in offsets.items():
        if max((pos, change_offset)) == change_offset:
            curr_offset += offset

    old_start = change.old_start + curr_offset
    new_start = change.new_start + curr_offset

    for _ in range(len(change.old_lines)):
        lines.pop(old_start)

    for line in reversed(change.new_lines):
        lines.insert(old_start if change.old_lines else new_start, line)

    return lines

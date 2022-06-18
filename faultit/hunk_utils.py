from typing import List

import pygit2


def get_hunk_new_lines(hunk: pygit2.DiffHunk) -> List[bytes]:
    return [line.raw_content for line in hunk.lines if line.origin == "+"]


def get_hunk_old_lines(hunk: pygit2.DiffHunk) -> List[bytes]:
    return [line.raw_content for line in hunk.lines if line.origin == "-"]

import re
from subprocess import PIPE, Popen
from typing import Dict


def get_blame_per_line(filename: str) -> Dict[int, str]:
    blame_re = re.compile(rb"^(?P<commit>[0-9a-f]{40}) (\d+) (?P<lineno>\d+).*")
    blame_proc = Popen(["git", "blame", "--porcelain", "HEAD", filename], stdout=PIPE)
    assert blame_proc.stdout

    blame_map = {}
    for line in blame_proc.stdout:
        m = blame_re.match(line)
        if not m:
            continue

        commit = m.group("commit").decode("ascii")
        lineno = int(m.group("lineno"))
        blame_map[lineno - 1] = commit  # Make it 0 based

    return blame_map

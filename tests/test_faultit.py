import os
import tempfile
import time
from pathlib import Path
from textwrap import dedent
from typing import Dict, List

import pytest
from pygit2 import GIT_FILEMODE_BLOB, IndexEntry, Repository, Signature

from faultit.blame import get_blame_per_line
from faultit.main import run_faultit

TEST_FILE = "testfile"


@pytest.fixture
def temp_repo() -> Repository:
    with tempfile.TemporaryDirectory() as td:
        os.popen(
            f"cd {td} && git init && touch temp && git add temp && git commit -m init"
        )
        time.sleep(
            1
        )  # Need to wait for git init - subproccess.Popen does not circumvent this.
        yield Repository(td)


def commit_file_by_line(text: str, repo: Repository, filename: str = TEST_FILE) -> None:
    lines: List[bytes] = []
    signature = Signature("test", "test")
    split_lines = text.split("\n")
    for index, line in enumerate(split_lines):
        lines.append((line + ("\n" if index != len(split_lines) - 1 else "")).encode())
        ie = IndexEntry(
            filename,
            repo.create_blob(b"".join(lines)),
            GIT_FILEMODE_BLOB,
        )
        repo.index.add(ie)

        repo.index.write()
        tree = repo.index.write_tree()
        head = repo.head.peel()

        commit_message = str(index)
        repo.create_commit(
            "HEAD", signature, signature, commit_message, tree, [head.id]
        )

    write_to_file(text, repo, filename)


def write_to_file(text: str, repo: Repository, filename: str = TEST_FILE) -> None:
    with open((Path(repo.path).parent / filename), "w") as f:
        f.write(text)


def get_test_file_blame(repo: Repository, filename: str = TEST_FILE) -> Dict[int, int]:
    blame_map = get_blame_per_line(filename, Path(repo.path).parent)
    return {
        line: int(repo.get(commit).message.split("\n", 1)[0])
        for line, commit in blame_map.items()
    }


def test_example(temp_repo: Repository) -> None:
    commit_file_by_line("hey\nthere\ngeneral kenobi", temp_repo)
    write_to_file("hey\nthere\nnew general\n kenobi", temp_repo)
    run_faultit(Path(temp_repo.path).parent)
    assert get_test_file_blame(temp_repo) == {0: 0, 1: 1, 2: 2, 3: 2}


def test_black_simple_use(temp_repo: Repository) -> None:
    commit_file_by_line(
        dedent(
            """
    def some_func(self, arg):
        assert SomeClass.__name__ in obj.clients, \\
            '{} is adding itself to {} clients.' \\
                 .format(self.__class__.__name__, SomeClass.__name__)
        obj.property = self.property
        obj.long_property_name = self.long_property_name
        obj.clients[
            self.__class__.__name__
        ] = self

        obj.prop_dic.setdefault(self.SOME_LONG_NAME_CONST,
                                SOME_LONG_NAME_CONST_DEFAULT)
    """
        ).strip(),
        temp_repo,
    )
    write_to_file(
        dedent(
            """
    def some_func(self, args):
        assert (
            SomeClass.__name__ in obj.clients
        ), "{} is adding itself to {} clients.".format(
            self.__class__.__name__, SomeClass.__name__
        )
        obj.property = self.property
        obj.long_property_name = self.long_property_name
        obj.clients[self.__class__.__name__] = self

        obj.prop_dic.setdefault(self.SOME_LONG_CONST_NAME, SOME_LONG_CONST_NAME_DEFAULT)
    """
        ).strip(),
        temp_repo,
    )

    run_faultit(Path(temp_repo.path).parent)
    assert get_test_file_blame(temp_repo) == {
        0: 0,
        1: 1,
        2: 1,
        3: 2,
        4: 3,
        5: 3,
        6: 4,
        7: 5,
        8: 7,
        9: 9,
        10: 10,
    }

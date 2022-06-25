from collections import defaultdict
from io import BytesIO
from itertools import chain
from pathlib import Path
from textwrap import dedent
from typing import Dict, Generator, Iterable, List

import click
import pygit2

from .apply import Offsets, apply_change_on_lines
from .change import (
    Change,
    get_change_offset,
    group_changes_by_commit,
    split_patch_to_changes,
)


def filter_patches(
    patches: Iterable[pygit2.Patch],
) -> Generator[pygit2.Patch, None, None]:
    for patch in patches:
        if not patch.delta.status == pygit2.GIT_DELTA_MODIFIED:
            continue

        yield patch


def get_unmodified_lines(filename: str, repo: pygit2.Repository) -> List[bytes]:
    head: pygit2.Commit = repo.head.peel()
    file_obj = head.tree
    for path_part in filename.split("/"):
        file_obj = file_obj / path_part

    return BytesIO(file_obj.data).readlines()


def create_commit_from_commit(
    index_entries: List[pygit2.IndexEntry],
    commit_id: str,
    signature: pygit2.Signature,
    repo: pygit2.Repository,
) -> None:
    for index_entry in index_entries:
        repo.index.add(index_entry)

    repo.index.write()
    tree = repo.index.write_tree()
    head = repo.head.peel()

    commit = repo.get(commit_id)
    commit_message = dedent(
        f"""
    {commit.message}\n\nAutomatic commit by faultit, original commit:\n{commit.hex}
    """
    ).strip()
    repo.create_commit(
        "HEAD", commit.author, signature, commit_message, tree, [head.id]
    )


def commit_changes(
    grouped_changes: Dict[str, List[Change]],
    repo: pygit2.Repository,
    signature: pygit2.Signature,
) -> None:

    filename_to_offsets: Dict[str, Offsets] = defaultdict(
        lambda: defaultdict(lambda: 0)
    )
    filename_to_lines = {
        filename: get_unmodified_lines(filename, repo)
        for filename in {
            change.filename
            for changes in grouped_changes.values()
            for change in changes
        }
    }
    filename_to_modes = {
        change.filename: change.mode
        for changes in grouped_changes.values()
        for change in changes
    }

    for commit_id, changes in grouped_changes.items():
        if not changes:
            continue

        for change in changes:
            new_lines = apply_change_on_lines(
                change,
                filename_to_lines[change.filename],
                filename_to_offsets[change.filename],
            )

            change_offset = get_change_offset(change)
            filename_to_offsets[change.filename][change_offset] += len(
                change.new_lines
            ) - len(change.old_lines)

            filename_to_lines[change.filename] = new_lines

        index_entries = [
            pygit2.IndexEntry(
                filename,
                repo.create_blob(b"".join(new_lines)),
                filename_to_modes[filename],
            )
            for filename, new_lines in filename_to_lines.items()
        ]

        create_commit_from_commit(index_entries, commit_id, signature, repo)


def run_faultit(dir: Path) -> None:
    repo = pygit2.Repository(dir)
    diff: pygit2.Diff = repo.diff(
        context_lines=0, flags=pygit2.GIT_DIFF_IGNORE_SUBMODULES
    )
    patches = filter_patches(diff)
    grouped = group_changes_by_commit(
        chain(*[split_patch_to_changes(patch, repo) for patch in patches])
    )

    commit_changes(grouped, repo, pygit2.Signature("faultit", "faultit@faultit.com"))


@click.command()
def main() -> None:
    run_faultit(Path("."))


if __name__ == "__main__":
    main()

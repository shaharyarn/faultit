from typing import Dict, List, Tuple


def _get_words(data: bytes) -> List[bytes]:
    words = (
        data.replace(b", ", b"")
        .replace(b"\n", b"")
        .replace(b"(", b" ")
        .replace(b")", b" ")
        .replace(b"[", b" ")
        .replace(b"]", b" ")
        .replace(b"'", b'"')
        .split(b" ")
    )

    return [word for word in words if word]


def _get_similarity_score(first: bytes, second: bytes) -> int:
    first_words = set(_get_words(first))
    second_words = set(_get_words(second))

    if len(first_words) == 0 and len(second_words) == 0:
        return 100

    return sum(len(word) for word in first_words.intersection(second_words))


def match_lines(
    old_lines: List[bytes], new_lines: List[bytes], all_removed_lines: Dict[int, bytes]
) -> Tuple[Dict[Tuple[int, ...], Tuple[int, ...]], List[Tuple[int, bytes, int, bytes]]]:
    matching: Dict[int, int] = {}
    external_matching: List[Tuple[int, bytes, int, bytes]] = []
    from_line_index = 0

    # match new line to old line
    for index, new_line in enumerate(new_lines):
        match = find_match_in_dict(
            {
                old_line_index: old_line
                for old_line_index, old_line in list(enumerate(old_lines))[
                    from_line_index:
                ]
            },
            new_line,
            index,
            all_removed_lines,
        )
        matching[index] = match[0]
        if match[1]:
            from_line_index = match[0]
        else:
            external_matching.append(
                (match[0], all_removed_lines[match[0]], index, new_line)
            )

    line_matching: Dict[Tuple[int, ...], Tuple[int, ...]] = {}
    for i in range(from_line_index):
        line_matching[(i,)] = tuple(
            (key for key, value in matching.items() if value == i)
        )

    line_matching[tuple(range(from_line_index, len(old_lines)))] = tuple(
        (key for key, value in matching.items() if value == from_line_index)
    )
    return line_matching, external_matching


def find_match_in_dict(
    index_to_line: Dict[int, bytes],
    line: bytes,
    line_index: int,
    other_lines: Dict[int, bytes],
) -> Tuple[int, bool]:

    if index_to_line:
        best_line = max(
            [
                (index, _get_similarity_score(indexed_line, line), True)
                for index, indexed_line in index_to_line.items()
            ],
            key=lambda x: (x[1], -abs(x[0] - line_index)),
        )
        if best_line[0] <= 0:
            best_line = max(
                [best_line]
                + [
                    (index, _get_similarity_score(indexed_line, line) - 5, False)
                    for index, indexed_line in other_lines.items()
                ],
                key=lambda x: (x[1], -abs(x[0] - line_index)),
            )
    else:
        best_line = max(
            [
                (index, _get_similarity_score(indexed_line, line) - 5, False)
                for index, indexed_line in other_lines.items()
            ],
            key=lambda x: (x[1], -abs(x[0] - line_index)),
        )
    return best_line[0], best_line[2]

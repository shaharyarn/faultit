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
    matching, from_line_index, external_matching = _generate_matching(
        old_lines, new_lines, all_removed_lines
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


def _generate_matching(
    old_lines: List[bytes], new_lines: List[bytes], all_removed_lines: Dict[int, bytes]
) -> Tuple[Dict[int, int], int, List[Tuple[int, bytes, int, bytes]]]:
    matching: Dict[int, int] = {}
    external_matching: List[Tuple[int, bytes, int, bytes]] = []
    from_line_index = 0

    for index, new_line in enumerate(new_lines):
        match = _find_match(
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

    return matching, from_line_index, external_matching


def _get_best_match_index(
    line: bytes,
    line_index: int,
    index_to_line: Dict[int, bytes],
) -> Tuple[int, int]:
    return max(
        [
            (index, _get_similarity_score(indexed_line, line))
            for index, indexed_line in index_to_line.items()
        ],
        key=lambda x: (x[1], -abs(x[0] - line_index)),
    )


def _find_match(
    index_to_line: Dict[int, bytes],
    line: bytes,
    line_index: int,
    other_lines: Dict[int, bytes],
) -> Tuple[int, bool]:
    best_match_in_removed = _get_best_match_index(line, line_index, other_lines)

    if not index_to_line:
        return best_match_in_removed[0], False

    best_match_in_curr = _get_best_match_index(line, line_index, index_to_line)

    if best_match_in_curr[1] <= best_match_in_removed[1] - 5:
        return best_match_in_removed[0], False

    return best_match_in_curr[0], True

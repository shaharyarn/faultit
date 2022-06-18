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
    old_lines: List[bytes], new_lines: List[bytes]
) -> Dict[Tuple[int, ...], Tuple[int, ...]]:
    matching: Dict[int, int] = {}
    from_line_index = 0

    # match new line to old line
    for index, new_line in enumerate(new_lines):
        match = max(
            list(
                enumerate(
                    _get_similarity_score(old_line, new_line) for old_line in old_lines
                )
            )[from_line_index:],
            key=lambda x: (x[1], -abs(x[0] - index)),
        )[0]
        matching[index] = match
        from_line_index = match

    line_matching: Dict[Tuple[int, ...], Tuple[int, ...]] = {}
    for i in range(from_line_index):
        line_matching[(i,)] = tuple(
            (key for key, value in matching.items() if value == i)
        )

    line_matching[tuple(range(from_line_index, len(old_lines)))] = tuple(
        (key for key, value in matching.items() if value == from_line_index)
    )

    return line_matching

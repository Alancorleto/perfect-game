import re
import unicodedata

SIMILARITY_SCORE_THRESHOLD = 0.55


def check_string_similarity(left: str, right: str) -> bool:
    left = _normalize_search_text(left)
    right = _normalize_search_text(right)
    return _string_similarity(left, right) >= SIMILARITY_SCORE_THRESHOLD


def _string_similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0

    if left in right or right in left:
        return 1.0

    max_length = max(len(left), len(right))
    distance = _levenshtein_distance(left, right)
    return max(0.0, 1.0 - (distance / max_length))


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    if len(left) < len(right):
        left, right = right, left

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insertion_cost = previous_row[right_index] + 1
            deletion_cost = current_row[right_index - 1] + 1
            substitution_cost = previous_row[right_index - 1]
            if left_char != right_char:
                substitution_cost += 1

            current_row.append(min(insertion_cost, deletion_cost, substitution_cost))
        previous_row = current_row

    return previous_row[-1]


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()

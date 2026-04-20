import re
from typing import Tuple, Optional
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Replace non-breaking spaces and weird whitespace
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    # Remove quotes
    text = re.sub(r"[\"'`]", "", text)

    # Remove punctuation (keep alphanumeric + space)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Normalize spaces again
    text = re.sub(r"\s+", " ", text).strip()

    return text


def singularize(word: str) -> str:
    """
    Very simple singularization heuristic.
    Good enough for cases like dollar(s), bank(s), etc.
    """
    if len(word) > 3:
        if word.endswith("ies"):
            return word[:-3] + "y"
        elif word.endswith("s") and not word.endswith("ss"):
            return word[:-1]
    return word


def normalize_tokens(text: str):
    tokens = text.split()
    return [singularize(t) for t in tokens]


def fuzzy_contains(value: str, chunk: str, threshold: float = 0.85) -> bool:
    """
    Fallback fuzzy matching
    """
    ratio = SequenceMatcher(None, value, chunk).ratio()
    return ratio >= threshold


def find_text_in_chunk(
    value: str,
    chunk: str,
    use_fuzzy: bool = True,
    fuzzy_threshold: float = 0.85
) -> Tuple[bool, Optional[str]]:
    """
    Returns:
        (found: bool, reason: str for debugging)
    """

    if not value or not chunk:
        return False, "Empty input"

    # Step 1: Normalize
    norm_value = normalize_text(value)
    norm_chunk = normalize_text(chunk)

    # Step 2: Direct substring match
    if norm_value in norm_chunk:
        return True, "Direct match after normalization"

    # Step 3: Token-based match (handles plural etc.)
    value_tokens = normalize_tokens(norm_value)
    chunk_tokens = normalize_tokens(norm_chunk)

    for vt in value_tokens:
        for ct in chunk_tokens:
            if vt == ct:
                return True, f"Token match: {vt}"

            # partial match (handles dollar vs dollars)
            if vt in ct or ct in vt:
                return True, f"Partial token match: {vt} ~ {ct}"

    # Step 4: Sliding window match (multi-word phrases)
    chunk_joined = " ".join(chunk_tokens)
    value_joined = " ".join(value_tokens)

    if value_joined in chunk_joined:
        return True, "Phrase match after token normalization"

    # Step 5: Fuzzy fallback
    if use_fuzzy:
        if fuzzy_contains(value_joined, chunk_joined, fuzzy_threshold):
            return True, "Fuzzy match"

    return False, "No match"

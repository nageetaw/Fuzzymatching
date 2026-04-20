@staticmethod
def _find_text_in_chunk(
    chunk: Chunk,
    extracted_string: str,
    allowed_errors: int = 0,
    allow_multimatch: bool = False,
) -> Chunk:
    """
    Finds and returns a Chunk object containing text that matches the given 
    extracted string within a chunk.
    
    Improvements over previous version:
    - Searches ALL cells including table cells
    - Handles singular/plural (trailing 's' or 'es')
    - Handles surrounding punctuation (quotes, brackets, colons)
    - Handles extra whitespace
    - Falls back with progressively relaxed matching
    """
    if (
        chunk.cells is None
        or extracted_string is None
        or not isinstance(extracted_string, str)
        or not extracted_string.strip()
    ):
        return None

    extracted_string = extracted_string.strip().lower()

    # --- Helper to build a chunk from matched cell indices ---
    def build_chunk_from_cells(cells, flat_idx, start, end):
        new_chunk_cells = []
        for cell_id in range(flat_idx[start], flat_idx[end - 1] + 1):
            cell = cells[cell_id]
            new_chunk_cells.append(cell.copy())
        return Chunk(new_chunk_cells, chunk.type, chunk.label)

    # --- Helper to search a given set of cells ---
    def search_in_cells(cells, pattern, allowed_errors, allow_multimatch):
        if not cells:
            return None

        flat_text = ''.join([x.text for x in cells]).lower()
        flat_idx = [i] * len(x.text) for i, x in enumerate(cells)]

        try:
            flat_idx = np.concatenate(flat_idx)

            # Remove spaces from both
            non_spaces = [m.start() for m in re.finditer(r'[^\s]', flat_text)]
            flat_text_nospace = re.sub(r'\s', '', flat_text)
            flat_idx = flat_idx[non_spaces]

            assert len(flat_idx) == len(flat_text_nospace)

        except Exception as exp:
            logger.error(
                f'Error searching in _find_text_in_chunk: {exp}',
                exc_info=True
            )
            raise

        search_pattern = re.sub(r'\s', '', pattern)
        search_pattern = re.escape(search_pattern)

        # Allow surrounding punctuation: quotes, brackets, colons
        search_pattern = (
            r'["\'\(\)\[\]\:]*'
            + search_pattern
            + r'(?:e?s)?'          # plural: optional trailing 's' or 'es'
            + r'["\'\(\)\[\]\:]*'  # trailing punctuation
        )

        if allowed_errors > 0:
            search_pattern = f'(?:{search_pattern}){{e<={allowed_errors}}}'

        matches = list(re.finditer(search_pattern, flat_text_nospace))

        if len(matches) > 1 and not allow_multimatch:
            return None

        for m in matches:
            start, end = m.start(), m.end()
            if start < end:
                return build_chunk_from_cells(cells, flat_idx, start, end)

        return None

    # ----------------------------------------------------------------
    # Strategy 1: search text cells only (preferred, tighter bboxes)
    # ----------------------------------------------------------------
    text_cells = [x for x in chunk.cells if x.type == 'text']
    table_cells = [x for x in chunk.cells if x.type != 'text']
    all_cells = chunk.cells

    max_errors = int(round(len(extracted_string) * 0.1))
    max_errors = min(max_errors, 5)

    for allowed_err in range(max_errors + 1):
        result = search_in_cells(
            text_cells, extracted_string, allowed_err, allow_multimatch
        )
        if result is not None:
            return result

    # ----------------------------------------------------------------
    # Strategy 2: search table cells (handles your MUFG BANK case)
    # ----------------------------------------------------------------
    for allowed_err in range(max_errors + 1):
        result = search_in_cells(
            table_cells, extracted_string, allowed_err, allow_multimatch
        )
        if result is not None:
            return result

    # ----------------------------------------------------------------
    # Strategy 3: search all cells together as last resort
    # ----------------------------------------------------------------
    for allowed_err in range(max_errors + 1):
        result = search_in_cells(
            all_cells, extracted_string, allowed_err, allow_multimatch
        )
        if result is not None:
            return result

    return None

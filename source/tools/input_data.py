from source.config import INPUT_DATA_DIR, MAX_FILE_SIZE
from source.tools.common import ensure_inside, truncate

from agents.decorators import tool


@tool
def list_input_files(relative_path: str = ".") -> str:
    """
    List files or directories inside the experimental dataset.
    """
    target = ensure_inside(INPUT_DATA_DIR / relative_path, INPUT_DATA_DIR)

    if not target.exists():
        return f"Path does not exist: {relative_path}"

    if target.is_file():
        return str(target.relative_to(INPUT_DATA_DIR))

    entries = []

    for p in sorted(target.iterdir()):
        suffix = "/" if p.is_dir() else ""
        entries.append(str(p.relative_to(INPUT_DATA_DIR)) + suffix)

    return "\n".join(entries)


@tool
def inspect_input_file(relative_path: str) -> str:
    """
    Inspect an input file without loading its full contents.

    Returns path, size, extension, and whether it is likely too large
    for direct reading. Large files should normally be parsed or streamed
    locally using an analysis script.
    """
    target = ensure_inside(
        INPUT_DATA_DIR / relative_path,
        INPUT_DATA_DIR,
    )

    if not target.exists():
        return f"File does not exist: {relative_path}"

    if not target.is_file():
        return f"Not a file: {relative_path}"

    size = target.stat().st_size

    units = ["B", "KB", "MB", "GB", "TB"]
    human = float(size)

    for unit in units:
        if human < 1024 or unit == units[-1]:
            human_size = f"{human:.2f} {unit}"
            break
        human /= 1024

    suffix = target.suffix.lower() or "(none)"

    return "\n".join([
        f"FILE: {relative_path}",
        f"SIZE_BYTES: {size}",
        f"SIZE: {human_size}",
        f"EXTENSION: {suffix}",
        (
            "RECOMMENDATION: inspect only; process locally with an "
            "analysis script rather than transferring the full file."
            if size > 10_000_000
            else "RECOMMENDATION: direct inspection is reasonable."
        ),
    ])


@tool
def read_input_file_chunk(
    relative_path: str,
    offset: int = 0,
    max_chars: int = 20_000,
) -> str:
    """
    Read a character window from a text-like input file.

    Intended for structural inspection of large files, not for complete
    quantitative analysis. Large datasets should be parsed or streamed
    locally using analysis scripts.
    """
    target = ensure_inside(
        INPUT_DATA_DIR / relative_path,
        INPUT_DATA_DIR,
    )

    if not target.exists():
        return f"File does not exist: {relative_path}"

    if not target.is_file():
        return f"Not a file: {relative_path}"

    offset = max(0, int(offset))
    max_chars = min(max(int(max_chars), 1000), MAX_FILE_SIZE)

    try:
        with target.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            handle.seek(offset)
            text = handle.read(max_chars)
    except Exception as exc:
        return f"Could not read {relative_path}: {exc}"

    return "\n".join([
        f"[FILE: {relative_path}]",
        f"[OFFSET: {offset}]",
        f"[CHARS RETURNED: {len(text)}]",
        "",
        text,
    ])


@tool
def read_input_file(
    relative_path: str,
    max_chars: int = 100_000,
) -> str:
    """
    Read the beginning of a text-like input file.

    This tool is intended for small files and structural inspection.
    Large files are not loaded fully into memory. For large datasets,
    use inspect_input_file() and process them with analysis scripts.
    """
    target = ensure_inside(
        INPUT_DATA_DIR / relative_path,
        INPUT_DATA_DIR,
    )

    if not target.exists():
        return f"File does not exist: {relative_path}"

    if not target.is_file():
        return f"Not a file: {relative_path}"

    max_chars = min(max(max_chars, 1000), MAX_FILE_SIZE)

    try:
        with target.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            text = handle.read(max_chars + 1)
    except Exception as exc:
        return f"Could not read {relative_path}: {exc}"

    if len(text) > max_chars:
        return (
            text[:max_chars]
            + f"\n\n[FILE TRUNCATED at {max_chars} characters]"
        )

    return text


@tool
def inspect_csv(
    relative_path: str,
    n_rows: int = 20
) -> str:
    """
    Inspect the header and first rows of a CSV file in the dataset.
    """
    import csv

    target = ensure_inside(
        INPUT_DATA_DIR / relative_path,
        INPUT_DATA_DIR
    )

    if not target.exists():
        return f"File does not exist: {relative_path}"

    if target.suffix.lower() != ".csv":
        return "inspect_csv only accepts CSV files."

    n_rows = max(1, min(n_rows, 100))

    rows = []

    with target.open(
        newline="",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:

        reader = csv.reader(handle)

        for i, row in enumerate(reader):
            rows.append(row)
            if i >= n_rows:
                break

    if not rows:
        return "CSV is empty."

    header = rows[0]

    output = [
        f"FILE: {relative_path}",
        f"COLUMNS ({len(header)}):",
        ", ".join(header),
        "",
        f"FIRST {len(rows)-1} DATA ROWS:",
    ]

    for row in rows[1:]:
        output.append(",".join(row))

    return truncate("\n".join(output))


@tool
def csv_column_summary(
    relative_path: str,
    column: str
) -> str:
    """
    Compute simple descriptive statistics for one numeric CSV column:
    n, missing, mean, standard deviation, minimum, quartiles,
    median and maximum.

    This is a generic descriptive tool and does not fit models.
    """
    import csv
    import math
    import statistics

    target = ensure_inside(
        INPUT_DATA_DIR / relative_path,
        INPUT_DATA_DIR
    )

    if target.suffix.lower() != ".csv":
        return "csv_column_summary only accepts CSV files."

    values = []
    missing = 0

    with target.open(
        newline="",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:

        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            return "CSV has no header."

        if column not in reader.fieldnames:
            return (
                f"Column {column!r} not found.\n"
                f"Available: {reader.fieldnames}"
            )

        for row in reader:
            raw = row.get(column, "")

            try:
                value = float(raw)
            except (TypeError, ValueError):
                missing += 1
                continue

            if math.isfinite(value):
                values.append(value)
            else:
                missing += 1

    if not values:
        return f"No finite numeric values in {column!r}."

    values.sort()

    def quantile(p):
        if len(values) == 1:
            return values[0]

        x = p * (len(values) - 1)
        lo = int(x)
        hi = min(lo + 1, len(values) - 1)
        frac = x - lo

        return (
            values[lo] * (1.0 - frac)
            + values[hi] * frac
        )

    result = {
        "file": relative_path,
        "column": column,
        "n": len(values),
        "missing_or_nonfinite": missing,
        "mean": statistics.fmean(values),
        "sd": (
            statistics.stdev(values)
            if len(values) > 1
            else 0.0
        ),
        "min": values[0],
        "q25": quantile(0.25),
        "median": quantile(0.50),
        "q75": quantile(0.75),
        "max": values[-1],
    }

    return "\n".join(
        f"{key}: {value}"
        for key, value in result.items()
    )


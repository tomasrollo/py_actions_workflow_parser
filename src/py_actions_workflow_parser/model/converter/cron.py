"""Cron expression validation and utilities."""

from __future__ import annotations

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}

_MINUTE_RANGE = (0, 59, None)
_HOUR_RANGE = (0, 23, None)
_DOM_RANGE = (1, 31, None)
_MONTH_RANGE = (1, 12, _MONTHS)
_DOW_RANGE = (0, 6, _DAYS)


def _convert_to_number(value: str, names: dict[str, int] | None) -> float:
    if names and value.lower() in names:
        return float(names[value.lower()])
    try:
        return float(value)
    except ValueError:
        return float("nan")


def _validate_part(
    value: str, range_: tuple[int, int, dict | None], allow_separators: bool = True
) -> bool:
    min_val, max_val, names = range_
    if names and value.lower() in names:
        return True
    if value == "*":
        return True

    if "," in value:
        if not allow_separators:
            return False
        return all(v and _validate_part(v, range_) for v in value.split(","))

    if "/" in value:
        if not allow_separators:
            return False
        parts = value.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False
        step_val = _convert_to_number(parts[1], None)
        if step_val != step_val or step_val <= 0:  # NaN check
            return False
        return _validate_part(parts[0], range_) and _validate_part(
            parts[1], range_, False
        )

    if "-" in value:
        if not allow_separators:
            return False
        parts = value.split("-")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False
        start_num = _convert_to_number(parts[0], names)
        end_num = _convert_to_number(parts[1], names)
        return (
            _validate_part(parts[0], range_, False)
            and _validate_part(parts[1], range_, False)
            and end_num >= start_num
        )

    try:
        num = float(value)
        return not (num != num) and min_val <= num <= max_val
    except ValueError:
        return False


def is_valid_cron(cron: str) -> bool:
    parts = cron.split()
    if len(parts) != 5:
        return False
    mins, hours, dom, months, dow = parts
    return (
        _validate_part(mins, _MINUTE_RANGE)
        and _validate_part(hours, _HOUR_RANGE)
        and _validate_part(dom, _DOM_RANGE)
        and _validate_part(months, _MONTH_RANGE)
        and _validate_part(dow, _DOW_RANGE)
    )


def _get_minute_interval(minute_part: str) -> int:
    if "/" in minute_part:
        parts = minute_part.split("/", 1)
        try:
            step = int(parts[1])
            if step > 0:
                return step
        except ValueError:
            pass

    if "," in minute_part:
        try:
            values = sorted(int(v) for v in minute_part.split(","))
            if len(values) >= 2:
                min_gap = 60
                for i in range(1, len(values)):
                    min_gap = min(min_gap, values[i] - values[i - 1])
                wrap_gap = values[0] + 60 - values[-1]
                return min(min_gap, wrap_gap)
        except ValueError:
            pass

    if "-" in minute_part and "/" not in minute_part:
        parts = minute_part.split("-")
        try:
            start, end = int(parts[0]), int(parts[1])
            if end > start:
                return 1
        except (ValueError, IndexError):
            pass

    if minute_part == "*":
        return 1

    return 60


def has_cron_interval_less_than_5_minutes(cron: str) -> bool:
    if not is_valid_cron(cron):
        return False
    minute_part = cron.split()[0]
    return _get_minute_interval(minute_part) < 5


def get_cron_description(cronspec: str) -> str | None:
    """Return a human-readable description of the cron expression, or None if invalid."""
    if not is_valid_cron(cronspec):
        return None
    try:
        from croniter import croniter  # type: ignore[import]

        # croniter doesn't provide human descriptions, so we return a minimal string
        # to satisfy callers. Full description (like cronstrue) is not needed for validation.
        return f"Runs on schedule: {cronspec}"
    except ImportError:
        return f"Runs on schedule: {cronspec}"

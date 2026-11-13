"""
Admin-editable settings.

Environment variables set the starting value of every setting. The ones listed in
EDITABLE_SETTINGS can also be overridden by admins at runtime; overrides are stored
in the platform_settings table and applied onto the global ``settings`` object at
startup and on save, so code keeps reading ``settings.X`` as usual. Everything else
(secrets, URLs, pool sizes, values read only at startup) stays environment-only.
"""

import logging
import types
from typing import Any, Literal, NamedTuple, Union, get_args, get_origin
from urllib.parse import urlsplit, urlunsplit

from annotated_types import Ge, Gt, Le, Lt
from pydantic import ValidationError

from app.core.config import Settings, settings


logger = logging.getLogger(__name__)


class Editable(NamedTuple):
    group: str
    label: str


# Settings admins can change at runtime, with how the settings page shows them
# (dict order = display order).
EDITABLE_SETTINGS: dict[str, Editable] = {
    "MATCH_SCHEDULER_ENABLED": Editable("Match scheduler", "Scheduler enabled"),
    "MATCH_SCHEDULER_INTERVAL_SECONDS": Editable("Match scheduler", "Check interval (seconds)"),
    "MATCH_SCHEDULER_SELECTION": Editable("Match scheduler", "Agent selection"),
    "MATCH_SCHEDULING_STRATEGY": Editable("Match scheduler", "Scheduling mode"),
    "MATCH_MAX_CONCURRENT_MATCHES": Editable("Match scheduler", "Matches in flight (concurrent mode)"),
    "MATCH_STALE_TIMEOUT_SECONDS": Editable("Match scheduler", "Stale match timeout (seconds)"),
    "HUMAN_MOVE_TIME_LIMIT_SECONDS": Editable("Human play", "Time per move (seconds)"),
    "HUMAN_MATCH_MAX_DURATION_SECONDS": Editable("Human play", "Max game duration (seconds)"),
    "TOURNAMENT_DEFAULT_TURN_TIME_LIMIT_SECONDS": Editable("Tournaments", "Default turn time limit (seconds)"),
    "TOURNAMENT_MAX_CONCURRENT_MATCHES": Editable("Tournaments", "Default concurrent matches"),
    "TOURNAMENT_MAX_GAME_RETRIES": Editable("Tournaments", "Retries for a failed game"),
    "MAX_TOURNAMENT_ENTRANTS": Editable("Tournaments", "Max entrants"),
    "MAX_AGENTS_PER_ARENA": Editable("Limits", "Agents per user per arena"),
    "MAX_SUBMISSIONS_PER_USER": Editable("Limits", "Submissions per user"),
    "MAX_UPLOAD_BYTES": Editable("Limits", "Upload size"),
    "MAX_HEX_BOARD_SIZE": Editable("Limits", "Hex board size"),
    "MAX_LOG_APPEND_BYTES": Editable("Limits", "Log chunk size"),
    "MAX_TOTAL_LOG_BYTES": Editable("Limits", "Total log size"),
    "MAX_RESULT_BYTES": Editable("Limits", "Match result size"),
    "MAX_GAME_STATE_BYTES": Editable("Limits", "Game state size"),
    "DISABLE_IP_RATE_LIMITING": Editable("Rate limiting", "Disable IP limits for anonymous requests"),
    "RATE_LIMIT_LOGIN": Editable("Rate limiting", "Login"),
    "RATE_LIMIT_REGISTER": Editable("Rate limiting", "Registration"),
    "RATE_LIMIT_EMAIL_TOKEN": Editable("Rate limiting", "Email verification and password reset"),
    "RATE_LIMIT_READS": Editable("Rate limiting", "Reads"),
    "RATE_LIMIT_PROFILE": Editable("Rate limiting", "Profile"),
    "RATE_LIMIT_MUTATIONS": Editable("Rate limiting", "Writes"),
    "RATE_LIMIT_UPLOAD": Editable("Rate limiting", "Uploads"),
    "RATE_LIMIT_MATCH_CREATE": Editable("Rate limiting", "Match creation"),
    "RATE_LIMIT_STREAM": Editable("Rate limiting", "Live match streams"),
    "RATE_LIMIT_ADMIN": Editable("Rate limiting", "Admin endpoints"),
}

# Display names for the values of choice settings.
OPTION_LABELS: dict[str, dict[str, str]] = {
    "MATCH_SCHEDULER_SELECTION": {
        "least_played": "Least played (agents with fewer games first)",
        "random": "Random",
    },
    "MATCH_SCHEDULING_STRATEGY": {
        "serial": "Serial (one match at a time)",
        "concurrent": "Concurrent (keep the runners busy)",
    },
}

_SECRET_SUFFIXES = ("_KEY", "_PASSWORD", "_SECRET")
_URLS_WITH_CREDENTIALS = {"DATABASE_URL", "REDIS_URL"}

# Environment/default values, captured before any override is applied.
_base_values: dict[str, Any] = settings.model_dump()
_from_environment: set[str] = set(settings.model_fields_set)
# Overrides currently applied (valid ones only).
_active: dict[str, Any] = {}


class SettingsValidationError(ValueError):
    """Raised when overrides are invalid; ``errors`` maps setting name -> message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(f"{name}: {msg}" for name, msg in errors.items()))
        self.errors = errors


def validate_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Validate overrides with the full Settings rules; return the coerced values."""
    not_editable = sorted(set(overrides) - EDITABLE_SETTINGS.keys())
    if not_editable:
        raise SettingsValidationError(dict.fromkeys(not_editable, "cannot be changed at runtime"))
    try:
        candidate = Settings(_env_file=None, **{**_base_values, **overrides})  # type: ignore[call-arg]
    except ValidationError as e:
        errors: dict[str, str] = {}
        for err in e.errors():
            name = str(err["loc"][0]) if err["loc"] else "settings"
            errors[name] = err["msg"].removeprefix("Value error, ")
        raise SettingsValidationError(errors) from None
    return {name: getattr(candidate, name) for name in overrides}


def apply_overrides(overrides: dict[str, Any]) -> None:
    """Set every editable setting to its override, or back to its environment/default value."""
    for name in EDITABLE_SETTINGS:
        setattr(settings, name, overrides.get(name, _base_values[name]))
    _active.clear()
    _active.update(overrides)


def active_overrides() -> dict[str, Any]:
    return dict(_active)


def drop_unchanged(overrides: dict[str, Any]) -> dict[str, Any]:
    """Overrides that differ from the environment/default value (an equal one would only shadow later env changes)."""
    return {name: value for name, value in overrides.items() if value != _base_values[name]}


def load_overrides(stored: dict[str, Any]) -> dict[str, Any]:
    """Validate stored overrides one by one, skipping (and logging) any that are no longer valid."""
    valid: dict[str, Any] = {}
    for name, value in stored.items():
        try:
            valid = validate_overrides({**valid, name: value})
        except SettingsValidationError as e:
            reason = "; ".join(e.errors.values())
            logger.warning("Ignoring stored setting override %s=%r: %s", name, value, reason)
    apply_overrides(valid)
    return valid


def is_secret(name: str) -> bool:
    return name.endswith(_SECRET_SUFFIXES) or name in _URLS_WITH_CREDENTIALS


def display_value(name: str, value: Any) -> Any:
    """Value safe to show to admins: secrets masked, URL passwords removed."""
    if value in (None, ""):
        return value
    if name in _URLS_WITH_CREDENTIALS:
        parts = urlsplit(str(value))
        if parts.password:
            netloc = parts.netloc.replace(f":{parts.password}@", ":***@")
            return urlunsplit(parts._replace(netloc=netloc))
        return value
    return "***" if is_secret(name) else value


def _value_type(annotation: Any) -> tuple[str, list[str] | None]:
    """Map a Settings annotation to a UI input type (and options for choices)."""
    if get_origin(annotation) in (Union, types.UnionType):
        annotation = next(a for a in get_args(annotation) if a is not type(None))
    if get_origin(annotation) is Literal:
        return "choice", [str(a) for a in get_args(annotation)]
    for kind, name in ((bool, "bool"), (int, "int"), (float, "float")):
        if annotation is kind:
            return name, None
    return "str", None


def _bounds(name: str) -> tuple[float | None, float | None]:
    minimum = maximum = None
    for meta in Settings.model_fields[name].metadata:
        if isinstance(meta, Ge):
            minimum = float(meta.ge)  # type: ignore[arg-type]
        elif isinstance(meta, Gt):
            minimum = float(meta.gt)  # type: ignore[arg-type]
        elif isinstance(meta, Le):
            maximum = float(meta.le)  # type: ignore[arg-type]
        elif isinstance(meta, Lt):
            maximum = float(meta.lt)  # type: ignore[arg-type]
    return minimum, maximum


def describe(overrides: dict[str, Any]) -> list[dict[str, Any]]:
    """Every setting with its effective value and where it comes from (secrets masked)."""
    rows = []
    # Editable settings first, in EDITABLE_SETTINGS order.
    names = [*EDITABLE_SETTINGS, *(n for n in Settings.model_fields if n not in EDITABLE_SETTINGS)]
    for name in names:
        field = Settings.model_fields[name]
        kind, options = _value_type(field.annotation)
        minimum, maximum = _bounds(name)
        if name in overrides:
            source = "override"
        elif name in _from_environment:
            source = "environment"
        else:
            source = "default"
        editable = EDITABLE_SETTINGS.get(name)
        rows.append(
            {
                "name": name,
                "label": editable.label if editable else None,
                "group": editable.group if editable else None,
                "editable": name in EDITABLE_SETTINGS,
                "secret": is_secret(name),
                "value": display_value(name, getattr(settings, name)),
                "base_value": display_value(name, _base_values[name]),
                "source": source,
                "type": kind,
                "options": options,
                "option_labels": OPTION_LABELS.get(name),
                "minimum": minimum,
                "maximum": maximum,
                "description": field.description,
            }
        )
    return rows


def warnings() -> list[str]:
    """Combinations that are valid but probably not what the admin wants."""
    found = []
    runners = settings.MATCH_RUNNER_REPLICAS
    if settings.MATCH_SCHEDULING_STRATEGY == "concurrent" and runners < settings.MATCH_MAX_CONCURRENT_MATCHES:
        found.append(
            f"MATCH_MAX_CONCURRENT_MATCHES ({settings.MATCH_MAX_CONCURRENT_MATCHES}) is higher than the "
            f"{runners} configured match runner(s); the extra matches wait in the queue."
        )
    if settings.HUMAN_MATCH_MAX_DURATION_SECONDS < settings.HUMAN_MOVE_TIME_LIMIT_SECONDS:
        found.append("HUMAN_MATCH_MAX_DURATION_SECONDS is shorter than a single human move.")
    return found


def log_effective_config(overrides: dict[str, Any]) -> None:
    """Log every setting that differs from the code default, with its source."""
    lines = [
        f"  {row['name']} = {row['value']!r} ({row['source']})"
        for row in describe(overrides)
        if row["source"] != "default"
    ]
    logger.info("Effective configuration (non-default values):\n%s", "\n".join(lines) or "  (none)")
    for warning in warnings():
        logger.warning("Configuration: %s", warning)

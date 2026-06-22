"""Structured views over Terraform ``-json`` output.

Terraform's ``plan``/``apply`` JSON output is a stream of newline-delimited log
events. These dataclasses and parsers turn that raw event list into typed
objects, so callers can read "what will change" without filtering events by hand.

The parsers are tolerant: unknown or missing fields are skipped rather than
raising, and a non-list value (for example raw text when ``json=False``) yields
empty results.
"""

from dataclasses import dataclass
from typing import List, Optional

__all__ = [
    "ResourceChange",
    "ChangeSummary",
    "OutputChange",
]


@dataclass(frozen=True)
class ResourceChange:
    """A single resource that Terraform plans to change or has changed.

    ``action`` is Terraform's own verb, one of ``create``, ``update``,
    ``delete``, ``read``, ``replace``, ``import``, ``move``, ``forget`` or
    ``no-op``.
    """

    address: str
    action: str
    resource_type: str = ""
    name: str = ""
    module: str = ""
    provider: Optional[str] = None


@dataclass(frozen=True)
class ChangeSummary:
    """Counts from a Terraform ``change_summary`` event.

    ``import_`` carries the ``import`` count (``import`` is a Python keyword).
    """

    add: int = 0
    change: int = 0
    remove: int = 0
    import_: int = 0
    operation: str = ""


@dataclass(frozen=True)
class OutputChange:
    """A planned or applied change to a root module output value."""

    name: str
    action: str
    sensitive: bool = False


def _events(value) -> list:
    """Return the event list, or an empty list for non-list values."""
    return value if isinstance(value, list) else []


def _resource_change(resource: Optional[dict], action: str) -> ResourceChange:
    resource = resource or {}
    return ResourceChange(
        address=resource.get("addr", ""),
        action=action,
        resource_type=resource.get("resource_type", ""),
        name=resource.get("resource_name", ""),
        module=resource.get("module", ""),
        provider=resource.get("implied_provider"),
    )


def parse_planned_changes(value) -> List[ResourceChange]:
    """Resource changes from ``planned_change`` events (``plan`` output)."""
    changes = []
    for event in _events(value):
        if event.get("type") == "planned_change":
            change = event.get("change") or {}
            changes.append(
                _resource_change(change.get("resource"), change.get("action", ""))
            )
    return changes


def parse_applied_changes(value) -> List[ResourceChange]:
    """Resource changes from ``apply_complete`` events (``apply`` output)."""
    changes = []
    for event in _events(value):
        if event.get("type") == "apply_complete":
            hook = event.get("hook") or {}
            changes.append(
                _resource_change(hook.get("resource"), hook.get("action", ""))
            )
    return changes


def parse_drift(value) -> List[ResourceChange]:
    """Resource drift from ``resource_drift`` events."""
    changes = []
    for event in _events(value):
        if event.get("type") == "resource_drift":
            change = event.get("change") or {}
            changes.append(
                _resource_change(change.get("resource"), change.get("action", ""))
            )
    return changes


def parse_summary(value, operation: Optional[str] = None) -> ChangeSummary:
    """The ``change_summary`` counts, optionally filtered by ``operation``.

    ``apply`` output carries both a ``plan`` and an ``apply`` summary, so pass
    ``operation`` to pick the right one. Returns an empty summary when none is
    found.
    """
    summary = ChangeSummary()
    for event in _events(value):
        if event.get("type") != "change_summary":
            continue
        changes = event.get("changes") or {}
        if operation is not None and changes.get("operation") != operation:
            continue
        summary = ChangeSummary(
            add=changes.get("add", 0),
            change=changes.get("change", 0),
            remove=changes.get("remove", 0),
            import_=changes.get("import", 0),
            operation=changes.get("operation", ""),
        )
    return summary


def parse_output_changes(value) -> List[OutputChange]:
    """Output changes from the last ``outputs`` event."""
    result: List[OutputChange] = []
    for event in _events(value):
        if event.get("type") == "outputs":
            outputs = event.get("outputs") or {}
            result = [
                OutputChange(
                    name=name,
                    action=info.get("action", ""),
                    sensitive=info.get("sensitive", False),
                )
                for name, info in outputs.items()
            ]
    return result

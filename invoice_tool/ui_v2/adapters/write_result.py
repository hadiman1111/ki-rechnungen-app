"""Structured write-operation results for UI-v2 adapters."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WriteOperationResult:
    success: bool
    message: str = ""
    errors: tuple[str, ...] = field(default_factory=tuple)
    profile_id: str | None = None
    configuration_id: str | None = None

    @classmethod
    def ok(cls, *, message: str = "", profile_id: str | None = None, configuration_id: str | None = None) -> WriteOperationResult:
        return cls(success=True, message=message, profile_id=profile_id, configuration_id=configuration_id)

    @classmethod
    def fail(cls, *errors: str, message: str = "") -> WriteOperationResult:
        items = tuple(error for error in errors if error)
        if not message and items:
            message = items[0]
        return cls(success=False, message=message or "Speichern nicht möglich.", errors=items)

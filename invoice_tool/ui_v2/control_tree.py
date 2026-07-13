"""Control-tree helpers for UI-v2 runtime rendering audits."""

from __future__ import annotations

from typing import Any, Iterable


def iter_controls(root: Any) -> Iterable[Any]:
    if root is None:
        return
    yield root

    content = getattr(root, "content", None)
    if content is not None:
        if isinstance(content, list):
            for item in content:
                yield from iter_controls(item)
        else:
            yield from iter_controls(content)

    controls = getattr(root, "controls", None)
    if controls:
        for item in controls:
            yield from iter_controls(item)


def control_label(control: Any) -> str | None:
    if control.__class__.__name__ == "Text":
        value = getattr(control, "value", None)
        if isinstance(value, str) and value:
            return value

    if control.__class__.__name__ == "ListTile":
        title = getattr(control, "title", None)
        title_label = control_label(title)
        if title_label:
            return title_label

    content = getattr(control, "content", None)
    if isinstance(content, str) and content:
        return content
    return None


def find_nav_handler(root: Any, label: str):
    """Return on_click for a sidebar nav item identified by visible label."""
    for control in iter_controls(root):
        if control.__class__.__name__ == "ListTile":
            title = getattr(control, "title", None)
            if control_label(title) == label:
                handler = getattr(control, "on_click", None)
                if handler is not None:
                    return handler
        if getattr(control, "on_click", None) is None:
            continue
        for item in iter_controls(control):
            if control_label(item) == label:
                return control.on_click
    return None


def collect_labels(root: Any) -> set[str]:
    labels: set[str] = set()
    for control in iter_controls(root):
        label = control_label(control)
        if label:
            labels.add(label)
    return labels

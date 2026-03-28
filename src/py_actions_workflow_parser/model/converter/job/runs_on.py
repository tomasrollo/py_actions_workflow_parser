"""convert_runs_on — converts the runs-on token."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ....tokens.template_token import TemplateToken
from ....tokens.type_guards import is_mapping, is_sequence, is_string

if TYPE_CHECKING:
    from ....templates.template_context import TemplateContext

_VALID_GROUP_PREFIXES = {"org", "organization", "ent", "enterprise"}


@dataclass
class RunsOn:
    labels: set[str] = field(default_factory=set)
    group: str = ""


def convert_runs_on(context: "TemplateContext", token: TemplateToken) -> RunsOn:
    labels = _convert_runs_on_labels(token)

    if not is_mapping(token):
        return RunsOn(labels=labels)

    group = ""
    for item in token:
        key = item.key.assert_string("job runs-on property name")
        if key.value == "group":
            if item.value.is_expression:
                continue
            group_name = item.value.assert_string("job runs-on group name").value
            parts = group_name.split("/")
            if len(parts) == 1:
                group = group_name
            elif len(parts) == 2:
                if parts[0] not in _VALID_GROUP_PREFIXES:
                    context.error(
                        item.value,
                        f"Invalid runs-on group name '{group_name}. Please use 'organization/' or 'enterprise/' prefix to target a single runner group.'",
                    )
                    continue
                if not parts[1]:
                    context.error(
                        item.value, f"Invalid runs-on group name '{group_name}'."
                    )
                    continue
                group = group_name
            else:
                context.error(
                    item.value,
                    f"Invalid runs-on group name '{group_name}. Please use 'organization/' or 'enterprise/' prefix to target a single runner group.'",
                )
        elif key.value == "labels":
            map_labels = _convert_runs_on_labels(item.value)
            labels.update(map_labels)

    return RunsOn(labels=labels, group=group)


def _convert_runs_on_labels(token: TemplateToken) -> set[str]:
    labels: set[str] = set()
    if token.is_expression:
        return labels

    if is_string(token):
        labels.add(token.value)
        return labels

    if is_sequence(token):
        for item in token:
            if item.is_expression:
                continue
            label = item.assert_string("job runs-on label sequence item")
            labels.add(label.value)

    return labels

"""convert_on — converts the 'on' trigger events token."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ...tokens.template_token import TemplateToken
from ...tokens.type_guards import is_literal, is_mapping, is_sequence, is_string
from ...tokens.types import TokenType
from ..workflow_template import EventsConfig, ScheduleConfig
from .cron import is_valid_cron
from .string_list import convert_string_list
from .workflow_call import convert_event_workflow_call
from .workflow_dispatch import convert_event_workflow_dispatch_inputs

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext
    from ...tokens.mapping_token import MappingToken
    from ...tokens.sequence_token import SequenceToken


def convert_on(context: "TemplateContext", token: TemplateToken) -> EventsConfig:
    result = EventsConfig()

    if is_literal(token):
        event = token.assert_string("on")
        result.extra[event.value] = {}
        result.event_order.append(event.value)
        return result

    if is_sequence(token):
        for item in token:
            event = item.assert_string("on")
            result.extra[event.value] = {}
            result.event_order.append(event.value)
        return result

    if is_mapping(token):
        for item in token:
            event_key = item.key.assert_string("event name")
            event_name = event_key.value

            if item.value.template_token_type == TokenType.Null:
                _set_event(result, event_name, {})
                result.event_order.append(event_name)
                continue

            if event_name == "schedule":
                schedule_token = item.value.assert_sequence(f"event {event_name}")
                result.schedule = _convert_schedule(context, schedule_token)
                result.event_order.append(event_name)
                continue

            event_token = item.value.assert_mapping(f"event {event_name}")

            if event_name == "workflow_call":
                result.workflow_call = convert_event_workflow_call(context, event_token)
                result.event_order.append(event_name)
                continue

            if event_name == "workflow_dispatch":
                result.workflow_dispatch = convert_event_workflow_dispatch_inputs(
                    context, event_token
                )
                result.event_order.append(event_name)
                continue

            event_data: dict[str, Any] = {}
            event_data.update(_convert_pattern_filter("branches", event_token))
            event_data.update(_convert_pattern_filter("tags", event_token))
            event_data.update(_convert_pattern_filter("paths", event_token))
            event_data.update(_convert_filter("types", event_token))
            event_data.update(_convert_filter("versions", event_token))
            event_data.update(_convert_filter("names", event_token))
            event_data.update(_convert_filter("workflows", event_token))

            _set_event(result, event_name, event_data)
            result.event_order.append(event_name)

        return result

    context.error(token, "Invalid format for 'on'")
    return result


def _set_event(result: EventsConfig, event_name: str, data: dict[str, Any]) -> None:
    """Store event data either in the well-known fields or in the extra dict."""
    if event_name == "pull_request":
        result.pull_request = data
    elif event_name == "pull_request_target":
        result.pull_request_target = data
    elif event_name == "push":
        result.push = data
    elif event_name == "workflow_run":
        result.workflow_run = data
    else:
        result.extra[event_name] = data


def _convert_pattern_filter(name: str, token: "MappingToken") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in token:
        key = item.key.assert_string(f"{name} filter key")
        if key.value == name:
            if is_string(item.value):
                result[name] = [item.value.value]
            else:
                result[name] = convert_string_list(
                    name, item.value.assert_sequence(f"{name} list")
                )
        elif key.value == f"{name}-ignore":
            ignore_key = f"{name}-ignore"
            if is_string(item.value):
                result[ignore_key] = [item.value.value]
            else:
                result[ignore_key] = convert_string_list(
                    ignore_key, item.value.assert_sequence(f"{ignore_key} list")
                )
    return result


def _convert_filter(name: str, token: "MappingToken") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in token:
        key = item.key.assert_string(f"{name} filter key")
        if key.value == name:
            if is_string(item.value):
                result[name] = [item.value.value]
            else:
                result[name] = convert_string_list(
                    name, item.value.assert_sequence(f"{name} list")
                )
    return result


def _convert_schedule(
    context: "TemplateContext",
    token: "SequenceToken",
) -> list[ScheduleConfig] | None:
    result: list[ScheduleConfig] = []

    for item in token:
        mapping_token = item.assert_mapping("event schedule")
        config = ScheduleConfig(cron="")
        valid = True

        for entry in mapping_token:
            key = entry.key.assert_string("schedule key")
            if key.value == "cron":
                cron = entry.value.assert_string("schedule cron")
                if not is_valid_cron(cron.value):
                    context.error(
                        cron,
                        "Invalid cron expression. Expected format: '* * * * *' (minute hour day month weekday)",
                    )
                config.cron = cron.value
            elif key.value == "timezone":
                config.timezone = entry.value.assert_string("schedule timezone").value
            else:
                context.error(key, "Invalid schedule key")
                valid = False

        if valid and config.cron:
            result.append(config)
        elif valid and not config.cron:
            context.error(
                mapping_token, "Missing required key 'cron' in schedule entry"
            )

    return result

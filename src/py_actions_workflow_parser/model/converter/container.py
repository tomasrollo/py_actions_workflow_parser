"""convert_to_job_container — converts a container token to a Container model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ...tokens.template_token import TemplateToken
from ...tokens.type_guards import is_string
from ..workflow_template import Container, Credential

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext


def convert_to_job_container(
    context: "TemplateContext",
    container: TemplateToken,
) -> Optional[Container]:
    # Skip validation for expressions
    for _parent, token, _key, _ancestors in TemplateToken.traverse(container):
        if token.is_expression:
            return None

    if is_string(container):
        return Container(image=container)  # type: ignore[arg-type]

    mapping = container.assert_mapping("container item")
    result = Container()

    for item in mapping:
        key = item.key.assert_string("container item key")
        value = item.value

        if key.value == "image":
            result.image = value.assert_string("container image")
        elif key.value == "credentials":
            _convert_to_job_credentials(context, value)
        elif key.value == "env":
            result.env = value.assert_mapping("container env")
            for env_item in result.env:
                env_item.key.assert_string("container env value")
        elif key.value == "ports":
            result.ports = value.assert_sequence("container ports")
            for port in result.ports:
                port.assert_string("container port")
        elif key.value == "volumes":
            result.volumes = value.assert_sequence("container volumes")
            for vol in result.volumes:
                vol.assert_string("container volume")
        elif key.value == "options":
            result.options = value.assert_string("container options")
        else:
            context.error(key, f"Unexpected container item key: {key.value}")

    if not result.image:
        context.error(container, "Container image cannot be empty")
        return None

    return result


def convert_to_job_services(
    context: "TemplateContext",
    services: TemplateToken,
) -> list[Container] | None:
    service_list: list[Container] = []
    mapping = services.assert_mapping("services")
    for service in mapping:
        service.key.assert_string("service key")
        c = convert_to_job_container(context, service.value)
        if c is not None:
            service_list.append(c)
    return service_list


def _convert_to_job_credentials(
    context: "TemplateContext",
    value: TemplateToken,
) -> Credential | None:
    mapping = value.assert_mapping("credentials")
    cred = Credential()

    for item in mapping:
        key = item.key.assert_string("credentials item")
        val = item.value
        if key.value == "username":
            cred.username = val.assert_string("credentials username")
        elif key.value == "password":
            cred.password = val.assert_string("credentials password")
        else:
            context.error(key, f"Invalid credentials key: {key.value}")

    return cred

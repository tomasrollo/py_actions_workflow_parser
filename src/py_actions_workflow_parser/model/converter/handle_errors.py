"""handle_template_token_errors — helper to catch TemplateTokenError during conversion."""

from __future__ import annotations

from typing import Callable, TypeVar

from ...tokens.template_token import TemplateToken, TemplateTokenError

if __name__ != "__main__":
    from ...templates.template_context import TemplateContext

T = TypeVar("T")


def handle_template_token_errors(
    root: TemplateToken,
    context: "TemplateContext",
    default_value: T,
    f: Callable[[], T],
) -> T:
    result = default_value
    try:
        result = f()
    except TemplateTokenError as err:
        context.error(err.token, err)
    except Exception as err:
        context.error(root, err)
    return result

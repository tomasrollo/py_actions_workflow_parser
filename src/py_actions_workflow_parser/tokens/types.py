"""TokenType enum and token_type_name() helper."""

from enum import IntEnum


class TokenType(IntEnum):
    String = 0
    Sequence = 1
    Mapping = 2
    BasicExpression = 3
    InsertExpression = 4
    Boolean = 5
    Number = 6
    Null = 7


_TOKEN_TYPE_NAMES: dict[int, str] = {
    TokenType.String: "StringToken",
    TokenType.Sequence: "SequenceToken",
    TokenType.Mapping: "MappingToken",
    TokenType.BasicExpression: "BasicExpressionToken",
    TokenType.InsertExpression: "InsertExpressionToken",
    TokenType.Boolean: "BooleanToken",
    TokenType.Number: "NumberToken",
    TokenType.Null: "NullToken",
}


def token_type_name(token_type: TokenType) -> str:
    name = _TOKEN_TYPE_NAMES.get(int(token_type))
    if name is None:
        raise ValueError(f"Unhandled token type: {token_type}")
    return name

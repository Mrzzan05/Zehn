"""
tests/support/snapshot_cases.py

Deterministic inputs for the bounded-snapshot golden test. Each entry builds
a FRESH value on demand. This module imports nothing from `reality`, so the
same inputs can be run against the code both before and after it moved.
"""

from decimal import Decimal
from typing import Callable


class MyInt(int):
    pass


class MyStr(str):
    pass


class MyDict(dict):
    pass


class Custom:
    pass


def _nested(levels: int) -> object:
    value: object = "leaf"
    for _ in range(levels):
        value = [value]
    return value


def _cyclic() -> object:
    cyc: dict = {}
    cyc["self"] = cyc
    return cyc


CASES: dict[str, Callable[[], object]] = {
    "none": lambda: None,
    "bool_true": lambda: True,
    "small_int": lambda: 7,
    "plain_float": lambda: 0.5,
    "short_str": lambda: "hello",
    "unicode_str": lambda: "نمونه é ☃",
    "lone_surrogate_str": lambda: "bad\ud800text",
    "str_len_1022": lambda: "x" * 1022,   # canonical form is exactly 1024 chars: not truncated
    "str_len_1023": lambda: "x" * 1023,   # canonical form is 1025 chars: truncated
    "str_len_5000": lambda: "x" * 5000,
    "nested_claim": lambda: {
        "subject_text": "Sara", "predicate": "likes",
        "type_hints": {"a": "b"}, "items": [1, 2, {"x": None}],
    },
    "tuple_as_list": lambda: (1, "a", (2, 3)),
    "empty_containers": lambda: {"a": {}, "b": []},
    "non_string_keys": lambda: {1: "a", None: "b", (1, 2): "c"},
    "dict_64_items": lambda: {f"k{i}": i for i in range(64)},
    "dict_65_items": lambda: {f"k{i}": i for i in range(65)},
    "dict_100k_items": lambda: {f"k{i}": i for i in range(100_000)},
    "list_200_items": lambda: list(range(200)),
    "nesting_8_levels": lambda: _nested(8),
    "nesting_9_levels": lambda: _nested(9),
    "nesting_10000_levels": lambda: _nested(10_000),
    "cyclic_dict": _cyclic,
    "wide_nested_node_budget": lambda: [[0] * 64 for _ in range(64)],
    "huge_int": lambda: 10 ** 5000,
    "int_limit_edges": lambda: [2 ** 63 - 1, 2 ** 63, -(2 ** 63), -(2 ** 63) + 1],
    "non_finite_floats": lambda: [float("nan"), float("inf"), float("-inf")],
    "unserializable_and_subclasses": lambda: {
        "decimal": Decimal("1.5"), "custom": Custom(),
        "str_sub": MyStr("x"), "int_sub": MyInt(1), "dict_sub": MyDict(a=1),
    },
    "preview_truncated_by_many_keys": lambda: {f"key_{i:02d}": "v" * 30 for i in range(60)},
    "bool_vs_int_list": lambda: [True, 1, False, 0],
}
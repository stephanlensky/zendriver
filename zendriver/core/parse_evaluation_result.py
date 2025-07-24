import base64
import datetime
import re
import urllib.parse

from typing import Any, Union

SerializedValue = Union[
    None, bool, int, float, str, dict  # the serialized object variants
]

typed_array_constructors = {
    "i8": "b",  # Int8Array
    "ui8": "B",  # Uint8Array
    "ui8c": "B",  # Uint8ClampedArray (same as Uint8Array)
    "i16": "h",
    "ui16": "H",
    "i32": "i",
    "ui32": "I",
    "f32": "f",
    "f64": "d",
    "bi64": "q",
    "bui64": "Q",
}


def base64_to_bytes(base64_str: str) -> bytes:
    return base64.b64decode(base64_str)


def base64_to_typed_array(base64_str: str, kind: str):
    from array import array

    type_code = typed_array_constructors.get(kind)
    if not type_code:
        raise ValueError(f"Unsupported typed array kind: {kind}")
    data = base64_to_bytes(base64_str)
    arr = array(type_code)
    arr.frombytes(data)
    return arr


def parse_evaluation_result_value(
    value: SerializedValue, handles=None, refs=None
) -> Any:
    if refs is None:
        refs = {}
    if handles is None:
        handles = []

    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, dict):
        if "ref" in value:
            return refs.get(value["ref"])

        if "v" in value:
            v = value["v"]
            if v == "undefined":
                return None
            if v == "null":
                return None
            if v == "NaN":
                return float("nan")
            if v == "Infinity":
                return float("inf")
            if v == "-Infinity":
                return float("-inf")
            if v == "-0":
                return -0.0
            return None

        if "d" in value:
            return datetime.datetime.fromisoformat(value["d"])

        if "u" in value:
            return urllib.parse.urlparse(value["u"])

        if "bi" in value:
            return int(value["bi"])

        if "e" in value:
            e = value["e"]
            exc = Exception(e["m"])
            exc.name = e["n"]  # type: ignore
            exc.stack = e["s"]  # type: ignore
            return exc

        if "r" in value:
            return re.compile(value["r"]["p"], flags=_regex_flags(value["r"]["f"]))

        if "a" in value:
            arr: list = []
            refs[value["id"]] = arr
            for item in value["a"]:
                arr.append(parse_evaluation_result_value(item, handles, refs))
            return arr

        if "o" in value:
            obj: dict = {}
            refs[value["id"]] = obj
            for pair in value["o"]:
                key = pair["k"]
                if key == "__proto__":
                    continue
                obj[key] = parse_evaluation_result_value(pair["v"], handles, refs)
            return obj

        if "h" in value:
            return handles[value["h"]]

        if "ta" in value:
            return base64_to_typed_array(value["ta"]["b"], value["ta"]["k"])

    return value


def _regex_flags(flags_str: str) -> int:
    flags = 0
    for ch in flags_str:
        if ch == "i":
            flags |= re.IGNORECASE
        elif ch == "m":
            flags |= re.MULTILINE
        elif ch == "s":
            flags |= re.DOTALL
        # Add more mappings if needed
    return flags

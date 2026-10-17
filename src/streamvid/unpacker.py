# src/streamvid/unpacker.py
"""Wrapper de eval-unpacker como librería Python.
"""

from __future__ import annotations

import sys

from eval_unpacker.core import (
    find_eval_function_calls,
    unpack_payload_from_call_args,
    fix_malformed_setrequestheader,
)


def unpack_eval_script(script_text: str, debug: bool = False) -> str | None:
    """
    Desempaqueta un bloque `eval(function(p,a,c,k,e,d){...})(...)`.

    Args:
        script_text: JS que contiene el patrón eval(function...)
        debug: si True, imprime info a stderr

    Returns:
        El JS desempacado, o None si no se encontró el patrón.
    """
    if not script_text:
        return None

    matches = find_eval_function_calls(script_text)
    if not matches:
        if debug:
            print("[unpacker] no se encontró eval(function...)", file=sys.stderr)
        return None

    _, _, call_args = matches[0]
    unpacked = unpack_payload_from_call_args(call_args, debug=debug)
    if unpacked is None:
        return None

    return fix_malformed_setrequestheader(unpacked)

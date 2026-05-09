from typing import Dict

FU_TYPE: Dict[str, str] = {
    "load": "LOAD",
    "store": "STORE",
    "beq": "BEQ",
    "call": "CALL_RET",
    "ret": "CALL_RET",
    "add": "ADD_SUB",
    "sub": "ADD_SUB",
    "and": "AND",
    "mul": "MUL",
}

FU_LATENCY: Dict[str, int] = {
    "LOAD": 8,
    "STORE": 8,
    "BEQ": 1,
    "CALL_RET": 1,
    "ADD_SUB": 2,
    "AND": 1,
    "MUL": 8,
}

FU_COUNT: Dict[str, int] = {
    "LOAD": 2,
    "STORE": 2,
    "BEQ": 2,
    "CALL_RET": 1,
    "ADD_SUB": 4,
    "AND": 2,
    "MUL": 1,
}

MEMORY_LIMIT = 1 << 16

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Instruction:
    pc: int
    mnemonic: str
    dest: Optional[str] = None
    src1: Optional[str] = None
    src2: Optional[str] = None
    immediate: Optional[int] = None
    target: Optional[int] = None
    raw_text: str = ""

    issued_cycle: Optional[int] = None
    start_cycle: Optional[int] = None
    finish_cycle: Optional[int] = None
    write_cycle: Optional[int] = None
    completed: bool = False
    flushed: bool = False

    @property
    def is_branch(self) -> bool:
        return self.mnemonic == "beq"

    @property
    def is_control(self) -> bool:
        return self.mnemonic in {"beq", "call", "ret"}

    @property
    def is_load(self) -> bool:
        return self.mnemonic == "load"

    @property
    def is_store(self) -> bool:
        return self.mnemonic == "store"

    @property
    def is_memory(self) -> bool:
        return self.is_load or self.is_store

    @property
    def is_arithmetic(self) -> bool:
        return self.mnemonic in {"add", "sub", "and", "mul"}

    def has_dest(self) -> bool:
        return self.dest is not None and self.mnemonic != "store"

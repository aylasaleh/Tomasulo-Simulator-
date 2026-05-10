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

    issued_cycle: List[Optional[int]] = field(default_factory=list)
    start_cycle: List[Optional[int]] = field(default_factory=list)
    finish_cycle: List[Optional[int]] = field(default_factory=list)
    write_cycle: List[Optional[int]] = field(default_factory=list)
    completed: List[bool] = field(default_factory=list)
    flushed: List[bool] = field(default_factory=list)

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

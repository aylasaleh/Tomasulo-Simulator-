from typing import List, Optional


class RegisterFile:
    def __init__(self):
        self.values: List[int] = [0] * 8
        self.producer_stack: List[List[str]] = [[] for _ in range(8)]

    def _index(self, register: str) -> int:
        return int(register[1:])

    def read(self, register: str) -> int:
        return self.values[self._index(register)]

    def current_producer(self, register: str) -> Optional[str]:
        if register == "r0":
            return None
        stack = self.producer_stack[self._index(register)]
        return stack[-1] if stack else None

    def write(self, register: str, value: int, FU: str) -> None:
        if register == "r0":
            return
        idx = self._index(register)
        current = self.current_producer(register)
        if current == FU:
            self.values[idx] = value
        self.remove_pending_producer(register, FU)

    def add_pending_producer(self, register: str, FU: str) -> None:
        if register == "r0":
            return
        stack = self.producer_stack[self._index(register)]
        stack.append(FU)

    def remove_pending_producer(self, register: str, FU: str) -> None:
        if register == "r0":
            return
        stack = self.producer_stack[self._index(register)]
        if FU in stack:
            stack.remove(FU)

    def is_ready(self, register: str) -> bool:
        return self.current_producer(register) is None

    def is_producer_pending(self, register: str, FU: str) -> bool:
        if register == "r0":
            return False
        stack = self.producer_stack[self._index(register)]
        return FU in stack

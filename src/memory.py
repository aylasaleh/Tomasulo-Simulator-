from isa import MEMORY_LIMIT


class Memory:
    def __init__(self, initial_values=None):
        self.storage = {}
        if initial_values:
            for address, value in initial_values.items():
                self.store(address, value)

    def load(self, address: int) -> int:
        if address < 0 or address >= MEMORY_LIMIT:
            raise ValueError(f"Memory address out of bounds: {address}")
        return self.storage.get(address, 0)

    def store(self, address: int, value: int) -> None:
        if address < 0 or address >= MEMORY_LIMIT:
            raise ValueError(f"Memory address out of bounds: {address}")
        self.storage[address] = value

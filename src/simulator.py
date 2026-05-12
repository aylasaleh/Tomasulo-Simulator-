from typing import Dict, Iterator, List, Optional

from instruction import Instruction
from isa import FU_LATENCY, FU_TYPE
from memory import Memory
from register_file import RegisterFile
from reservation_station import ReservationStations, ReservationStationSlot


class Simulator:
    def __init__(self, instructions: List[Instruction], memory_init: Dict[int, int]):
        self.instructions = instructions
        self.program_index = {instr.pc: idx for idx, instr in enumerate(instructions)}
        self.memory = Memory(memory_init)
        self.registers = RegisterFile()
        self.rs = ReservationStations()
        self.next_issue_index = 0
        self.cycle = 0
        self.completed_count = 0
        self.branch_count = 0
        self.mispredictions = 0
        self.block_start_issue = False
        self.call_stack: List[int] = []

    def step(self) -> bool:
        """Execute one simulation cycle. Returns False if the simulation is finished."""
        if self.is_done():
            return False

        self.cycle += 1

        # 1. Write stage (Broadcasting results)
        self.complete_write_stage()

        # 2. Execution stage (Advancing timers and processing finishes)
        finished = self.advance_execution()
        self.process_finished_execution(finished)

        # 3. Handle control hazard blocking
        if self.block_start_issue:
            self.block_start_issue = False
            return True

        # 4. Start execution for ready instructions
        self.start_ready_executions()

        # 5. Issue stage
        self.issue_instruction()

        return True

    def run(self) -> None:
        """Runs the simulation until completion."""
        while self.step():
            pass

    #SECTION WRITE STAGE
    def complete_write_stage(self) -> None:
        write_slots = [slot for slot in self.get_all_slots() if slot.busy and slot.stage == "WRITE" and slot.instruction is not None]
        for slot in sorted(write_slots, key=lambda s: s.inst_pc if s.inst_pc is not None else float('inf')):
            was_control = slot.instruction.is_control
            self.perform_write(slot)
            slot.busy = False  # empty slot for next instruction
            self.completed_count += 1
            slot.instruction.completed = True
            slot.instruction.write_cycle = self.cycle
            slot.instruction.trace.append(("write", self.cycle))
            if was_control:
                self.block_start_issue = True

    # computes targets for any branches/jumps and broadcasts results if needed and writes to registers
    def perform_write(self, slot: ReservationStationSlot) -> None:
        instr = slot.instruction
        if instr.mnemonic == "call":
            value = instr.pc + 1
            self.broadcast_result(slot.name, value)
            if slot.name is not None:
                self.registers.write("r1", value, slot.name)
            if instr.target is not None:
                self.call_stack.append(instr.target)
            self.flush_wrong_path(instr.pc)
            self.jump_to_target(instr.target)
        elif instr.mnemonic == "ret":
            target = self.registers.read("r1")
            call_target = self.call_stack.pop() if self.call_stack else None
            self.flush_wrong_path(instr.pc)
            self.jump_to_target(target, preserve_range=(call_target, instr.pc) if call_target is not None else None)
        elif instr.mnemonic == "beq":
            taken = slot.Vj == slot.Vk
            if taken:
                self.mispredictions += 1
                self.flush_wrong_path(instr.pc, instr.target)
                self.jump_to_target(instr.target)
        elif instr.has_dest():
            value = slot.value if slot.value is not None else self.compute_result(slot)
            self.broadcast_result(slot.name, value)
            if slot.name is not None:
                self.registers.write(instr.dest, value, slot.name)
    #!SECTION 

    #SECTION EXECUTION STAGE
    def advance_execution(self) -> List[ReservationStationSlot]:
        for slot in self.get_all_slots():
            self.update_operand_availability(slot)
        finished: List[ReservationStationSlot] = []

        for slot in self.get_all_slots():
            if not slot.busy or slot.stage != "EXECUTE":
                continue

            # handle address computation for memory operations (2 cycles)
            if self.is_memory_slot(slot) and slot.address is None:
                if slot.addr_comp_cycles_remaining is not None and slot.addr_comp_cycles_remaining > 0:
                    slot.addr_comp_cycles_remaining -= 1
                    slot.rem_cycles -= 1
                    continue
                elif slot.addr_comp_cycles_remaining == 0:
                    self.compute_effective_address(slot)
                    slot.addr_comp_cycles_remaining = None

            # check if memory operation can proceed (no conflicts)
            if self.is_memory_slot(slot) and slot.address is not None and not self.can_start_memory_operation(slot):
                continue

            if slot.rem_cycles == 0:
                if not self.is_store_slot(slot) and not self.is_control_slot(slot):
                    slot.value = self.compute_result(slot)
                slot.stage = "WRITE"
                slot.instruction.finish_cycle = self.cycle
                slot.instruction.trace.append(("finish", self.cycle))
                finished.append(slot)
            else:
                slot.rem_cycles -= 1

        return finished

    def process_finished_execution(self, finished_entries: List[ReservationStationSlot]) -> None:
        for slot in finished_entries:
            if not slot.busy:
                continue

            if self.is_store_slot(slot):
                self.perform_store(slot)
                slot.instruction.write_cycle = self.cycle
                slot.instruction.trace.append(("write", self.cycle))
                self.completed_count += 1
                if slot.instruction is not None:
                    slot.instruction.completed = True
                self.cleanup_slot(slot)

    def start_ready_executions(self) -> None:
        for slot in self.get_all_slots():
            if not slot.busy or slot.stage != "ISSUE":
                continue

            if slot.Qj is not None or slot.Qk is not None:
                continue

            if self.has_unresolved_older_branch(slot):
                continue

            if self.is_memory_slot(slot):
                if slot.address is None:
                    if not self.can_compute_address(slot):
                        continue
                    if slot.instruction.is_load and self.has_older_store(slot):
                        continue
                elif not self.can_start_memory_operation(slot):
                    continue

            slot.stage = "EXECUTE"
            slot.instruction.start_cycle = self.cycle
            slot.instruction.trace.append(("start", self.cycle))
            
            # Initialize address computation cycles for memory operations
            if self.is_memory_slot(slot):
                slot.addr_comp_cycles_remaining = 2
    #!SECTION

    #SECTION ISSUE STAGE
    def issue_instruction(self) -> None:
        while self.next_issue_index < len(self.instructions):
            instr = self.instructions[self.next_issue_index]

            if instr.issued_cycle and not instr.flushed:
                self.next_issue_index += 1
                continue
            if instr.flushed:
                instr.flushed = 0

            if self.is_instruction_in_flight(instr):
                self.next_issue_index += 1
                continue

            fu_type = FU_TYPE[instr.mnemonic]
            slot = self.rs.get_free_station(fu_type)
            if slot is None:
                return

            slot.instruction = instr
            slot.inst_pc = instr.pc
            slot.busy = True
            slot.fu_type = fu_type
            slot.stage = "ISSUE"
            slot.instruction.issued_cycle = self.cycle
            slot.instruction.trace.append(("issued", self.cycle))
            slot.rem_cycles = FU_LATENCY[fu_type] - 1
            slot.immediate = instr.immediate

            self.populate_operand_tags(slot)
            if instr.has_dest() and slot.name is not None:
                self.registers.add_pending_producer(instr.dest, slot.name)
            if instr.is_control and instr.mnemonic == "beq":
                self.branch_count += 1
            self.next_issue_index += 1
            return
    #!SECTION

    def is_done(self) -> bool:
        all_issued = self.next_issue_index >= len(self.instructions)
        all_rs_empty = not any(slot.busy for slot in self.get_all_slots())
        return all_issued and all_rs_empty

    def get_all_slots(self) -> Iterator[ReservationStationSlot]:
        for entries in self.rs.stations.values():
            for slot in entries:
                yield slot

    def is_instruction_in_flight(self, instr: Instruction) -> bool:
        return any(slot.busy and slot.instruction is instr for slot in self.get_all_slots())

    def is_memory_slot(self, slot: ReservationStationSlot) -> bool:
        return slot.busy and bool(slot.instruction and slot.instruction.is_memory)

    def _older_busy_slots(self, slot: ReservationStationSlot) -> Iterator[ReservationStationSlot]:
        if not slot.busy or slot.inst_pc is None or slot.instruction is None:
            return
        for other in self.get_all_slots():
            if other is slot or not other.busy or other.inst_pc is None or other.instruction is None:
                continue
            if other.inst_pc >= slot.inst_pc:
                continue
            yield other

    def is_store_slot(self, slot: ReservationStationSlot) -> bool:
        return slot.busy and bool(slot.instruction and slot.instruction.is_store)

    def is_control_slot(self, slot: ReservationStationSlot) -> bool:
        return slot.busy and bool(slot.instruction and slot.instruction.is_control)

    def populate_operand_tags(self, slot: ReservationStationSlot) -> None:
        if not slot.busy or slot.instruction is None:
            return
        instr = slot.instruction
        if instr.src1:
            producer = self.registers.current_producer(instr.src1)
            if producer is None:
                slot.Vj = self.registers.read(instr.src1)
            else:
                slot.Qj = producer
        if instr.src2:
            producer = self.registers.current_producer(instr.src2)
            if producer is None:
                slot.Vk = self.registers.read(instr.src2)
            else:
                slot.Qk = producer

    def can_compute_address(self, slot: ReservationStationSlot) -> bool:
        if not slot.busy or slot.instruction is None:
            return False
        if not self.is_memory_slot(slot):
            return False
        if slot.Qj is not None:
            return False
        for other in self._older_busy_slots(slot):
            if self.is_memory_slot(other) and other.address is None and other.instruction.is_store:
                return False
        return True

    def has_older_store(self, slot: ReservationStationSlot) -> bool:
        if not slot.busy or slot.instruction is None:
            return False
        if not self.is_memory_slot(slot):
            return False
        return any(other.instruction.is_store for other in self._older_busy_slots(slot))

    def has_unresolved_older_branch(self, slot: ReservationStationSlot) -> bool:
        if not slot.busy or slot.instruction is None:
            return False
        return any(self.is_control_slot(other) for other in self._older_busy_slots(slot))

    def compute_effective_address(self, slot: ReservationStationSlot) -> None:
        if not slot.busy or slot.instruction is None:
            return
        base = slot.Vj if slot.Vj is not None else 0
        slot.address = base + (slot.instruction.immediate or 0)
        slot.value = slot.address

    def can_start_memory_operation(self, slot: ReservationStationSlot) -> bool:
        if not slot.busy or slot.instruction is None:
            return False
        if slot.address is None:
            return False
        if self.is_store_slot(slot):
            return not any(self.is_memory_slot(other) and other.address == slot.address for other in self._older_busy_slots(slot))
        return not any(other.instruction.is_store and other.address == slot.address for other in self._older_busy_slots(slot))

    def update_operand_availability(self, slot: ReservationStationSlot) -> None:
        if not slot.busy or slot.instruction is None:
            return
        if slot.Qj is not None:
            if not self.registers.is_producer_pending(slot.instruction.src1, slot.Qj):
                slot.Vj = self.registers.read(slot.instruction.src1)
                slot.Qj = None
        if slot.Qk is not None:
            if not self.registers.is_producer_pending(slot.instruction.src2, slot.Qk):
                slot.Vk = self.registers.read(slot.instruction.src2)
                slot.Qk = None

    def perform_store(self, slot: ReservationStationSlot) -> None:
        address = slot.address
        value = slot.Vk
        self.memory.store(address, value)

    def compute_result(self, slot: ReservationStationSlot) -> int:
        instr = slot.instruction
        a = slot.Vj if slot.Vj is not None else 0
        b = slot.Vk if slot.Vk is not None else 0
        if instr.mnemonic == "add":
            return (a + b) & 0xFFFF
        if instr.mnemonic == "sub":
            return (a - b) & 0xFFFF
        if instr.mnemonic == "and":
            return a & b
        if instr.mnemonic == "mul":
            return (a * b) & 0xFFFF
        if instr.mnemonic == "load":
            if slot.address is None:
                raise ValueError("Load address must be computed before result")
            return self.memory.load(slot.address)
        raise ValueError(f"Unhandled write result for {instr.mnemonic}")

    def cleanup_slot(self, slot: ReservationStationSlot) -> None:
        slot.busy = False

    def broadcast_result(self, FU_name: Optional[str], value: int) -> None:
        if FU_name is None:
            return
        for Opp in self.rs.stations.values():
            for slot in Opp:
                if not slot.busy:
                    continue
                if slot.Qj == FU_name:
                    slot.Vj = value
                    slot.Qj = None
                if slot.Qk == FU_name:
                    slot.Vk = value
                    slot.Qk = None

    def jump_to_target(self, target_pc: Optional[int], preserve_range: Optional[tuple] = None) -> None:
        if target_pc is None:
            return
        if target_pc not in self.program_index:
            raise ValueError(f"Target PC {target_pc} not found in program")
        target_index = self.program_index[target_pc]
        if target_index < self.next_issue_index:
            for instr in self.instructions[target_index:]:
                if preserve_range is not None:
                    start, end = preserve_range
                    if start is not None and start <= instr.pc < end:
                        continue
                instr.issued_cycle = None
                instr.start_cycle = None
                instr.finish_cycle = None
                instr.write_cycle = None
                instr.completed = False
                instr.flushed = 0
        self.next_issue_index = target_index

    def _flush_slot(self, slot: ReservationStationSlot) -> None:
        slot.instruction.flushed = 1
        if slot.instruction.has_dest() and slot.name is not None:
            self.registers.remove_pending_producer(slot.instruction.dest, slot.name)
        self.cleanup_slot(slot)

    def flush_wrong_path(self, branch_pc: int, target_pc: Optional[int] = None) -> None:
        for slot in self.get_all_slots():
            if not slot.busy or slot.inst_pc is None or slot.instruction is None:
                continue
            if target_pc is None:
                if slot.inst_pc > branch_pc:
                    self._flush_slot(slot)
            else:
                if target_pc > branch_pc:
                    if branch_pc < slot.inst_pc < target_pc:
                        self._flush_slot(slot)
                else:
                    if slot.inst_pc > branch_pc:
                        self._flush_slot(slot)

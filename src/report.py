from simulator import Simulator


class Report:
    @staticmethod
    def print_table(simulator: Simulator) -> None:
        print("\nInstruction timing table:")
        print("pc\tinst\tissued\tstart\tfinish\twrite")
        for instr in sorted(simulator.instructions, key=lambda i: i.pc):
            if instr.flushed or instr.issued_cycle is None:
                continue
            print(
                f"{instr.pc}\t{instr.raw_text}\t{instr.issued_cycle}\t"
                f"{instr.start_cycle or '-'}\t{instr.finish_cycle or '-'}\t{instr.write_cycle or '-'}"
            )

    @staticmethod
    def print_summary(simulator: Simulator) -> None:
        cycles = simulator.cycle
        ipc = simulator.completed_count / cycles if cycles else 0.0
        branch_pct = (
            simulator.mispredictions / simulator.branch_count * 100
            if simulator.branch_count
            else 0.0
        )
        print("\nSimulation summary:")
        print(f"Cycles spanned: {cycles}")
        print(f"Instructions completed: {simulator.completed_count}")
        print(f"IPC: {ipc:.4f}")
        print(f"Conditional branches: {simulator.branch_count}")
        print(f"Branch misprediction percentage: {branch_pct:.2f}%")

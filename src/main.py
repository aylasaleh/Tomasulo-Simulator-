import json
import sys

from parser import parse_program
from simulator import Simulator
from report import Report


def main():
    if len(sys.argv) != 2:
        print("Usage: python src/main.py <input.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    instructions, memory_init = parse_program(payload)
    simulator = Simulator(instructions, memory_init)
    simulator.run()

    Report.print_table(simulator)
    Report.print_summary(simulator)


if __name__ == "__main__":
    main()

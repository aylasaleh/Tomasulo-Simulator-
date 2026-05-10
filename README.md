# Tomasulo Simulator

A simple Tomasulo-style simulator for a 16-bit RISC processor.

## Purpose

This project simulates a simplified out-of-order 16-bit RISC processor using Tomasulo's algorithm without a reorder buffer or separate commit stage.

The simulator takes a JSON input describing the program and initial memory contents, executes the program with:
- issue stage (1 cycle)
- execute stage (latency per functional unit)
- write stage (1 cycle except for stores)

It reports per-instruction issue/execute/write cycles, total execution cycles, IPC, and branch misprediction percentage.

## Input format

The simulator accepts a JSON file with two top-level fields:

- `instructions`: an array of instruction objects
- `memory`: an optional array of initial memory entries

Each instruction object should include:
- `pc`: integer program counter
- `text`: assembly text, e.g. `"add r0,r1,r2"`

Example:

```json
{
  "instructions": [
    {"pc": 1, "text": "add r0,r1,r2"},
    {"pc": 2, "text": "call 5"}
  ],
  "memory": [
    {"address": 10, "value": 42}
  ]
}
```

### Notes

- The instruction mnemonic identifies the functional unit.
- Branch and call targets may be specified using numeric PC values.
- If your front-end uses a text editor in a web interface, this JSON format is ideal.

### Assumptions

- Branches are predicted not-taken and are resolved in write-back.
- There is no reorder buffer or separate commit stage.
- Loads and stores issue to reservation stations and require 2 cycles to compute the effective address before memory execution.
- Stores execute only when there are no older memory operations on the same address, and loads wait for prior stores to the same address.
- Calls/returns are handled as control operations with explicit target update and path flushing.
- A flushed instruction is removed from the reservation station and will be re-issued from the target path if needed.

### Testing

From the workspace root, run the unit test module with `src` on `PYTHONPATH`:

```bash
PYTHONPATH=src python -m unittest tests.test_simulator -v
```

Or run the test file directly:

```bash
PYTHONPATH=src python tests/test_simulator.py
```

If you want to run all tests in the repository, use:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## Running

From the workspace root:

```bash
python src/main.py data/sample_program.json
```

## Project layout

- `src/` — main simulator code
- `data/` — sample input files
- `tests/` — unit test skeletons
- `docs/` — design notes and documentation

## Sample programs

The `data/` folder now includes several example workloads:

- `sample_program.json` — a mixed example with branch and call/return flow
- `arithmetic_only.json` — dependent arithmetic chain
- `branch_taken.json` — a taken conditional branch and misprediction case
- `load_store_hazard.json` — load/store ordering with address conflict
- `call_return.json` — call/return control flow

Run them with:

```bash
python src/main.py data/branch_taken.json
```

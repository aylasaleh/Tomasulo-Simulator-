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

### Command-line Mode (Terminal)

From the workspace root:

```bash
python src/main.py data/sample_program.json
```

### GUI Mode

Launch the interactive graphical interface:

```bash
PYTHONPATH=src python3 src/gui.py
```

The GUI provides a visual step-through debugger and performance metrics display.

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

## GUI Usage Guide

### Launching the GUI

```bash
PYTHONPATH=src python3 src/gui.py
```

This opens an interactive window with a visual representation of the simulator state.

### Interface Overview

**Left Panel:**
- **Program Input**: Text editor for pasting JSON or assembly code
- **Starting PC**: Spinbox to set the starting program counter (default: 1) — applies only to assembly format
- **Instruction Timing Table**: Shows issue/execute/write cycle timings for each instruction
- **Performance Metrics**: Displays IPC, branch misprediction rate, and total cycles

**Right Panel (Tabbed Interface):**
- **Reservation Stations**: Shows all active operations by functional unit type
- **Registers**: Displays current register file values (r0–r7)
- **Memory**: Shows memory contents and write operations

### Loading and Parsing Programs

#### Method 1: Open JSON File
1. Click the **Open JSON** button (top toolbar)
2. Select a `.json` file from the `data/` folder
3. The program automatically loads and displays instruction count

#### Method 2: Paste JSON Code
1. Paste JSON code into the **Program Input** editor
2. Click **Parse** button
3. GUI auto-detects JSON format and loads the program

#### Method 3: Write Assembly Code
1. Paste or type assembly instructions in the **Program Input** editor (one per line)
2. Optional: Set **Starting PC** spinbox to desired value (e.g., 100 for PC 100, 101, 102, ...)
3. Click **Parse** button
4. GUI auto-detects assembly format (if JSON parsing fails) and loads the program

**Assembly Format Example:**
```
add r1,r0,r0
add r2,r0,r1
load r3,0(r2)
beq r3,r1,6
mul r4,r2,r3
ret
```

### Simulation Control

- **Step**: Execute one cycle and update all displays
- **Run**: Auto-advance simulation at 300ms per cycle until completion
- **Pause**: Stop auto-execution (appears as ⏸ when running)
- **Reset**: Clear and reload the current program (if JSON format; assembly requires re-parsing)
- **Cycle Counter**: Displays current cycle number

### Understanding the Display

**Instruction Timing Table:**
- `PC`: Program counter
- `Issue`: Cycle when instruction entered issue stage
- `Execute`: Cycle when instruction entered execute stage
- `Write`: Cycle when instruction completed write stage
- `FU`: Functional unit type (LOAD, STORE, BEQ, CALL_RET, ADD_SUB, AND, MUL)
- Status indicators: ✓ (completed), → (in flight), ⏱ (waiting)

**Reservation Stations Tab:**
- Shows each reservation station slot with:
  - Instruction mnemonic
  - Operand tags (Qj, Qk — producer station IDs or "—" if ready)
  - Immediate operand values
  - Effective address (for memory ops)
  - Remaining execution cycles
  - Current stage (ISSUE, EXECUTE, WRITE)

**Registers Tab:**
- Shows r0–r7 with current values
- Highlight indicates recently updated register

**Memory Tab:**
- Shows memory contents at queried addresses
- Tracks load/store operations and their timings

**Performance Metrics:**
- **IPC** (Instructions Per Cycle): Throughput = completed instructions ÷ total cycles
- **Mispredictions**: Count and percentage of branch mispredictions
- **Total Cycles**: Overall simulation duration

### Tips

- Use **Step** to trace through small programs instruction-by-instruction
- Use **Run** to quickly execute large programs and see final results
- Check the **Reservation Stations** tab to understand pipeline stalls and dependencies
- Monitor **Starting PC** when testing assembly code from different entry points
- Click **Reset** to reload the same program with different settings (for JSON only)

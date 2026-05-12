import re
from typing import Any, Dict, List, Tuple

from instruction import Instruction

REGISTER_PATTERN = re.compile(r"^r([0-7])$")
LOAD_STORE_PATTERN = re.compile(r"^(load|store)\s+(r[0-7])\s*,\s*([-]?[0-9]+)\s*\(\s*(r[0-7])\s*\)$", re.IGNORECASE)


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError:
        raise ValueError(f"Invalid integer literal: {value}")


def parse_register(token: str) -> str:
    token = token.strip().lower()
    match = REGISTER_PATTERN.match(token)
    if not match:
        raise ValueError(f"Invalid register: {token}")
    return f"r{match.group(1)}"


def normalize_text(text: str) -> str:
    text = text.strip()
    match = re.match(r"^(\d+)\s+(.*)$", text)
    if match:
        return match.group(2).strip()
    return text


def parse_instruction_line(pc: int, text: str) -> Instruction:
    raw_text = text.strip()
    text = normalize_text(raw_text)
    tokens = [token.strip() for token in re.split(r"[\s,]+", text) if token.strip()]
    if not tokens:
        raise ValueError(f"Empty instruction text at PC={pc}")

    mnemonic = tokens[0].lower()
    instruction = Instruction(pc=pc, mnemonic=mnemonic, raw_text=raw_text)

    if mnemonic == "ret":
        return instruction

    if mnemonic == "call":
        if len(tokens) != 2:
            raise ValueError(f"CALL requires 1 operand at PC={pc}")
        instruction.target = parse_int(tokens[1])
        instruction.dest = "r1"
        return instruction

    if mnemonic == "beq":
        if len(tokens) != 4:
            raise ValueError(f"BEQ requires 3 operands at PC={pc}")
        instruction.src1 = parse_register(tokens[1])
        instruction.src2 = parse_register(tokens[2])
        instruction.target = parse_int(tokens[3])
        return instruction

    if mnemonic in {"add", "sub", "and", "mul"}:
        if len(tokens) != 4:
            raise ValueError(f"{mnemonic.upper()} requires 3 operands at PC={pc}")
        instruction.dest = parse_register(tokens[1])
        instruction.src1 = parse_register(tokens[2])
        instruction.src2 = parse_register(tokens[3])
        return instruction

    match = LOAD_STORE_PATTERN.match(text)
    if match:
        instruction.mnemonic = match.group(1).lower()
        instruction.dest = parse_register(match.group(2)) if instruction.mnemonic == "load" else parse_register(match.group(2))
        instruction.src1 = parse_register(match.group(4))
        instruction.immediate = parse_int(match.group(3))
        if mnemonic == "store":
            instruction.dest = None
            instruction.src2 = parse_register(match.group(2))
        return instruction

    raise ValueError(f"Unknown instruction format at PC={pc}: '{raw_text}'")


def parse_program(payload: Dict[str, Any]) -> Tuple[List[Instruction], Dict[int, int]]:
    instructions_data = payload.get("instructions")
    if instructions_data is None:
        raise ValueError("Input JSON must contain an 'instructions' array")

    instructions = []
    for entry in instructions_data:
        if isinstance(entry, str):
            stripped = entry.strip()
            match = re.match(r"^(\d+)\s+(.*)$", stripped)
            if not match:
                raise ValueError(f"Unable to parse instruction string: {entry}")
            pc = int(match.group(1), 0)
            text = match.group(2)
        elif isinstance(entry, dict):
            if "pc" not in entry or "text" not in entry:
                raise ValueError("Each instruction object must contain 'pc' and 'text'")
            pc = int(entry["pc"])
            text = str(entry["text"])
        else:
            raise ValueError("Instruction entries must be objects or strings")

        instructions.append(parse_instruction_line(pc, text))

    instructions.sort(key=lambda instr: instr.pc)

    memory_init = {}
    for entry in payload.get("memory", []):
        if not isinstance(entry, dict) or "address" not in entry or "value" not in entry:
            raise ValueError("Memory entries must be objects with 'address' and 'value'")
        address = int(entry["address"])
        value = int(entry["value"])
        memory_init[address] = value

    return instructions, memory_init


def parse_assembly(code: str, start_pc: int = 1) -> Tuple[List[Instruction], Dict[int, int]]:
    """
    Parse assembly code format where each line is an instruction.
    Lines are automatically numbered starting from start_pc.
    Empty lines and lines starting with '#' are comments/skipped.
    Returns (instructions, memory_init) tuple.
    """
    instructions = []
    pc = start_pc
    
    for line in code.split('\n'):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Parse the instruction with auto-assigned PC
        try:
            instructions.append(parse_instruction_line(pc, line))
            pc += 1
        except ValueError as e:
            raise ValueError(f"Error on line {pc}: {e}")
    
    # Memory is always empty for assembly format
    return instructions, {}

import glob
import json
import os
import unittest

from parser import parse_program
from simulator import Simulator


def load_sample(name):
    path = os.path.join(os.path.dirname(__file__), "..", "data", name)
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    instructions, memory = parse_program(payload)
    sim = Simulator(instructions, memory)
    sim.run()
    return sim, instructions


class SimulatorSampleTests(unittest.TestCase):
    def test_sample_program_runs(self):
        sim, _ = load_sample("sample_program.json")
        self.assertGreater(sim.completed_count, 0)
        self.assertGreaterEqual(sim.cycle, 1)
        self.assertEqual(sim.branch_count, 1)

    def test_arithmetic_only_results(self):
        sim, _ = load_sample("arithmetic_only.json")
        self.assertEqual(sim.cycle, 22)
        self.assertEqual(sim.completed_count, 5)
        self.assertEqual(sim.branch_count, 0)
        self.assertEqual(sim.mispredictions, 0)

    def test_branch_taken_misprediction(self):
        sim, instructions = load_sample("branch_taken.json")
        self.assertEqual(sim.cycle, 11)
        self.assertEqual(sim.completed_count, 4)
        self.assertEqual(sim.branch_count, 1)
        self.assertEqual(sim.mispredictions, 1)
        self.assertIsNone(next(instr for instr in instructions if instr.pc == 4).start_cycle)
        self.assertIsNone(next(instr for instr in instructions if instr.pc == 5).start_cycle)

    def test_load_store_hazard(self):
        sim, instructions = load_sample("load_store_hazard.json")
        self.assertEqual(sim.cycle, 21)
        self.assertEqual(sim.completed_count, 5)
        self.assertEqual(sim.branch_count, 0)
        self.assertEqual(sim.mispredictions, 0)
        load_instr = next(instr for instr in instructions if instr.pc == 4)
        store_instr = next(instr for instr in instructions if instr.pc == 3)
        self.assertEqual(store_instr.finish_cycle, 14)
        self.assertEqual(load_instr.start_cycle, 14)

    def test_three_iteration_loop(self):
        sim, instructions = load_sample("loop_three_times.json")
        self.assertEqual(sim.completed_count, 20)
        self.assertEqual(sim.branch_count, 6)
        self.assertEqual(sim.mispredictions, 3)
        self.assertEqual(sim.registers.read("r1"), 0)
        self.assertEqual(sim.registers.read("r7"), 0)
        self.assertTrue(all(instr.completed for instr in instructions))

    def test_call_return_sequence(self):
        sim, instructions = load_sample("call_return.json")

        self.assertEqual(sim.completed_count, 6)
        self.assertEqual(sim.branch_count, 0)      
        self.assertEqual(sim.mispredictions, 0)
        self.assertEqual(sum(1 for instr in instructions if instr.completed), 6)


    def test_loop_with_waw_war_hazards(self):
        sim, instructions = load_sample("loop_hazards.json")
        self.assertEqual(sim.cycle, 42)
        self.assertEqual(sim.completed_count, 27)
        self.assertEqual(sim.branch_count, 9)
        self.assertEqual(sim.mispredictions, 5)


if __name__ == "__main__":
    unittest.main()

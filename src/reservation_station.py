from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ReservationStationSlot:
    name: str

    busy: bool = False

    op: Optional[str] = None

    #ISSUE EXECUTE WRITE
    stage: Optional[str] = None

    rem_cycles: Optional[int] = None

    # Instruction PC
    inst_pc: Optional[int] = None

    # Operand values
    Vj: Optional[str] = None
    Vk: Optional[str] = None

    # name of producing station
    Qj: Optional[str] = None
    Qk: Optional[str] = None

    # Extra fields useful for loads/stores/branches
    address: Optional[int] = None
    immediate: Optional[int] = None
    
    # final output 
    value: Optional[int] = None

    # Full instruction text
    instruction: Optional[str] = None

    def flush(self):
        self.busy = False
        self.op = None

        self.instruction_pc = None

        self.Vj = None
        self.Vk = None

        self.Qj = None
        self.Qk = None

        self.address = None
        self.immediate = None

        self.instruction = None


class ReservationStations:

    OPERATION_TO_UNIT = {
        "LOAD": "LOAD",
        "STORE": "STORE",

        "BEQ": "BEQ",

        "CALL": "CALL_RET",
        "RET": "CALL_RET",

        "ADD": "ADD_SUB",
        "SUB": "ADD_SUB",

        "AND": "AND",

        "MUL": "MUL",
    }

    def __init__(self):

        self.stations = {

            "LOAD": [
                ReservationStationSlot("LOAD1"),
                ReservationStationSlot("LOAD2"),
            ],

            "STORE": [
                ReservationStationSlot("STORE1"),
                ReservationStationSlot("STORE2"),
            ],

            "BEQ": [
                ReservationStationSlot("BEQ1"),
                ReservationStationSlot("BEQ2"),
            ],

            "CALL_RET": [
                ReservationStationSlot("CALL_RET1"),
            ],

            "ADD_SUB": [
                ReservationStationSlot("ADD_SUB1"),
                ReservationStationSlot("ADD_SUB2"),
                ReservationStationSlot("ADD_SUB3"),
                ReservationStationSlot("ADD_SUB4"),
            ],

            "AND": [
                ReservationStationSlot("AND1"),
                ReservationStationSlot("AND2"),
            ],

            "MUL": [
                ReservationStationSlot("MUL1"),
            ],
        }

    def get_free_station(self, unit_type: str):
        """
        Returns first free station for a unit type.
        """

        if unit_type not in self.stations:
            return None

        for station in self.stations[unit_type]:

            if not station.busy:
                return station

        return None


    def flush_younger_than(
        self,
        branch_pc: int
    ):
        for entries in self.stations.values():

            for station in entries:

                if (station.busy and station.inst_pc is not None and station.int_pc > branch_pc):
                    station.flush()
        return

    def print_status(self):

        for unit_type, entries in self.stations.items():

            print(f"\n=== {unit_type} ===")

            for rs in entries:

                print(
                    f"{rs.name:10} | "
                    f"Busy={rs.busy} | "
                    f"PC={rs.instruction_pc} | "
                    f"Op={rs.op}"
                )

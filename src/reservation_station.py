from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ReservationStationSlot:
    name: str

    busy: bool = False

    op: Optional[str] = None

    #ISSUE EXECUTE WRITE
    stage: Optional[str] = None
    value: Optional[int] = None

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
    
    # Full instruction text
    instruction: Optional[str] = None
    
    # Functional unit type
    fu_type: Optional[str] = None
    
    # Address computation cycles remaining (for loads/stores)
    addr_comp_cycles_remaining: Optional[int] = None

    def flush(self):
        self.busy = False


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

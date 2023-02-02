from __future__ import annotations

import string
from enum import Enum


class RamUnit(Enum):
    """1000 KB = 1MB"""

    B = 1.0
    KB = 10.0**3
    MB = 10.0**6
    GB = 10.0**9
    TB = 10.0**12


class Ram:
    def __init__(self, value: float = 0.0, unit: str | RamUnit = RamUnit.B) -> None:
        self.value = value
        if isinstance(unit, RamUnit):
            self.unit = unit
        elif unit in RamUnit.__members__:
            self.unit = RamUnit[unit.upper()]
        elif unit in ["KiB", "MiB", "GiB", "TiB"]:
            self.value *= 1.048588
            self.unit = RamUnit[unit.replace("i", "").upper()]
        else:
            from .spgio import MessageHandler

            MessageHandler().error(f"Invalid memory unit: {unit}")
            exit()

    @classmethod
    def from_string(cls, ram_str: str) -> Ram:
        value = "".join(
            char for char in ram_str if char in string.digits + string.punctuation
        )
        unit = "".join(char for char in ram_str if char in string.ascii_letters)

        ram = Ram()
        if unit in RamUnit.__members__:
            ram.value = float(value)
            ram.unit = RamUnit[unit]
        elif unit in ["KiB", "MiB", "GiB", "TiB"]:
            ram.value = float(value) * 1.048588
            ram.unit = RamUnit[unit.replace("i", "")]

        return ram

    @property
    def byte(self) -> float:
        return self.value * self.unit.value

    def to_human_readable(self) -> None:
        for unit in RamUnit:
            value = self.byte / unit.value
            if 1.0 <= value < 1_000.0:
                self.value = value
                self.unit = unit
                break

    def __sub__(self, other: Ram) -> Ram:
        ram = Ram(max(0.0, self.byte - other.byte))
        ram.to_human_readable()
        return ram

    def __truediv__(self, other: Ram) -> float:
        return self.byte / other.byte

    def __eq__(self, other: Ram) -> bool:
        return self.byte == other.byte

    def __gt__(self, other: Ram) -> bool:
        return self.byte > other.byte

    def __str__(self) -> str:
        self.to_human_readable()
        return f"{self.value:.1f}{self.unit.name}"

    def __format__(self, _: str) -> str:
        return self.__str__()

from __future__ import annotations

import math
from enum import Enum

from .name import extract_alphabet, extract_number


class Byte(Enum):
    B = 1
    KB = 10**3
    MB = 10**6
    GB = 10**9
    TB = 10**12


class BinaryByte(Enum):
    B = 1
    KiB = 2**10
    MiB = 2**20
    GiB = 2**30
    TiB = 2**40


class Ram:
    def __init__(self, value: float = 0.0, unit: str | Byte = Byte.B) -> None:
        if isinstance(unit, Byte):
            self.value, self.unit = value, unit
        elif unit in Byte.__members__:
            self.value, self.unit = value, Byte[unit]
        elif unit in BinaryByte.__members__:
            self.value = value * BinaryByte[unit].value
            self.unit = Byte.B
        else:
            from .spgio import MessageHandler

            MessageHandler().error(f"Invalid memory unit: {unit}")
            exit()

    @classmethod
    def from_string(cls, ram_str: str) -> Ram:
        """Create ram obejct from string
        e.g., '7.6GiB' -> value = 8.16, unit = GB
        """
        value = float(extract_number(ram_str))
        unit = extract_alphabet(ram_str)

        if unit in Byte.__members__:
            return cls(value, Byte[unit])
        elif unit in BinaryByte.__members__:
            return cls(value * BinaryByte[unit].value, Byte.B)
        raise ValueError(f"Invalid ram unit: {unit}")

    @property
    def byte(self) -> float:
        return self.value * self.unit.value

    def to_human_readable(self) -> Ram:
        """Change to human-readable format: 7.5MB, 256GB, ..."""
        byte = self.byte
        unit_idx = int(math.log(byte, 1000))

        self.unit = list(Byte)[unit_idx]
        self.value = byte / self.unit.value
        return self

    def __sub__(self, other: Ram) -> Ram:
        ram = Ram(max(0.0, self.byte - other.byte))
        return ram.to_human_readable()

    def __truediv__(self, other: Ram) -> float:
        return self.byte / other.byte

    def __eq__(self, other: Ram) -> bool:
        return self.byte == other.byte

    def __gt__(self, other: Ram) -> bool:
        return self.byte > other.byte

    def __ge__(self, other: Ram) -> bool:
        return self.byte >= other.byte

    def __str__(self) -> str:
        self.to_human_readable()
        return f"{self.value:.1f}{self.unit.name}"

    def __format__(self, _: str) -> str:
        self.to_human_readable()
        return f"{self.value:.1f}{self.unit.name}"


from __future__ import annotations

import math
from dataclasses import dataclass
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


@dataclass(slots=True)
class Ram:
    value: float = 0.0
    unit: Byte | BinaryByte = Byte.B

    @classmethod
    def from_string(cls, ram: str) -> Ram:
        """Create ram obejct from string
        e.g., '7.6GiB' -> value = 8.16, unit = GB
        """
        value = float(extract_number(ram))
        unit = extract_alphabet(ram)

        if unit in Byte.__members__:
            return cls(value, Byte[unit])
        elif unit in BinaryByte.__members__:
            return cls(value, BinaryByte[unit])
        raise ValueError(f"Invalid ram unit: {unit}")

    @property
    def byte(self) -> float:
        """Value in Byte unit"""
        return self.value * self.unit.value

    def __sub__(self, other: Ram) -> Ram:
        return Ram(max(0.0, self.byte - other.byte), Byte.B)

    def __truediv__(self, other: Ram) -> float:
        return self.byte / other.byte

    def __eq__(self, other: Ram) -> bool:
        return self.byte == other.byte

    def __gt__(self, other: Ram) -> bool:
        return self.byte > other.byte

    def __ge__(self, other: Ram) -> bool:
        return self.byte >= other.byte

    def __format__(self, _: str) -> str:
        """
        Change to human-readable format with Byte unit
        e.g.,  7.5MB, 256GB, ...
        """
        if self.byte == 0.0:
            return "0.0B"

        byte = self.byte

        # Get proper unit
        unit_idx = int(math.log(byte, 1000))
        unit = list(Byte)[unit_idx]

        # Get proper value for the given unit
        value = byte / unit.value
        return f"{value:.1f}{unit.name}"

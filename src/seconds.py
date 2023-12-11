from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TimeUnit(Enum):
    s = 1
    m = 60
    h = 60 * 60
    d = 60 * 60 * 24
    w = 60 * 60 * 24 * 7


@dataclass(slots=True)
class Seconds:
    value: int = 0
    unit: TimeUnit = TimeUnit.s

    @classmethod
    def from_input(cls, input_times: list[str]) -> Seconds:
        """1w 2d 3h 40m 56s to Seconds"""
        return sum(
            [
                cls(int(input_time[:-1]), TimeUnit[input_time[-1]])
                for input_time in input_times
            ],
            start=cls(),
        )

    @classmethod
    def from_ps(cls, ps_times: str) -> Seconds:
        """ps time format [DD-]HH:MM:SS to Seconds"""
        seconds = sum(
            [
                cls(int(ps_time), unit)
                for ps_time, unit in zip(
                    reversed(ps_times.replace("-", ":").split(":")), TimeUnit
                )
            ],
            start=cls(),
        )
        return seconds

    @property
    def second(self) -> int:
        return self.value * self.unit.value


    def __nonzero__(self):
        return self.second != 0

    def __add__(self, other: Seconds) -> Seconds:
        return Seconds(self.second + other.second)

    def __eq__(self, other: Seconds) -> bool:
        return self.second == other.second

    def __gt__(self, other: Seconds) -> bool:
        return self.second > other.second

    def __ge__(self, other: Seconds) -> bool:
        return self.second >= other.second

    def __format__(self, format_spec: str) -> str:
        readable: dict[TimeUnit, float] = {}
        second = self.second

        for unit in reversed(TimeUnit):
            readable[unit] = second // unit.value
            second %= unit.value

        if format_spec == "ps":
            formatted = "{:02d}:{:02d}:{:02d}".format(
                readable[TimeUnit.h], readable[TimeUnit.m], readable[TimeUnit.s]
            )

            readable[TimeUnit.d] += 7 * readable[TimeUnit.w]
            if readable[TimeUnit.d]:
                return f"{readable[TimeUnit.d]:02d}-{formatted}"
            else:
                return formatted

        elif format_spec == "human":
            formatted = " ".join(
                f"{value}{unit.name}" for unit, value in readable.items() if value != 0
            )

            # When 0 seconds, readable is empty string
            if not formatted:
                formatted = "0s"
            return formatted
        raise ValueError(f"No such time format: {format_spec}")

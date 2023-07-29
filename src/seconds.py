from __future__ import annotations

from enum import Enum


class TimeUnit(Enum):
    s = 1
    m = 60
    h = 60 * 60
    d = 60 * 60 * 24
    w = 60 * 60 * 24 * 7


class Seconds:
    def __init__(self, value: int | str = 0, unit: str | TimeUnit = TimeUnit.s) -> None:
        if isinstance(value, str):
            value = int(value)
        if isinstance(unit, str):
            unit = TimeUnit[unit]
        self.value = value * unit.value

    @classmethod
    def from_input(cls, input_times: list[str]) -> Seconds:
        """1w 2d 3h 40m 56s to Seconds"""
        return sum(
            [cls(input_time[:-1], input_time[-1]) for input_time in input_times],
            start=cls(),
        )


    @classmethod
    def from_ps(cls, ps_times: str) -> Seconds:
        """ps time format [DD-]HH:MM:SS to Seconds"""
        seconds = sum(
            [
                cls(ps_time, unit)
                for ps_time, unit in zip(
                    reversed(ps_times.replace("-", ":").split(":")), TimeUnit
                )
            ],
            start=cls(),
        )
        return seconds

    def to_human_readable(self) -> dict[TimeUnit, int]:
        human_readable = {}
        seconds = self.value

        human_readable[TimeUnit.w] = seconds // TimeUnit.w.value
        seconds %= TimeUnit.w.value

        human_readable[TimeUnit.d] = seconds // TimeUnit.d.value
        seconds %= TimeUnit.d.value

        human_readable[TimeUnit.h] = seconds // TimeUnit.h.value
        seconds %= TimeUnit.h.value

        human_readable[TimeUnit.m] = seconds // TimeUnit.m.value
        seconds %= TimeUnit.m.value

        human_readable[TimeUnit.d.s] = seconds
        return human_readable

    def __add__(self, other: Seconds) -> Seconds:
        return Seconds(self.value + other.value)

    def __eq__(self, other: Seconds) -> bool:
        return self.value == other.value

    def __gt__(self, other: Seconds) -> bool:
        return self.value > other.value

    def __ge__(self, other: Seconds) -> bool:
        return self.value >= other.value

    def __str__(self) -> str:
        return f"{self.value} seconds"

    def __repr__(self) -> str:
        return f"{self.value} seconds"

    def __format__(self, format_spec: str) -> str:
        readable = self.to_human_readable()
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
        else:
            raise ValueError(f"No such time format: {format_spec}")

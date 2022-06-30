from enum import Enum, auto


class Option(Enum):
    list = auto()
    free = auto()
    job = auto()
    user = auto()
    run = auto()
    runs = auto()
    KILL = auto()


if __name__ == "__main__":
    print("This is module option at spg")

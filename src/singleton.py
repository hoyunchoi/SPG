from typing import Any


class Singleton(type):
    """
    Singleton pattern
    This is sub-optimal but used until finding a good alternative.
    """

    _instances: dict[Any, Any] = {}

    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwds)
        return cls._instances[cls]


if __name__ == "__main__":
    print("This is module Singleton from SPG")

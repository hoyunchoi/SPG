from typing import Any

class Singleton(type):
    """
        Singleton pattern
        Not recommanded but use until find good alternatives
    """
    _instances = {}
    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwds)
        return cls._instances[cls]
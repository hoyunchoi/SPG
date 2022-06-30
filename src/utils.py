import re


def get_machine_group(name: str) -> str:
    """Return group name which the machine is at"""
    return re.sub("[0-9]", "", name)


def get_machine_index(name: str) -> int:
    """
    Get index of machine.
    ex) tenet100 -> 100
    """
    return int(re.sub("[^0-9]", "", name))


def get_mem_with_unit(mem: str | float, unit: str) -> str:
    """
    Change memory in KB unit to MB or GB
    Args
        mem: memory utilization in KB unit
        unit: Unit of input mem
    Return
        memory utilization in MB or GB unit
    """
    if isinstance(mem, str):
        mem = float(mem)
    unit_list = ["KB", "MB", "GB", "TB"]
    try:
        idx = unit_list.index(unit)
    except ValueError:
        from .output import MessageHandler

        MessageHandler().error(f"Invalid memory unit: {unit}")
        exit()

    for unit in unit_list[idx:]:
        if mem < 1000.0:
            break
        mem /= 1000.0

    return f"{mem:.1f}{unit}"


def input_time_to_seconds(time: list[str]) -> int:
    """Input time format to seconds"""
    unit_to_second = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    try:
        return sum(int(t[:-1]) * unit_to_second[t[-1]] for t in time)
    except (KeyError, ValueError):
        from .output import MessageHandler

        MessageHandler().error(f"Invalid time window: {' '.join(time)}")
        MessageHandler().error("Run 'spg KILL -h' for more help")
        exit()


def ps_time_to_seconds(time: str) -> int:
    """ps time format [DD-]HH:MM:SS to seconds"""
    to_second_list = [1, 60, 3600, 62400]  # second, minute, hour, day

    # [DD-]HH:MM:SS -> [DD:]HH:MM:SS -> list
    time_list = time.replace("-", ":").split(":")

    return sum(
        int(time) * to_second
        for time, to_second in zip(reversed(time_list), to_second_list)
    )


def yes_no(msg: str | None = None) -> bool:
    """
    Get input yes or no
    If other input is given, ask again for 5 times
    'yes', 'y', 'Y', ... : pass
    'no', 'n', 'No', ... : fail
    """
    # Print message first if given
    if msg is not None:
        print(msg)

    # Ask 5 times
    for _ in range(5):
        reply = str(input("(y/n): ")).strip().lower()
        if reply[0] == "y":
            return True
        elif reply[0] == "n":
            return False
        print("You should provied either 'y' or 'n'", end=" ")
    return False


if __name__ == "__main__":
    print("This is module utils from SPG")

import string


def extract_number(target: str) -> str:
    return "".join(
        char for char in target if char in string.digits + string.punctuation
    )


def extract_alphabet(target: str) -> str:
    return "".join(char for char in target if char in string.ascii_letters)


def get_machine_index(machine_name: str) -> int:
    """
    Get index of machine.
    e.g., tenet100 -> 100
    """
    return int(extract_number(machine_name))


if __name__ == "__main__":
    print("This is module name from SPG")

#! /usr/bin/python
from src import SPG, Argument, get_arguments


def main():
    # Get arguments
    args = Argument(**vars(get_arguments()))

    # Run SPG according to arguments
    spg = SPG(args)
    spg()


if __name__ == "__main__":
    main()

#! /usr/bin/python
from src import SPG, Argument, configure_logger, get_args


def main():
    # Create logger
    configure_logger()

    # Get arguments
    args = Argument(**vars(get_args()))

    # Run SPG according to arguments
    spg = SPG(args)
    spg()


if __name__ == "__main__":
    main()

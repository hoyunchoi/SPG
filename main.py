#! /usr/bin/python
from src import configure_logger, Argument, SPG

def main():
    # Create logger
    configure_logger()

    # Get arguments
    args = Argument().get_args()

    # Run SPG according to arguments
    spg = SPG(args)
    spg()


if __name__ == "__main__":
    main()

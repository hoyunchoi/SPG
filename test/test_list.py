import inspect
import unittest

from src.spg import SPG
from src.argument import Argument
from src.spgio import MessageHandler
from .test_item import TestItem

class TestList(unittest.TestCase):
    """ Test option list and machine/group restriction arguments """
    message_handler = MessageHandler()

    def setUp(self) -> None:
        self.message_handler.clear()

    def test_list(self):
        print(f"\n{inspect.stack()[0][3]}: spg {TestItem.LIST.value}")
        args = Argument.from_input(TestItem.LIST.value)
        spg = SPG(args)
        spg()

    def test_list_machine(self):
        print(f"\n{inspect.stack()[0][3]}: spg {TestItem.LIST_MACHINE.value}")
        args = Argument.from_input(TestItem.LIST_MACHINE.value)
        spg = SPG(args)
        spg()

    def test_list_machines(self):
        print(f"\n{inspect.stack()[0][3]}: spg {TestItem.LIST_MACHINES.value}")
        args = Argument.from_input(TestItem.LIST_MACHINES.value)
        spg = SPG(args)
        spg()

    def test_list_group(self):
        print(f"\n{inspect.stack()[0][3]}: spg {TestItem.LIST_GROUP.value}")
        args = Argument.from_input(TestItem.LIST_GROUP.value)
        spg = SPG(args)
        spg()

    def test_list_machine_group(self):
        print(f"\n{inspect.stack()[0][3]}: spg {TestItem.LIST_MACHINE_GROUP.value}")
        args = Argument.from_input(TestItem.LIST_MACHINE_GROUP.value)
        spg = SPG(args)
        spg()

    def test_list_machine_group_suppress(self):
        print(f"\n{inspect.stack()[0][3]}: spg {TestItem.LIST_MACHINE_GROUP_SUPPRESS.value}")
        args = Argument.from_input(TestItem.LIST_MACHINE_GROUP_SUPPRESS.value)
        spg = SPG(args)
        spg()
        self.assertEqual(len(self.message_handler.warning_list), 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)



import unittest
from unittest.mock import patch

from src.argument import Argument
from src.option import Option
from src.spgio import MessageHandler, MessageType

from .test_item import TestItem


class TestArgument(unittest.TestCase):
    """ Test both get_args and Argument dataclass """
    message_handler = MessageHandler()

    def setUp(self) -> None:
        self.message_handler.clear()

    # option silent
    def test_silent_user(self):
        args = Argument.from_input(TestItem.SILENT_USER.value)
        true_args = Argument(
            silent=True,
            option=Option.user
        )
        self.assertEqual(args, true_args)

    ####################################### Option list #######################################
    def test_list(self):
        args = Argument.from_input(TestItem.LIST.value)
        true_args = Argument(
            option=Option.list
        )
        self.assertEqual(args, true_args)

    def test_list_machine(self):
        args = Argument.from_input(TestItem.LIST_MACHINE.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_list_machines(self):
        args = Argument.from_input(TestItem.LIST_MACHINES.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)

    def test_list_group(self):
        args = Argument.from_input(TestItem.LIST_GROUP.value)
        true_args = Argument(
            option=Option.list,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)

    def test_list_machine_group(self):
        args = Argument.from_input(TestItem.LIST_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_list_machine_group_suppress(self):
        args = Argument.from_input(TestItem.LIST_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)

    ####################################### Option free #######################################
    def test_free(self):
        args = Argument.from_input(TestItem.FREE.value)
        true_args = Argument(
            option=Option.free
        )
        self.assertEqual(args, true_args)

    def test_free_machine(self):
        args = Argument.from_input(TestItem.FREE_MACHINE.value)
        true_args = Argument(
            option=Option.free,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_free_machines(self):
        args = Argument.from_input(TestItem.FREE_MACHINES.value)
        true_args = Argument(
            option=Option.free,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)

    def test_free_group(self):
        args = Argument.from_input(TestItem.FREE_GROUP.value)
        true_args = Argument(
            option=Option.free,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)

    def test_free_machine_group(self):
        args = Argument.from_input(TestItem.FREE_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.free,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_free_machine_group_suppress(self):
        args = Argument.from_input(TestItem.FREE_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.free,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)

    ####################################### Option job #######################################
    def test_job(self):
        args = Argument.from_input(TestItem.JOB.value)
        true_args = Argument(
            option=Option.job
        )
        self.assertEqual(args, true_args)

    def test_job_machine(self):
        args = Argument.from_input(TestItem.JOB_MACHINE.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_job_machines(self):
        args = Argument.from_input(TestItem.JOB_MACHINES.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)

    def test_job_group(self):
        args = Argument.from_input(TestItem.JOB_GROUP.value)
        true_args = Argument(
            option=Option.job,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)

    def test_job_machine_group(self):
        args = Argument.from_input(TestItem.JOB_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_job_machine_group_suppress(self):
        args = Argument.from_input(TestItem.JOB_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)

    def test_job_user(self):
        args = Argument.from_input(TestItem.JOB_USER.value)
        true_args = Argument(
            option=Option.job,
            user='root'
        )
        self.assertEqual(args, true_args)

    def test_job_user_err(self):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.JOB_USER_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 1)

    def test_job_all(self):
        args = Argument.from_input(TestItem.JOB_ALL.value)
        true_args = Argument(
            option=Option.job,
            all=True
        )
        self.assertEqual(args, true_args)

    def test_job_pid(self):
        args = Argument.from_input(TestItem.JOB_PID.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"],
            pid=["1234", "5678"]
        )
        self.assertEqual(args, true_args)

    def test_job_pid_err(self):
        with self.assertRaises(SystemExit) as cm:
            Argument.from_input(TestItem.JOB_PID_ERR.value)
            self.assertEqual(cm.exception, "Pid error")
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 1)

    def test_job_cmd(self):
        args = Argument.from_input(TestItem.JOB_CMD.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)

    def test_job_time(self):
        args = Argument.from_input(TestItem.JOB_TIME.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)

    def test_job_time_err(self):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.JOB_TIME_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 2)

    def test_job_start(self):
        args = Argument.from_input(TestItem.JOB_START.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"],
            start="10:00"
        )
        self.assertEqual(args, true_args)

    ####################################### Option user #######################################
    def test_user(self):
        args = Argument.from_input(TestItem.USER.value)
        true_args = Argument(
            option=Option.user
        )
        self.assertEqual(args, true_args)

    def test_user_machine(self):
        args = Argument.from_input(TestItem.USER_MACHINE.value)
        true_args = Argument(
            option=Option.user,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_user_machines(self):
        args = Argument.from_input(TestItem.USER_MACHINES.value)
        true_args = Argument(
            option=Option.user,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)

    def test_user_group(self):
        args = Argument.from_input(TestItem.USER_GROUP.value)
        true_args = Argument(
            option=Option.user,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)

    def test_user_machine_group(self):
        args = Argument.from_input(TestItem.USER_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.user,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    def test_user_machine_group_suppress(self):
        args = Argument.from_input(TestItem.USER_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.user,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)

    ####################################### Option run #######################################
    def test_run(self):
        args = Argument.from_input(TestItem.RUN.value)
        true_args = Argument(
            option=Option.run,
            machine="tenet1",
            command="python test.py"
        )
        self.assertEqual(args, true_args)

    def test_run_argument(self):
        args = Argument.from_input(TestItem.RUN_ARGUMENT.value)
        true_args = Argument(
            option=Option.run,
            machine="tenet1",
            command="python test.py -N 10"
        )
        self.assertEqual(args, true_args)

    ####################################### Option runs #######################################
    def test_runs(self):
        args = Argument.from_input(TestItem.RUNS.value)
        true_args = Argument(
            option=Option.runs,
            group=["tenet"],
            command="test.txt"
        )
        self.assertEqual(args, true_args)

    def test_runs_boundary(self):
        args = Argument.from_input(TestItem.RUNS_BOUNDARY.value)
        true_args = Argument(
            option=Option.runs,
            group=["tenet", "1", "5"],
            command="test.txt"
        )
        self.assertEqual(args, true_args)

    ####################################### Option KILL #######################################
    @patch("builtins.input", return_value="y")
    def test_KILL(self, mock_input):
        args = Argument.from_input(TestItem.KILL.value)
        true_args = Argument(
            option=Option.KILL,
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="n")
    def test_KILL_abort(self, mock_input):
        with self.assertRaises(SystemExit) as cm:
            Argument.from_input(TestItem.KILL.value)
            self.assertEqual(cm.exception, "Aborting...")

    @patch("builtins.input", return_value="y")
    def test_kill_machine(self, mock_input):
        args = Argument.from_input(TestItem.KILL_MACHINE.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_machines(self, mock_input):
        args = Argument.from_input(TestItem.KILL_MACHINES.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_group(self, mock_input):
        args = Argument.from_input(TestItem.KILL_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_machine_group(self, mock_input):
        args = Argument.from_input(TestItem.KILL_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_machine_group_suppress(self, mock_input):
        args = Argument.from_input(TestItem.KILL_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_user_err(self, mock_input):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.KILL_USER_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 1)

    @patch("builtins.input", return_value="y")
    def test_kill_all_err(self, mock_input):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.KILL_ALL_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 1)

    @patch("builtins.input", return_value="y")
    def test_kill_pid(self, mock_input):
        args = Argument.from_input(TestItem.KILL_PID.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            pid=["1234", "5678"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_pid_err(self, mock_input):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.JOB_PID_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 1)

    @patch("builtins.input", return_value="y")
    def test_kill_cmd(self, mock_input):
        args = Argument.from_input(TestItem.KILL_CMD.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_time(self, mock_input):
        args = Argument.from_input(TestItem.KILL_TIME.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)

    @patch("builtins.input", return_value="y")
    def test_kill_time_err(self, mock_input):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.JOB_TIME_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 2)

    @patch("builtins.input", return_value="y")
    def test_kill_start(self, mock_input):
        args = Argument.from_input(TestItem.KILL_START.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            start="10:00"
        )
        self.assertEqual(args, true_args)

    ##################################### Option machine ######################################
    def test_machine(self):
        args = Argument.from_input(TestItem.MACHINE.value)
        true_args = Argument(
            option=Option.list
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_machine_machine(self):
        args = Argument.from_input(TestItem.MACHINE_MACHINE.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_machine_machines(self):
        args = Argument.from_input(TestItem.MACHINE_MACHINES.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_machine_group(self):
        args = Argument.from_input(TestItem.MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.list,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_machine_machine_group(self):
        args = Argument.from_input(TestItem.MACHINE_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_machine_machine_group_suppress(self):
        args = Argument.from_input(TestItem.MACHINE_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.list,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 2)

    ####################################### Option all ########################################
    def test_all(self):
        args = Argument.from_input(TestItem.ALL.value)
        true_args = Argument(
            option=Option.job,
            all=True,
            user=None
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_all_machine(self):
        args = Argument.from_input(TestItem.ALL_MACHINE.value)
        true_args = Argument(
            option=Option.job,
            all=True,
            user=None,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_all_machines(self):
        args = Argument.from_input(TestItem.ALL_MACHINES.value)
        true_args = Argument(
            option=Option.job,
            all=True,
            user=None,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_all_group(self):
        args = Argument.from_input(TestItem.ALL_GROUP.value)
        true_args = Argument(
            option=Option.job,
            all=True,
            user=None,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_all_machine_group(self):
        args = Argument.from_input(TestItem.ALL_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.job,
            all=True,
            user=None,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_all_machine_group_suppress(self):
        args = Argument.from_input(TestItem.ALL_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.job,
            all=True,
            user=None,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 2)

    ######################################## Option me ########################################
    def test_me(self):
        args = Argument.from_input(TestItem.ME.value)
        true_args = Argument(
            option=Option.job
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_me_machine(self):
        args = Argument.from_input(TestItem.ME_MACHINE.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_me_machines(self):
        args = Argument.from_input(TestItem.ME_MACHINES.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_me_group(self):
        args = Argument.from_input(TestItem.ME_GROUP.value)
        true_args = Argument(
            option=Option.job,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_me_machine_group(self):
        args = Argument.from_input(TestItem.ME_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    def test_me_machine_group_suppress(self):
        args = Argument.from_input(TestItem.ME_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.job,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 2)

    ####################################### Option kill #######################################
    @patch("builtins.input", return_value="y")
    def test_kill(self, mock_input):
        args = Argument.from_input(TestItem.KILL_lower.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            pid=["1234"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_kills(self, mock_input):
        args = Argument.from_input(TestItem.KILL_lower_pids.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            pid=["1234", "5678"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    ##################################### Option killall ######################################
    @patch("builtins.input", return_value="y")
    def test_killall(self, mock_input):
        args = Argument.from_input(TestItem.KILLALL.value)
        true_args = Argument(
            option=Option.KILL
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killall_machine(self, mock_input):
        args = Argument.from_input(TestItem.KILLALL_MACHINE.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killall_machines(self, mock_input):
        args = Argument.from_input(TestItem.KILLALL_MACHINES.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killall_group(self, mock_input):
        args = Argument.from_input(TestItem.KILLALL_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            group=["kuda"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killall_machine_group(self, mock_input):
        args = Argument.from_input(TestItem.KILLALL_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killall_machine_group_suppress(self, mock_input):
        args = Argument.from_input(TestItem.KILLALL_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 2)

    @patch("builtins.input", return_value="y")
    def test_killall_user_err(self, mock_input):
        with self.assertRaises(SystemExit):
            Argument.from_input(TestItem.KILLALL_USER_ERR.value)
        self.assertEqual(len(MessageHandler().msg[MessageType.ERROR]), 1)

    ################################### Option killmachine ####################################
    @patch("builtins.input", return_value="y")
    def test_killmachine(self, mock_input):
        args = Argument.from_input(TestItem.KILLMACHINE.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    ##################################### Option killthis #####################################
    @patch("builtins.input", return_value="y")
    def test_killthis(self, mock_input):
        args = Argument.from_input(TestItem.KILLTHIS.value)
        true_args = Argument(
            option=Option.KILL,
            command="python test.py"
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killthis_machine(self, mock_input):
        args = Argument.from_input(TestItem.KILLTHIS_MACHINE.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killthis_machines(self, mock_input):
        args = Argument.from_input(TestItem.KILLTHIS_MACHINES.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killthis_group(self, mock_input):
        args = Argument.from_input(TestItem.KILLTHIS_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            group=["kuda"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killthis_machine_group(self, mock_input):
        args = Argument.from_input(TestItem.KILLTHIS_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killthis_machine_group_suppress(self, mock_input):
        args = Argument.from_input(TestItem.KILLTHIS_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"],
            command="python test.py"
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 2)

    #################################### Option killbefore ####################################
    @patch("builtins.input", return_value="y")
    def test_killbefore(self, mock_input):
        args = Argument.from_input(TestItem.KILLBEFORE.value)
        true_args = Argument(
            option=Option.KILL,
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killbefore_machine(self, mock_input):
        args = Argument.from_input(TestItem.KILLBEFORE_MACHINE.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killbefore_machines(self, mock_input):
        args = Argument.from_input(TestItem.KILLBEFORE_MACHINES.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "tenet2", "kuda1"],
            group=["tenet", "kuda"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killbefore_group(self, mock_input):
        args = Argument.from_input(TestItem.KILLBEFORE_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            group=["kuda"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killbefore_machine_group(self, mock_input):
        args = Argument.from_input(TestItem.KILLBEFORE_MACHINE_GROUP.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1"],
            group=["tenet"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 1)

    @patch("builtins.input", return_value="y")
    def test_killbefore_machine_group_suppress(self, mock_input):
        args = Argument.from_input(TestItem.KILLBEFORE_MACHINE_GROUP_SUPPRESS.value)
        true_args = Argument(
            option=Option.KILL,
            machine=["tenet1", "xenet1"],
            group=["tenet", "xenet"],
            time=["1h", "30m"]
        )
        self.assertEqual(args, true_args)
        self.assertEqual(len(MessageHandler().msg[MessageType.WARNING]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
